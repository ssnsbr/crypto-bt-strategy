from ._base_condition import Condition
import backtrader as bt


class SuperTrendCond(Condition):
    default_params = {
        "period": 10,
        "multiplier": 3
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)
        self.close = close

        self.st = bt.indicators.SuperTrend(high, low, close, period=self.params["period"], multiplier=self.params["multiplier"])

    def get_name(self):
        return f"SuperTrend({self.params['period']},{self.params['multiplier']})"

    def long(self):
        ok = self.st.lines.supertrend[0] < self.close[0]
        return ok, f"{self.get_name()} LONG supertrend below price"

    def short(self):
        ok = self.st.lines.supertrend[0] > self.close[0]
        return ok, f"{self.get_name()} SHORT supertrend above price"

    def exit_long(self):
        ok = self.st.lines.supertrend[0] > self.close[0]
        return ok, f"{self.get_name()} exit LONG supertrend above price"

    def exit_short(self):
        ok = self.st.lines.supertrend[0] < self.close[0]
        return ok, f"{self.get_name()} exit SHORT supertrend below price"
