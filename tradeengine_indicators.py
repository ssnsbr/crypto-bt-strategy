from collections import deque
from typing import Tuple

from dataclasses import dataclass
from typing import Type, Tuple
from abc import ABC, abstractmethod


class Indicator(ABC):
    def __init__(self, key: str):
        self._key = key

    def key(self) -> str:
        return self._key

    @abstractmethod
    def update(self, candle):
        pass

    @abstractmethod
    def value(self):
        pass

    def values(self) -> dict:
        """
        Override to expose multiple outputs.
        Default wraps single value() for backwards compatibility.
        """
        return {"value": self.value()}

    def reset(self):
        pass

    def ready(self) -> bool:
        return True

    def get_state(self) -> dict:
        """
        Return internal state needed to restore indicator.
        Must be JSON-serializable.
        """
        return {}

    def set_state(self, state: dict):
        """
        Restore indicator from state produced by get_state().
        """
        pass


class DEMA(Indicator):
    """
    Double Exponential Moving Average: 2*EMA(src, len) - EMA(EMA(src, len), len)
    Streaming implementation.
    """

    def __init__(self, period: int):
        self.period = period
        self.k = 2.0 / (period + 1)

        self._ema1 = None
        self._ema2 = None
        self._count = 0
        self._value = None

    def update(self, candle):
        self.update_value(candle.close)

    def update_value(self, price: float):
        if self._ema1 is None:
            self._ema1 = price
            self._ema2 = price
            self._count = 1
        else:
            self._ema1 = price * self.k + self._ema1 * (1 - self.k)
            self._ema2 = self._ema1 * self.k + self._ema2 * (1 - self.k)
            self._count += 1

        self._value = 2 * self._ema1 - self._ema2

    def value(self):
        return self._value

    def ready(self) -> bool:
        return self._count >= self.period

    def get_state(self) -> dict:
        return {
            "ema1": self._ema1,
            "ema2": self._ema2,
            "count": self._count,
            "value": self._value,
        }

    def set_state(self, state: dict):
        self._ema1 = state["ema1"]
        self._ema2 = state["ema2"]
        self._count = state["count"]
        self._value = state["value"]


class BarsSinceCross(Indicator):
    """
    Streaming equivalent of:
        bars_i = ta.barssince(ta.cross(close, ma))
        z_i    = -1 if ma > close else 1
    Tracks bars since last cross + sign of position.
    Optionally normalises by MA period (matching the document code).
    """

    def __init__(self, dema: DEMA, period: int, useZ: bool = True, normalize_by_period: bool = True):
        self.dema = dema
        self.period = period
        self.useZ = useZ
        self.normalize_by_period = normalize_by_period

        self.bars_since: int = 0
        self._value: float = 0.0
        self._prev_diff = None

    def update(self, candle):
        close = candle.close
        ma_val = self.dema.value()

        if ma_val is None:
            return

        diff = close - ma_val

        self.bars_since += 1

        # cross detection: sign flip or exact touch
        if self._prev_diff is not None:
            if diff == 0 or (diff * self._prev_diff < 0):
                self.bars_since = 0

        self._prev_diff = diff

        raw = self.bars_since / self.period if self.normalize_by_period else float(self.bars_since)

        if self.useZ:
            z = -1 if ma_val > close else 1
            self._value = raw * z
        else:
            self._value = raw

    def value(self) -> float:
        return self._value

    def ready(self) -> bool:
        return self.dema.ready()

    def get_state(self) -> dict:
        return {
            "bars_since": self.bars_since,
            "_value": self._value,
            "_prev_diff": self._prev_diff,
        }

    def set_state(self, state: dict):
        self.bars_since = state["bars_since"]
        self._value = state["_value"]
        self._prev_diff = state["_prev_diff"]


