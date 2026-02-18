from ._base_condition import Condition


class FractalsCond(Condition):
    """
    Williams Fractals - Reversal patterns
    Up Fractal: High > 2 highs on left and 2 highs on right
    Down Fractal: Low < 2 lows on left and 2 lows on right
    """
    default_params = {
        "period": 5,  # Total period (5 = 2 left + 1 middle + 2 right)
    }

    def __init__(self, high, low, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.high = high
        self.low = low

    def get_name(self):
        return f"Fractals({self.params['period']})"

    def _is_up_fractal(self):
        """Check if middle bar is up fractal (local high)"""
        if len(self.high) < self.params["period"]:
            return False

        middle = self.high[-2]
        return (middle > self.high[-4] and middle > self.high[-3] and
                middle > self.high[-1] and middle > self.high[0])

    def _is_down_fractal(self):
        """Check if middle bar is down fractal (local low)"""
        if len(self.low) < self.params["period"]:
            return False

        middle = self.low[-2]
        return (middle < self.low[-4] and middle < self.low[-3] and
                middle < self.low[-1] and middle < self.low[0])

    def long(self):
        """Enter long on down fractal (buy at support)"""
        ok = self._is_down_fractal()
        msg = f"{self.get_name()} LONG down fractal detected (support)"
        return ok, msg

    def short(self):
        """Enter short on up fractal (sell at resistance)"""
        ok = self._is_up_fractal()
        msg = f"{self.get_name()} SHORT up fractal detected (resistance)"
        return ok, msg

    def exit_long(self):
        """Exit long on up fractal (resistance reached)"""
        ok = self._is_up_fractal()
        msg = f"{self.get_name()} exit LONG up fractal (resistance)"
        return ok, msg

    def exit_short(self):
        """Exit short on down fractal (support reached)"""
        ok = self._is_down_fractal()
        msg = f"{self.get_name()} exit SHORT down fractal (support)"
        return ok, msg


class TrendStructureCond(Condition):
    """
    Higher Highs / Lower Lows - Trend structure
    Uptrend: HH + HL, Downtrend: LH + LL
    """
    default_params = {
        "lookback": 10,       # Bars to look back for swing points
        "min_swing_pct": 0.01,  # Minimum 1% move to count as swing
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.high = high
        self.low = low
        self.close = close

    def get_name(self):
        return f"TrendStruct({self.params['lookback']})"

    def _is_higher_high(self):
        """Current high > previous high"""
        lb = self.params["lookback"]
        prev_high = max([self.high[-i] for i in range(1, lb + 1)])
        return self.high[0] > prev_high * (1 + self.params["min_swing_pct"])

    def _is_higher_low(self):
        """Current low > previous low"""
        lb = self.params["lookback"]
        prev_low = min([self.low[-i] for i in range(1, lb + 1)])
        return self.low[0] > prev_low * (1 + self.params["min_swing_pct"])

    def _is_lower_high(self):
        """Current high < previous high"""
        lb = self.params["lookback"]
        prev_high = max([self.high[-i] for i in range(1, lb + 1)])
        return self.high[0] < prev_high * (1 - self.params["min_swing_pct"])

    def _is_lower_low(self):
        """Current low < previous low"""
        lb = self.params["lookback"]
        prev_low = min([self.low[-i] for i in range(1, lb + 1)])
        return self.low[0] < prev_low * (1 - self.params["min_swing_pct"])

    def long(self):
        """Enter long on confirmed uptrend (HH + HL)"""
        ok = self._is_higher_high() and self._is_higher_low()
        msg = f"{self.get_name()} LONG uptrend confirmed (HH+HL)"
        return ok, msg

    def short(self):
        """Enter short on confirmed downtrend (LH + LL)"""
        ok = self._is_lower_high() and self._is_lower_low()
        msg = f"{self.get_name()} SHORT downtrend confirmed (LH+LL)"
        return ok, msg

    def exit_long(self):
        """Exit long on trend break (LH or LL)"""
        ok = self._is_lower_high() or self._is_lower_low()
        msg = f"{self.get_name()} exit LONG trend broken"
        return ok, msg

    def exit_short(self):
        """Exit short on trend break (HH or HL)"""
        ok = self._is_higher_high() or self._is_higher_low()
        msg = f"{self.get_name()} exit SHORT trend broken"
        return ok, msg


class PivotPointsCond(Condition):
    """
    Pivot Points - Support and Resistance levels
    Classic pivot calculation: PP = (H + L + C) / 3
    """
    default_params = {
        "timeframe": "daily",  # Calculate pivots based on daily/weekly data
        "break_distance": 0.001,  # 0.1% distance to confirm break
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.high = high
        self.low = low
        self.close = close

        # These would typically be calculated from higher timeframe
        # Simplified: using recent high/low/close
        self.pivot = None
        self.r1 = None
        self.r2 = None
        self.s1 = None
        self.s2 = None

    def _calculate_pivots(self):
        """Calculate pivot points from previous period"""
        # Simplified: using last bar's data
        h = self.high[-1]
        l = self.low[-1]
        c = self.close[-1]

        self.pivot = (h + l + c) / 3
        self.r1 = 2 * self.pivot - l
        self.r2 = self.pivot + (h - l)
        self.s1 = 2 * self.pivot - h
        self.s2 = self.pivot - (h - l)

    def get_name(self):
        return f"Pivot({self.params['timeframe']})"

    def long(self):
        """Enter long on bounce from support levels"""
        self._calculate_pivots()

        # Check if price bounced from S1 or S2
        at_s1 = abs(self.close[0] - self.s1) / self.s1 < self.params["break_distance"]
        at_s2 = abs(self.close[0] - self.s2) / self.s2 < self.params["break_distance"]

        ok = at_s1 or at_s2
        level = "S1" if at_s1 else "S2"
        msg = f"{self.get_name()} LONG bounce from {level}={self.s1 if at_s1 else self.s2:.2f}"
        return ok, msg

    def short(self):
        """Enter short on rejection from resistance levels"""
        self._calculate_pivots()

        # Check if price rejected from R1 or R2
        at_r1 = abs(self.close[0] - self.r1) / self.r1 < self.params["break_distance"]
        at_r2 = abs(self.close[0] - self.r2) / self.r2 < self.params["break_distance"]

        ok = at_r1 or at_r2
        level = "R1" if at_r1 else "R2"
        msg = f"{self.get_name()} SHORT rejection from {level}={self.r1 if at_r1 else self.r2:.2f}"
        return ok, msg

    def exit_long(self):
        """Exit long when reaching resistance"""
        self._calculate_pivots()
        ok = self.close[0] >= self.r1
        msg = f"{self.get_name()} exit LONG at R1={self.r1:.2f}"
        return ok, msg

    def exit_short(self):
        """Exit short when reaching support"""
        self._calculate_pivots()
        ok = self.close[0] <= self.s1
        msg = f"{self.get_name()} exit SHORT at S1={self.s1:.2f}"
        return ok, msg
