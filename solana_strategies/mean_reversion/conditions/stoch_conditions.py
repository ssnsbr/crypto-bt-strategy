from ._base_condition import Condition
import backtrader as bt


class StochasticMeanReversionCond(Condition):
    """
    Stochastic Oscillator - Mean Reversion
    Buy when oversold, sell when overbought
    """
    default_params = {
        "period": 14,
        "period_dfast": 3,   # %K smoothing
        "period_dslow": 3,   # %D smoothing
        "oversold": 20,
        "overbought": 80,
        "exit_neutral": 50,
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.stoch = bt.indicators.Stochastic(
            high, low, close,
            period=self.params["period"],
            period_dfast=self.params["period_dfast"],
            period_dslow=self.params["period_dslow"]
        )

    def get_name(self):
        return f"Stoch_MeanRev({self.params['period']},{self.params['oversold']},{self.params['overbought']})"

    def long(self):
        """Enter long when %K is oversold"""
        ok = self.stoch.percK[0] < self.params["oversold"]
        msg = f"{self.get_name()} LONG %K={self.stoch.percK[0]:.2f} < {self.params['oversold']}"
        return ok, msg

    def short(self):
        """Enter short when %K is overbought"""
        ok = self.stoch.percK[0] > self.params["overbought"]
        msg = f"{self.get_name()} SHORT %K={self.stoch.percK[0]:.2f} > {self.params['overbought']}"
        return ok, msg

    def exit_long(self):
        """Exit long when %K returns above neutral"""
        ok = self.stoch.percK[0] > self.params["exit_neutral"]
        msg = f"{self.get_name()} exit LONG %K={self.stoch.percK[0]:.2f} > {self.params['exit_neutral']}"
        return ok, msg

    def exit_short(self):
        """Exit short when %K returns below neutral"""
        ok = self.stoch.percK[0] < self.params["exit_neutral"]
        msg = f"{self.get_name()} exit SHORT %K={self.stoch.percK[0]:.2f} < {self.params['exit_neutral']}"
        return ok, msg


class StochasticCrossoverCond(Condition):
    """
    Stochastic %K/%D Crossover - Trend Following
    Buy on bullish crossover, sell on bearish crossover
    """
    default_params = {
        "period": 14,
        "period_dfast": 3,
        "period_dslow": 3,
        "oversold_filter": 20,   # Only trade crossovers in oversold zone
        "overbought_filter": 80,  # Only trade crossovers in overbought zone
        "use_filters": True,
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.stoch = bt.indicators.Stochastic(
            high, low, close,
            period=self.params["period"],
            period_dfast=self.params["period_dfast"],
            period_dslow=self.params["period_dslow"]
        )

    def get_name(self):
        return f"Stoch_Cross({self.params['period']})"

    def long(self):
        """Enter long when %K crosses above %D (optionally in oversold zone)"""
        crossover = self.stoch.percK[0] > self.stoch.percD[0] and self.stoch.percK[-1] <= self.stoch.percD[-1]

        if self.params["use_filters"]:
            in_zone = self.stoch.percK[0] < self.params["oversold_filter"]
            ok = crossover and in_zone
        else:
            ok = crossover

        msg = f"{self.get_name()} LONG %K cross above %D: %K={self.stoch.percK[0]:.2f} %D={self.stoch.percD[0]:.2f}"
        return ok, msg

    def short(self):
        """Enter short when %K crosses below %D (optionally in overbought zone)"""
        crossunder = self.stoch.percK[0] < self.stoch.percD[0] and self.stoch.percK[-1] >= self.stoch.percD[-1]

        if self.params["use_filters"]:
            in_zone = self.stoch.percK[0] > self.params["overbought_filter"]
            ok = crossunder and in_zone
        else:
            ok = crossunder

        msg = f"{self.get_name()} SHORT %K cross below %D: %K={self.stoch.percK[0]:.2f} %D={self.stoch.percD[0]:.2f}"
        return ok, msg

    def exit_long(self):
        """Exit long when %K crosses back below %D"""
        ok = self.stoch.percK[0] < self.stoch.percD[0] and self.stoch.percK[-1] >= self.stoch.percD[-1]
        msg = f"{self.get_name()} exit LONG %K cross below %D"
        return ok, msg

    def exit_short(self):
        """Exit short when %K crosses back above %D"""
        ok = self.stoch.percK[0] > self.stoch.percD[0] and self.stoch.percK[-1] <= self.stoch.percD[-1]
        msg = f"{self.get_name()} exit SHORT %K cross above %D"
        return ok, msg
