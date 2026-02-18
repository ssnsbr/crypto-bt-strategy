import backtrader as bt
from ._base_condition import Condition


class VWAPCond(Condition):
    """
    VWAP (Volume Weighted Average Price) - Mean Reversion
    Institutional traders often use VWAP as reference
    """
    default_params = {
        "deviation_pct": 0.02,  # 2% deviation from VWAP
    }

    def __init__(self, high, low, close, volume, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close
        # Simple VWAP calculation (for intraday, should reset daily)
        typical_price = (high + low + close) / 3
        self.vwap = bt.indicators.WeightedMovingAverage(typical_price, volume)

    def get_name(self):
        return f"VWAP({self.params['deviation_pct']*100:.1f}%)"

    def long(self):
        """Enter long when price is significantly below VWAP"""
        threshold = self.vwap[0] * (1 - self.params["deviation_pct"])
        ok = self.close[0] < threshold
        msg = f"{self.get_name()} LONG price={self.close[0]:.2f} < threshold={threshold:.2f}"
        return ok, msg

    def short(self):
        """Enter short when price is significantly above VWAP"""
        threshold = self.vwap[0] * (1 + self.params["deviation_pct"])
        ok = self.close[0] > threshold
        msg = f"{self.get_name()} SHORT price={self.close[0]:.2f} > threshold={threshold:.2f}"
        return ok, msg

    def exit_long(self):
        """Exit long when price returns to VWAP"""
        ok = self.close[0] >= self.vwap[0]
        msg = f"{self.get_name()} exit LONG price={self.close[0]:.2f} >= VWAP={self.vwap[0]:.2f}"
        return ok, msg

    def exit_short(self):
        """Exit short when price returns to VWAP"""
        ok = self.close[0] <= self.vwap[0]
        msg = f"{self.get_name()} exit SHORT price={self.close[0]:.2f} <= VWAP={self.vwap[0]:.2f}"
        return ok, msg


class VolumeWeightedRSICond(Condition):
    """
    Volume-weighted RSI - More weight to high-volume periods
    """
    default_params = {
        "period": 14,
        "oversold": 30,
        "overbought": 70,
    }

    def __init__(self, close, volume, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        # Create volume-weighted price
        self.vwp = close * volume
        self.rsi = bt.indicators.RSI(self.vwp, period=self.params["period"])

    def get_name(self):
        return f"VRSI({self.params['period']})"

    def long(self):
        ok = self.rsi[0] < self.params["oversold"]
        return ok, f"{self.get_name()} LONG VRSI={self.rsi[0]:.2f} < {self.params['oversold']}"

    def short(self):
        ok = self.rsi[0] > self.params["overbought"]
        return ok, f"{self.get_name()} SHORT VRSI={self.rsi[0]:.2f} > {self.params['overbought']}"

    def exit_long(self):
        ok = self.rsi[0] > 50
        return ok, f"{self.get_name()} exit LONG VRSI={self.rsi[0]:.2f} > 50"

    def exit_short(self):
        ok = self.rsi[0] < 50
        return ok, f"{self.get_name()} exit SHORT VRSI={self.rsi[0]:.2f} < 50"


class VolumeSpikeCond(Condition):
    """
    Volume Spike - Detect unusual volume activity
    High volume often precedes big moves
    """
    default_params = {
        "ma_period": 20,
        "spike_multiplier": 2.0,  # Volume must be 2x average
        "price_confirmation": True,  # Require price move confirmation
        "min_price_move": 0.01,  # 1% minimum price move
    }

    def __init__(self, close, volume, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close
        self.volume = volume
        self.vol_ma = bt.indicators.SMA(volume, period=self.params["ma_period"])

    def get_name(self):
        return f"VolSpike({self.params['spike_multiplier']}x)"

    def _is_volume_spike(self):
        """Check if current volume is spike"""
        return self.volume[0] > self.vol_ma[0] * self.params["spike_multiplier"]

    def long(self):
        """Enter long on volume spike with bullish price action"""
        volume_spike = self._is_volume_spike()

        if self.params["price_confirmation"]:
            price_up = (self.close[0] - self.close[-1]) / self.close[-1] > self.params["min_price_move"]
            ok = volume_spike and price_up
        else:
            ok = volume_spike

        msg = f"{self.get_name()} LONG vol={self.volume[0]:.0f} vs avg={self.vol_ma[0]:.0f}"
        return ok, msg

    def short(self):
        """Enter short on volume spike with bearish price action"""
        volume_spike = self._is_volume_spike()

        if self.params["price_confirmation"]:
            price_down = (self.close[-1] - self.close[0]) / self.close[-1] > self.params["min_price_move"]
            ok = volume_spike and price_down
        else:
            ok = volume_spike

        msg = f"{self.get_name()} SHORT vol={self.volume[0]:.0f} vs avg={self.vol_ma[0]:.0f}"
        return ok, msg

    def exit_long(self):
        """Exit on volume spike in opposite direction"""
        volume_spike = self._is_volume_spike()
        price_down = (self.close[-1] - self.close[0]) / self.close[-1] > self.params["min_price_move"]
        ok = volume_spike and price_down
        msg = f"{self.get_name()} exit LONG reversal volume spike"
        return ok, msg

    def exit_short(self):
        """Exit on volume spike in opposite direction"""
        volume_spike = self._is_volume_spike()
        price_up = (self.close[0] - self.close[-1]) / self.close[-1] > self.params["min_price_move"]
        ok = volume_spike and price_up
        msg = f"{self.get_name()} exit SHORT reversal volume spike"
        return ok, msg
