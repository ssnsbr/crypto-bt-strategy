import backtrader as bt
import numpy as np


class RSIDivergence(bt.Indicator):
    lines = (
        'bull', 'hidden_bull',
        'bear', 'hidden_bear',
        'pivot_low', 'pivot_high'
    )

    params = dict(
        period=14,
        lbL=5,
        lbR=5,
        rangeLower=5,
        rangeUpper=60,
        src='close'
    )

    plotinfo = dict(subplot=True)

    def __init__(self):
        src = getattr(self.data, self.p.src)

        # RSI
        self.rsi = bt.ind.RSI(src, period=self.p.period)

        # Buffers to store pivots
        self.last_pl_idx = None
        self.last_ph_idx = None

    # -----------------------
    # Pivot detection
    # -----------------------
    def is_pivot_low(self, data, lbL, lbR):
        """Detect RSI pivot low."""
        if len(data) < lbL + lbR + 1:
            return False

        mid = -lbR - 1
        center_val = data[mid]

        left = data.get(size=lbL + lbR + 1)[lbR + 1: -lbR]
        right = data.get(size=lbL + lbR + 1)[:lbR]

        return (
            center_val == min(data[-lbR - lbL - 1: -lbR + 1]) and
            all(center_val < v for v in left) and
            all(center_val < v for v in right)
        )

    def is_pivot_high(self, data, lbL, lbR):
        """Detect RSI pivot high."""
        if len(data) < lbL + lbR + 1:
            return False

        mid = -lbR - 1
        center_val = data[mid]

        left = data.get(size=lbL + lbR + 1)[lbR + 1: -lbR]
        right = data.get(size=lbL + lbR + 1)[:lbR]

        return (
            center_val == max(data[-lbR - lbL - 1: -lbR + 1]) and
            all(center_val > v for v in left) and
            all(center_val > v for v in right)
        )

    # -----------------------
    # Main Next
    # -----------------------
    def next(self):
        i = len(self) - 1
        rsi = self.rsi

        # --------------------------------
        # Detect pivots
        # --------------------------------
        pl = self.is_pivot_low(rsi, self.p.lbL, self.p.lbR)
        ph = self.is_pivot_high(rsi, self.p.lbL, self.p.lbR)

        self.lines.pivot_low[0] = rsi[-self.p.lbR] if pl else np.nan
        self.lines.pivot_high[0] = rsi[-self.p.lbR] if ph else np.nan

        if pl:
            self.last_pl_idx = i - self.p.lbR
        if ph:
            self.last_ph_idx = i - self.p.lbR

        # --------------------------------
        # Divergence logic
        # --------------------------------
        self.lines.bull[0] = 0
        self.lines.hidden_bull[0] = 0
        self.lines.bear[0] = 0
        self.lines.hidden_bear[0] = 0

        # ------------------------------
        # Check ranges
        # ------------------------------
        def in_range(last_idx):
            if last_idx is None:
                return False
            bars = i - last_idx
            return self.p.rangeLower <= bars <= self.p.rangeUpper

        # ------------------------------
        # Bullish Regular
        # RSI HL + Price LL
        # ------------------------------
        if pl and self.last_pl_idx is not None and in_range(self.last_pl_idx):
            prev_rsi = rsi[self.last_pl_idx - i]
            curr_rsi = rsi[-self.p.lbR]

            prev_low = self.data.low[self.last_pl_idx - i]
            curr_low = self.data.low[-self.p.lbR]

            oscHL = curr_rsi > prev_rsi
            priceLL = curr_low < prev_low

            if oscHL and priceLL:
                self.lines.bull[0] = 1

        # ------------------------------
        # Bullish Hidden
        # RSI LL + Price HL
        # ------------------------------
        if pl and self.last_pl_idx is not None and in_range(self.last_pl_idx):
            prev_rsi = rsi[self.last_pl_idx - i]
            curr_rsi = rsi[-self.p.lbR]

            prev_low = self.data.low[self.last_pl_idx - i]
            curr_low = self.data.low[-self.p.lbR]

            oscLL = curr_rsi < prev_rsi
            priceHL = curr_low > prev_low

            if oscLL and priceHL:
                self.lines.hidden_bull[0] = 1

        # ------------------------------
        # Bearish Regular
        # RSI LH + Price HH
        # ------------------------------
        if ph and self.last_ph_idx is not None and in_range(self.last_ph_idx):
            prev_rsi = rsi[self.last_ph_idx - i]
            curr_rsi = rsi[-self.p.lbR]

            prev_high = self.data.high[self.last_ph_idx - i]
            curr_high = self.data.high[-self.p.lbR]

            oscLH = curr_rsi < prev_rsi
            priceHH = curr_high > prev_high

            if oscLH and priceHH:
                self.lines.bear[0] = 1

        # ------------------------------
        # Bearish Hidden
        # RSI HH + Price LH
        # ------------------------------
        if ph and self.last_ph_idx is not None and in_range(self.last_ph_idx):
            prev_rsi = rsi[self.last_ph_idx - i]
            curr_rsi = rsi[-self.p.lbR]

            prev_high = self.data.high[self.last_ph_idx - i]
            curr_high = self.data.high[-self.p.lbR]

            oscHH = curr_rsi > prev_rsi
            priceLH = curr_high < prev_high

            if oscHH and priceLH:
                self.lines.hidden_bear[0] = 1
