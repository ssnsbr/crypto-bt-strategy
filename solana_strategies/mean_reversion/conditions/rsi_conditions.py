from ._base_condition import Condition
import backtrader as bt


class RSICond(Condition):
    default_params = {
        "period": 14,
        "long_thr": 30,
        "short_thr": 70,
        "exit_long_thr": 60,
        "exit_short_thr": 40,
    }

    def __init__(self, price, **kwargs):
        # instance-specific params (no shared mutation)
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.period = self.params["period"]
        self.rsi = bt.indicators.RSI_Safe(price, period=self.period)

    def get_name(self):
        return f"RSI{self.period}"

    # ---------------- ENTRY ---------------- #
    def long(self):
        ok = self.rsi[0] < self.params["long_thr"]
        return ok, f"{self.get_name()} {self.rsi[0]:.2f} < {self.params['long_thr']}"

    def short(self):
        ok = self.rsi[0] > self.params["short_thr"]
        return ok, f"{self.get_name()} {self.rsi[0]:.2f} > {self.params['short_thr']}"

    # ---------------- EXIT ---------------- #
    def exit_long(self):
        ok = self.rsi[0] > self.params["exit_long_thr"]
        return ok, f"{self.get_name()} exit long: {self.rsi[0]:.2f} > {self.params['exit_long_thr']}"

    def exit_short(self):
        ok = self.rsi[0] < self.params["exit_short_thr"]
        return ok, f"{self.get_name()} exit short: {self.rsi[0]:.2f} < {self.params['exit_short_thr']}"


class MeanReversionRSICond(Condition):
    """
    Mean reversion using RSI - buy oversold, sell overbought
    """
    default_params = {
        "period": 14,
        "oversold": 30,      # Enter long below this
        "overbought": 70,    # Enter short above this
        "exit_neutral": 50,  # Exit when RSI returns to neutral
    }

    def __init__(self, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)
        self.period = self.params["period"]
        self.rsi = bt.indicators.RSI_Safe(price, period=self.period)

    def get_name(self):
        return f"RSI_MeanRev{self.period}"

    def long(self):
        """Enter long when oversold (expecting bounce)"""
        ok = self.rsi[0] < self.params["oversold"]
        return ok, f"{self.get_name()} LONG {self.rsi[0]:.2f} < {self.params['oversold']}"

    def short(self):
        """Enter short when overbought (expecting pullback)"""
        ok = self.rsi[0] > self.params["overbought"]
        return ok, f"{self.get_name()} SHORT {self.rsi[0]:.2f} > {self.params['overbought']}"

    def exit_long(self):
        """Exit long when RSI returns to neutral or becomes overbought"""
        ok = self.rsi[0] > self.params["exit_neutral"]
        return ok, f"{self.get_name()} exit LONG {self.rsi[0]:.2f} > {self.params['exit_neutral']}"

    def exit_short(self):
        """Exit short when RSI returns to neutral or becomes oversold"""
        ok = self.rsi[0] < self.params["exit_neutral"]
        return ok, f"{self.get_name()} exit SHORT {self.rsi[0]:.2f} < {self.params['exit_neutral']}"
