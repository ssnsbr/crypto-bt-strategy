import backtrader as bt
from ._base_condition import Condition


class UltimateOscillatorCond(Condition):
    """
    Ultimate Oscillator - Multi-timeframe momentum
    Combines 7, 14, and 28 period momentum
    """
    default_params = {
        "period1": 7,
        "period2": 14,
        "period3": 28,
        "oversold": 30,
        "overbought": 70,
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.uo = bt.indicators.UltimateOscillator(
            high, low, close,
            period1=self.params["period1"],
            period2=self.params["period2"],
            period3=self.params["period3"]
        )

    def get_name(self):
        return f"UO({self.params['period1']},{self.params['period2']},{self.params['period3']})"

    def long(self):
        """Enter long when UO oversold"""
        ok = self.uo[0] < self.params["oversold"]
        msg = f"{self.get_name()} LONG UO={self.uo[0]:.2f} < {self.params['oversold']}"
        return ok, msg

    def short(self):
        """Enter short when UO overbought"""
        ok = self.uo[0] > self.params["overbought"]
        msg = f"{self.get_name()} SHORT UO={self.uo[0]:.2f} > {self.params['overbought']}"
        return ok, msg

    def exit_long(self):
        """Exit long when UO returns above 50"""
        ok = self.uo[0] > 50
        msg = f"{self.get_name()} exit LONG UO={self.uo[0]:.2f} > 50"
        return ok, msg

    def exit_short(self):
        """Exit short when UO returns below 50"""
        ok = self.uo[0] < 50
        msg = f"{self.get_name()} exit SHORT UO={self.uo[0]:.2f} < 50"
        return ok, msg


class AwesomeOscillatorCond(Condition):
    """
    Awesome Oscillator - Bill Williams indicator
    5/34 period Simple MA difference
    """
    default_params = {
        "fast": 5,
        "slow": 34,
    }

    def __init__(self, high, low, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        # Median price
        median = (high + low) / 2

        self.ao = bt.indicators.AwesomeOscillator(
            high, low,
            fast=self.params["fast"],
            slow=self.params["slow"]
        )

    def get_name(self):
        return f"AO({self.params['fast']},{self.params['slow']})"

    def long(self):
        """Enter long on saucer signal (3 bars: red, red, green)"""
        # Simplified: enter when AO crosses above 0
        ok = self.ao[0] > 0 and self.ao[-1] <= 0
        msg = f"{self.get_name()} LONG AO={self.ao[0]:.4f} crosses above 0"
        return ok, msg

    def short(self):
        """Enter short when AO crosses below 0"""
        ok = self.ao[0] < 0 and self.ao[-1] >= 0
        msg = f"{self.get_name()} SHORT AO={self.ao[0]:.4f} crosses below 0"
        return ok, msg

    def exit_long(self):
        """Exit long when AO crosses back below 0"""
        ok = self.ao[0] < 0 and self.ao[-1] >= 0
        msg = f"{self.get_name()} exit LONG AO crosses below 0"
        return ok, msg

    def exit_short(self):
        """Exit short when AO crosses back above 0"""
        ok = self.ao[0] > 0 and self.ao[-1] <= 0
        msg = f"{self.get_name()} exit SHORT AO crosses above 0"
        return ok, msg

