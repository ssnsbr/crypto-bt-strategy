from ._base_condition import Condition
import backtrader as bt


class MomentumCond(Condition):
    """
    Rate of Change (Momentum) - Trend Following
    Positive momentum = uptrend, negative = downtrend
    """
    default_params = {
        "period": 10,
        "threshold": 0.02,  # 2% momentum threshold
    }

    def __init__(self, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.momentum = bt.indicators.Momentum(close, period=self.params["period"])
        self.close = close

    def get_name(self):
        return f"Momentum({self.params['period']})"

    def long(self):
        """Enter long when momentum is strongly positive"""
        mom_pct = self.momentum[0] / self.close[0]
        ok = mom_pct > self.params["threshold"]
        msg = f"{self.get_name()} LONG momentum={mom_pct*100:.2f}% > {self.params['threshold']*100:.1f}%"
        return ok, msg

    def short(self):
        """Enter short when momentum is strongly negative"""
        mom_pct = self.momentum[0] / self.close[0]
        ok = mom_pct < -self.params["threshold"]
        msg = f"{self.get_name()} SHORT momentum={mom_pct*100:.2f}% < -{self.params['threshold']*100:.1f}%"
        return ok, msg

    def exit_long(self):
        """Exit long when momentum turns negative"""
        ok = self.momentum[0] < 0
        msg = f"{self.get_name()} exit LONG momentum={self.momentum[0]:.2f} < 0"
        return ok, msg

    def exit_short(self):
        """Exit short when momentum turns positive"""
        ok = self.momentum[0] > 0
        msg = f"{self.get_name()} exit SHORT momentum={self.momentum[0]:.2f} > 0"
        return ok, msg


class ROCCond(Condition):
    """
    Rate of Change (%) - Similar to Momentum but in percentage
    """
    default_params = {
        "period": 10,
        "threshold_pct": 2.0,  # 2% ROC threshold
    }

    def __init__(self, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.roc = bt.indicators.ROC(close, period=self.params["period"])

    def get_name(self):
        return f"ROC({self.params['period']})"

    def long(self):
        """Enter long when ROC is strongly positive"""
        ok = self.roc[0] > self.params["threshold_pct"]
        msg = f"{self.get_name()} LONG ROC={self.roc[0]:.2f}% > {self.params['threshold_pct']}%"
        return ok, msg

    def short(self):
        """Enter short when ROC is strongly negative"""
        ok = self.roc[0] < -self.params["threshold_pct"]
        msg = f"{self.get_name()} SHORT ROC={self.roc[0]:.2f}% < -{self.params['threshold_pct']}%"
        return ok, msg

    def exit_long(self):
        """Exit long when ROC turns negative"""
        ok = self.roc[0] < 0
        msg = f"{self.get_name()} exit LONG ROC={self.roc[0]:.2f}% < 0"
        return ok, msg

    def exit_short(self):
        """Exit short when ROC turns positive"""
        ok = self.roc[0] > 0
        msg = f"{self.get_name()} exit SHORT ROC={self.roc[0]:.2f}% > 0"
        return ok, msg
