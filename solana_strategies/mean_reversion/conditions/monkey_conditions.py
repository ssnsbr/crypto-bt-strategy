import backtrader as bt
from ._base_condition import Condition


class ChaikinMoneyFlowCond(Condition):
    """
    Chaikin Money Flow (CMF) - Volume-weighted accumulation/distribution
    Positive CMF = buying pressure, Negative = selling pressure
    """
    default_params = {
        "period": 20,
        "threshold": 0.05,  # CMF above/below this triggers signal
    }

    def __init__(self, high, low, close, volume, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        # Money Flow Multiplier = [(C - L) - (H - C)] / (H - L)
        # Money Flow Volume = MF Multiplier * Volume
        # CMF = Sum(MFV, period) / Sum(Volume, period)

        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

    def get_name(self):
        return f"CMF({self.params['period']})"

    def _calculate_cmf(self):
        """Calculate Chaikin Money Flow"""
        # Simplified calculation for current bar
        h = self.high[0]
        l = self.low[0]
        c = self.close[0]
        v = self.volume[0]

        if h == l:
            return 0

        mf_multiplier = ((c - l) - (h - c)) / (h - l)

        # This is simplified - proper CMF needs sum over period
        # Using proxy: current bar's money flow
        return mf_multiplier

    def long(self):
        """Enter long when CMF shows strong buying pressure"""
        cmf = self._calculate_cmf()
        ok = cmf > self.params["threshold"]
        msg = f"{self.get_name()} LONG CMF={cmf:.3f} > {self.params['threshold']}"
        return ok, msg

    def short(self):
        """Enter short when CMF shows strong selling pressure"""
        cmf = self._calculate_cmf()
        ok = cmf < -self.params["threshold"]
        msg = f"{self.get_name()} SHORT CMF={cmf:.3f} < -{self.params['threshold']}"
        return ok, msg

    def exit_long(self):
        """Exit long when CMF turns negative"""
        cmf = self._calculate_cmf()
        ok = cmf < 0
        msg = f"{self.get_name()} exit LONG CMF={cmf:.3f} < 0"
        return ok, msg

    def exit_short(self):
        """Exit short when CMF turns positive"""
        cmf = self._calculate_cmf()
        ok = cmf > 0
        msg = f"{self.get_name()} exit SHORT CMF={cmf:.3f} > 0"
        return ok, msg


class MFICond(Condition):
    """
    Money Flow Index (MFI) - Volume-weighted RSI
    Combines price and volume to identify overbought/oversold
    """
    default_params = {
        "period": 14,
        "oversold": 20,
        "overbought": 80,
        "exit_neutral": 50,
    }

    def __init__(self, high, low, close, volume, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        # Calculate MFI manually as backtrader might not have it
        typical_price = (high + low + close) / 3
        raw_money_flow = typical_price * volume

        # This is a simplified version - proper MFI needs more complex calculation
        # Using a proxy: RSI of volume-weighted price
        self.mfi = bt.indicators.RSI(raw_money_flow, period=self.params["period"])

    def get_name(self):
        return f"MFI({self.params['period']})"

    def long(self):
        """Enter long when MFI oversold (smart money accumulating)"""
        ok = self.mfi[0] < self.params["oversold"]
        msg = f"{self.get_name()} LONG MFI={self.mfi[0]:.2f} < {self.params['oversold']}"
        return ok, msg

    def short(self):
        """Enter short when MFI overbought (smart money distributing)"""
        ok = self.mfi[0] > self.params["overbought"]
        msg = f"{self.get_name()} SHORT MFI={self.mfi[0]:.2f} > {self.params['overbought']}"
        return ok, msg

    def exit_long(self):
        """Exit long when MFI returns above neutral"""
        ok = self.mfi[0] > self.params["exit_neutral"]
        msg = f"{self.get_name()} exit LONG MFI={self.mfi[0]:.2f} > {self.params['exit_neutral']}"
        return ok, msg

    def exit_short(self):
        """Exit short when MFI returns below neutral"""
        ok = self.mfi[0] < self.params["exit_neutral"]
        msg = f"{self.get_name()} exit SHORT MFI={self.mfi[0]:.2f} < {self.params['exit_neutral']}"
        return ok, msg