class TimeDistance(Indicator):
    """
    Streaming translation of the Pine Script ind.next() logic.

    Uses 5 DEMA MAs. For each bar:
      1. Average (optionally signed) bars-since-cross across all 5 MAs.
      2. Smooth with EMA(smooth).
      3. Z-score normalize with SMA/StdDev(normalizing).
      4. Signal line: EMA(normalized, signaling).

    Public attributes after .update(candle):
        .time_norm      – normalized oscillator value
        .time_signal    – signal line
        .slope_up       – bool: time_norm > time_signal
        .slope_down     – bool: time_norm < time_signal
    """

    MA_LENGTHS = (21, 50, 100, 150, 200)  # defaults matching typical Pine usage

    def __init__(
        self,
        ma_lengths: Tuple[int, ...] = MA_LENGTHS,
        smooth: int = 23,
        useZ: bool = True,
        normalizing: int = 200,
        signaling: int = 15,
        # normalize_by_period: bool = False,
    ):
        self.smooth = smooth
        self.useZ = useZ
        self.normalizing = normalizing
        self.signaling = signaling

        # 5 DEMAs + their bars-since-cross trackers
        self.demas = [DEMA(length) for length in ma_lengths]
        self.bars_inds = [
            BarsSinceCross(dema, length, useZ)
            for dema, length in zip(self.demas, ma_lengths)
        ]

        # Smoothing EMA
        self._avg_ema = _StreamingEMA(smooth)

        # Normalisation buffers (rolling SMA + StdDev)
        self._norm_buf: deque = deque(maxlen=normalizing)

        # Signal EMA
        self._signal_ema = _StreamingEMA(signaling)

        # Outputs
        self.time_norm: float | None = None
        self.time_signal: float | None = None
        self.slope_up: bool = False
        self.slope_down: bool = False

    # ------------------------------------------------------------------
    def update(self, candle):
        # Step 1 – update all DEMAs, then bars-since trackers
        for dema in self.demas:
            dema.update(candle)

        for bi in self.bars_inds:
            bi.update(candle)

        # Need all DEMAs warm before proceeding
        if not all(d.ready() for d in self.demas):
            return

        # Step 2 – average bars values  (mirrors Pine: sum/5)
        avg = sum(bi.value() for bi in self.bars_inds) / len(self.bars_inds)

        # Step 3 – smooth
        self._avg_ema.update(avg)
        if not self._avg_ema.ready():
            return
        smoothed = self._avg_ema.value()

        # Step 4 – rolling z-score
        self._norm_buf.append(smoothed)
        if len(self._norm_buf) < self.normalizing:
            return

        mean = sum(self._norm_buf) / self.normalizing
        variance = sum((x - mean) ** 2 for x in self._norm_buf) / self.normalizing
        std = variance ** 0.5

        if std == 0:
            return

        self.time_norm = (smoothed - mean) / std

        # Step 5 – signal line
        self._signal_ema.update(self.time_norm)
        if self._signal_ema.ready():
            self.time_signal = self._signal_ema.value()
            self.slope_up = self.time_norm > self.time_signal
            self.slope_down = self.time_norm < self.time_signal

    def value(self):
        return self.time_norm

    def values(self) -> dict:
        return {
            "value": self.time_norm,        # keeps .value() contract
            "signal": self.time_signal,
            "slope_up": self.slope_up,
            "slope_down": self.slope_down,
        }

    def ready(self) -> bool:
        return self.time_signal is not None

    # ------------------------------------------------------------------
    def get_state(self) -> dict:
        return {
            "demas": [d.get_state() for d in self.demas],
            "bars_inds": [b.get_state() for b in self.bars_inds],
            "avg_ema": self._avg_ema.get_state(),
            "norm_buf": list(self._norm_buf),
            "signal_ema": self._signal_ema.get_state(),
            "time_norm": self.time_norm,
            "time_signal": self.time_signal,
            "slope_up": self.slope_up,
            "slope_down": self.slope_down,
        }

    def set_state(self, state: dict):
        for d, s in zip(self.demas, state["demas"]):
            d.set_state(s)
        for b, s in zip(self.bars_inds, state["bars_inds"]):
            b.set_state(s)
        self._avg_ema.set_state(state["avg_ema"])
        self._norm_buf.clear()
        self._norm_buf.extend(state["norm_buf"])
        self._signal_ema.set_state(state["signal_ema"])
        self.time_norm = state["time_norm"]
        self.time_signal = state["time_signal"]
        self.slope_up = state["slope_up"]
        self.slope_down = state["slope_down"]


# ---------------------------------------------------------------------------
# Minimal self-contained EMA used internally (no candle dependency)
# ---------------------------------------------------------------------------

class _StreamingEMA:
    """Lightweight EMA that accepts raw float values (not candles)."""

    def __init__(self, period: int):
        self.period = period
        self.k = 2.0 / (period + 1)
        self._val: float | None = None
        self._count: int = 0

    def update(self, price: float):
        if self._val is None:
            self._val = price
        else:
            self._val = price * self.k + self._val * (1 - self.k)
        self._count += 1

    def value(self) -> float | None:
        return self._val

    def ready(self) -> bool:
        return self._count >= self.period

    def get_state(self) -> dict:
        return {"val": self._val, "count": self._count}

    def set_state(self, state: dict):
        self._val = state["val"]
        self._count = state["count"]


# Usage
# ind = TimeDistance(
#     ma_lengths=(21, 50, 100, 150, 200),
#     smooth=23,
#     useZ=True,
#     normalizing=200,
#     signaling=15,
# )

# for candle in live_candles:
#     ind.update(candle)
#     if ind.ready():
#         print(ind.time_norm, ind.time_signal, ind.slope_up)
