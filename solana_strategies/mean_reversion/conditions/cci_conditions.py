
from ._base_condition import Condition
import backtrader as bt


class CCICond(Condition):
    default_params = {
        "period": 20,
        "long_thr": -100,
        "short_thr": 100
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.cci = bt.indicators.CCI(high, low, close, period=self.params["period"])

    def get_name(self):
        return f"CCI({self.params['period']})"

    def long(self):
        ok = self.cci[0] < self.params["long_thr"]
        return ok, f"{self.get_name()} LONG CCI {self.cci[0]:.2f} < {self.params['long_thr']}"

    def short(self):
        ok = self.cci[0] > self.params["short_thr"]
        return ok, f"{self.get_name()} SHORT CCI {self.cci[0]:.2f} > {self.params['short_thr']}"

    def exit_long(self):
        ok = self.cci[0] > 0
        return ok, f"{self.get_name()} exit LONG CCI {self.cci[0]:.2f} > 0"

    def exit_short(self):
        ok = self.cci[0] < 0
        return ok, f"{self.get_name()} exit SHORT CCI {self.cci[0]:.2f} < 0"


class MeanReversionCCICond(Condition):
    """
    Mean reversion using CCI - buy extreme lows, sell extreme highs
    """
    default_params = {
        "period": 20,
        "oversold": -200,     # Enter long below this
        "overbought": 200,    # Enter short above this
        "exit_neutral": 0,    # Exit when CCI returns to neutral
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)
        self.cci = bt.indicators.CCI(high, low, close, period=self.params["period"])

    def get_name(self):
        return f"CCI_MeanRev({self.params['period']})"

    def long(self):
        """Enter long when CCI extremely negative (oversold)"""
        ok = self.cci[0] < self.params["oversold"]
        return ok, f"{self.get_name()} LONG CCI={self.cci[0]:.2f} < {self.params['oversold']}"

    def short(self):
        """Enter short when CCI extremely positive (overbought)"""
        ok = self.cci[0] > self.params["overbought"]
        return ok, f"{self.get_name()} SHORT CCI={self.cci[0]:.2f} > {self.params['overbought']}"

    def exit_long(self):
        """Exit long when CCI returns above neutral"""
        ok = self.cci[0] > self.params["exit_neutral"]
        return ok, f"{self.get_name()} exit LONG CCI={self.cci[0]:.2f} > {self.params['exit_neutral']}"

    def exit_short(self):
        """Exit short when CCI returns below neutral"""
        ok = self.cci[0] < self.params["exit_neutral"]
        return ok, f"{self.get_name()} exit SHORT CCI={self.cci[0]:.2f} < {self.params['exit_neutral']}"
