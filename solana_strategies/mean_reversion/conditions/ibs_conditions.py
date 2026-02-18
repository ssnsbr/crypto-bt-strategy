
from ._base_condition import Condition


class IBSCond(Condition):
    """
    Internal Bar Strength (IBS) - Mean reversion indicator
    IBS = (Close - Low) / (High - Low)
    Values near 0 = oversold, values near 1 = overbought
    """
    default_params = {
        "oversold": 0.2,    # Enter long when IBS < 0.2
        "overbought": 0.8,  # Enter short when IBS > 0.8
        "exit_neutral": 0.5,  # Exit when IBS returns to middle
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)
        self.high = high
        self.low = low
        self.close = close

    def get_name(self):
        return f"IBS({self.params['oversold']:.2f},{self.params['overbought']:.2f})"

    def _calculate_ibs(self):
        """Calculate Internal Bar Strength"""
        range_hl = self.high[0] - self.low[0]
        if range_hl == 0:
            return 0.5  # Neutral if no range
        return (self.close[0] - self.low[0]) / range_hl

    def long(self):
        """Enter long when IBS is low (closed near low of day - oversold)"""
        ibs = self._calculate_ibs()
        ok = ibs < self.params["oversold"]
        return ok, f"{self.get_name()} LONG IBS={ibs:.3f} < {self.params['oversold']}"

    def short(self):
        """Enter short when IBS is high (closed near high of day - overbought)"""
        ibs = self._calculate_ibs()
        ok = ibs > self.params["overbought"]
        return ok, f"{self.get_name()} SHORT IBS={ibs:.3f} > {self.params['overbought']}"

    def exit_long(self):
        """Exit long when IBS returns to neutral or above"""
        ibs = self._calculate_ibs()
        ok = ibs > self.params["exit_neutral"]
        return ok, f"{self.get_name()} exit LONG IBS={ibs:.3f} > {self.params['exit_neutral']}"

    def exit_short(self):
        """Exit short when IBS returns to neutral or below"""
        ibs = self._calculate_ibs()
        ok = ibs < self.params["exit_neutral"]
        return ok, f"{self.get_name()} exit SHORT IBS={ibs:.3f} < {self.params['exit_neutral']}"
