from ._base_condition import Condition
import backtrader as bt


class WilliamsRMeanReversionCond(Condition):
    """
    Williams %R - Mean Reversion
    Similar to Stochastic but inverted (0 to -100 scale)
    """
    default_params = {
        "period": 14,
        "oversold": -80,     # -80 to -100 is oversold
        "overbought": -20,   # -20 to 0 is overbought
        "exit_neutral": -50,
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.willr = bt.indicators.WilliamsR(high, low, close, period=self.params["period"])

    def get_name(self):
        return f"WillR_MeanRev({self.params['period']})"

    def long(self):
        """Enter long when Williams %R is oversold (< -80)"""
        ok = self.willr[0] < self.params["oversold"]
        msg = f"{self.get_name()} LONG WillR={self.willr[0]:.2f} < {self.params['oversold']}"
        return ok, msg

    def short(self):
        """Enter short when Williams %R is overbought (> -20)"""
        ok = self.willr[0] > self.params["overbought"]
        msg = f"{self.get_name()} SHORT WillR={self.willr[0]:.2f} > {self.params['overbought']}"
        return ok, msg

    def exit_long(self):
        """Exit long when Williams %R returns above neutral"""
        ok = self.willr[0] > self.params["exit_neutral"]
        msg = f"{self.get_name()} exit LONG WillR={self.willr[0]:.2f} > {self.params['exit_neutral']}"
        return ok, msg

    def exit_short(self):
        """Exit short when Williams %R returns below neutral"""
        ok = self.willr[0] < self.params["exit_neutral"]
        msg = f"{self.get_name()} exit SHORT WillR={self.willr[0]:.2f} < {self.params['exit_neutral']}"
        return ok, msg
