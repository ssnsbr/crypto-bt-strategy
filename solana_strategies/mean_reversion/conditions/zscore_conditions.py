from ._base_condition import Condition
import backtrader as bt


class ZScoreCond(Condition):
    default_params = {
        "ma_period": 20,
        "std_period": 20,
        "long_thr": -2,
        "short_thr": 2
    }

    def __init__(self, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.ma = bt.indicators.SMA(price, period=self.params["ma_period"])
        self.std = bt.indicators.StandardDeviation(price, period=self.params["std_period"])
        self.price = price

    def get_name(self):
        return f"ZScore({self.params['ma_period']},{self.params['std_period']})"

    def zscore(self):
        return (self.price[0] - self.ma[0]) / self.std[0] if self.std[0] != 0 else 0

    def long(self):
        ok = self.zscore() < self.params["long_thr"]
        return ok, f"{self.get_name()} LONG Z={self.zscore():.2f} < {self.params['long_thr']}"

    def short(self):
        ok = self.zscore() > self.params["short_thr"]
        return ok, f"{self.get_name()} SHORT Z={self.zscore():.2f} > {self.params['short_thr']}"

    def exit_long(self):
        ok = self.zscore() > 0
        return ok, f"{self.get_name()} exit LONG Z={self.zscore():.2f} > 0"

    def exit_short(self):
        ok = self.zscore() < 0
        return ok, f"{self.get_name()} exit SHORT Z={self.zscore():.2f} < 0"


class MeanReversionZScoreCond(Condition):
    """
    Mean reversion using Z-Score - buy when extremely low, sell when extremely high
    """
    default_params = {
        "ma_period": 20,
        "std_period": 20,
        "entry_threshold": 2.0,   # Enter at ±2 standard deviations
        "exit_threshold": 0.5,    # Exit when back within ±0.5 std devs
    }

    def __init__(self, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)
        self.price = price
        self.ma = bt.indicators.SMA(price, period=self.params["ma_period"])
        self.std = bt.indicators.StandardDeviation(price, period=self.params["std_period"])

    def get_name(self):
        return f"ZScore_MeanRev({self.params['ma_period']},{self.params['std_period']})"

    def zscore(self):
        return (self.price[0] - self.ma[0]) / self.std[0] if self.std[0] != 0 else 0

    def long(self):
        """Enter long when Z-score is extremely negative (oversold)"""
        z = self.zscore()
        ok = z < -self.params["entry_threshold"]
        return ok, f"{self.get_name()} LONG Z={z:.2f} < -{self.params['entry_threshold']}"

    def short(self):
        """Enter short when Z-score is extremely positive (overbought)"""
        z = self.zscore()
        ok = z > self.params["entry_threshold"]
        return ok, f"{self.get_name()} SHORT Z={z:.2f} > {self.params['entry_threshold']}"

    def exit_long(self):
        """Exit long when Z-score returns closer to mean"""
        z = self.zscore()
        ok = z > -self.params["exit_threshold"]
        return ok, f"{self.get_name()} exit LONG Z={z:.2f} > -{self.params['exit_threshold']}"

    def exit_short(self):
        """Exit short when Z-score returns closer to mean"""
        z = self.zscore()
        ok = z < self.params["exit_threshold"]
        return ok, f"{self.get_name()} exit SHORT Z={z:.2f} < {self.params['exit_threshold']}"
