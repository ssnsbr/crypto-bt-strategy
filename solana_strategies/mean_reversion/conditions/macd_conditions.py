from ._base_condition import Condition
import backtrader as bt


class MACDHistCond(Condition):
    """Check if MACD histogram is positive/negative (momentum direction)"""
    default_params = {
        "fast": 12,
        "slow": 26,
        "signal": 9
    }

    def __init__(self, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.macd = bt.indicators.MACD(price,
                                       period_me1=self.params["fast"],
                                       period_me2=self.params["slow"],
                                       period_signal=self.params["signal"])

    def get_name(self):
        return f"MACDHist({self.params['fast']},{self.params['slow']},{self.params['signal']})"

    def long(self):
        hist = self.macd.macd[0] - self.macd.signal[0]
        ok = hist > 0
        return ok, f"{self.get_name()} LONG hist={hist:.4f} > 0"

    def short(self):
        hist = self.macd.macd[0] - self.macd.signal[0]
        ok = hist < 0
        return ok, f"{self.get_name()} SHORT hist={hist:.4f} < 0"

    def exit_long(self):
        hist = self.macd.macd[0] - self.macd.signal[0]
        ok = hist < 0
        return ok, f"{self.get_name()} exit LONG hist={hist:.4f} < 0"

    def exit_short(self):
        hist = self.macd.macd[0] - self.macd.signal[0]
        ok = hist > 0
        return ok, f"{self.get_name()} exit SHORT hist={hist:.4f} > 0"


class MACDHistChangeCond(Condition):
    """Check if MACD histogram is increasing/decreasing (momentum acceleration)"""
    default_params = {
        "fast": 12,
        "slow": 26,
        "signal": 9,
        "lookback": 1  # Compare with N bars ago
    }

    def __init__(self, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.macd = bt.indicators.MACD(price,
                                       period_me1=self.params["fast"],
                                       period_me2=self.params["slow"],
                                       period_signal=self.params["signal"])

    def get_name(self):
        return f"MACDHistChg({self.params['fast']},{self.params['slow']},{self.params['signal']})"

    def _hist_current(self):
        return self.macd.macd[0] - self.macd.signal[0]

    def _hist_previous(self):
        lb = self.params["lookback"]
        return self.macd.macd[-lb] - self.macd.signal[-lb]

    def long(self):
        """Histogram increasing (bullish momentum building)"""
        hist_curr = self._hist_current()
        hist_prev = self._hist_previous()
        ok = hist_curr > hist_prev
        return ok, f"{self.get_name()} LONG hist increasing {hist_prev:.4f} -> {hist_curr:.4f}"

    def short(self):
        """Histogram decreasing (bearish momentum building)"""
        hist_curr = self._hist_current()
        hist_prev = self._hist_previous()
        ok = hist_curr < hist_prev
        return ok, f"{self.get_name()} SHORT hist decreasing {hist_prev:.4f} -> {hist_curr:.4f}"

    def exit_long(self):
        """Histogram starts decreasing (momentum weakening)"""
        hist_curr = self._hist_current()
        hist_prev = self._hist_previous()
        ok = hist_curr < hist_prev
        return ok, f"{self.get_name()} exit LONG hist decreasing {hist_prev:.4f} -> {hist_curr:.4f}"

    def exit_short(self):
        """Histogram starts increasing (momentum weakening)"""
        hist_curr = self._hist_current()
        hist_prev = self._hist_previous()
        ok = hist_curr > hist_prev
        return ok, f"{self.get_name()} exit SHORT hist increasing {hist_prev:.4f} -> {hist_curr:.4f}"


class MACDSignalCond(Condition):
    default_params = {
        "fast": 12,
        "slow": 26,
        "signal": 9
    }

    def __init__(self, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.macd = bt.indicators.MACD(price,
                                       period_me1=self.params["fast"],
                                       period_me2=self.params["slow"],
                                       period_signal=self.params["signal"])

    def get_name(self):
        return f"MACD({self.params['fast']},{self.params['slow']},{self.params['signal']})"

    def long(self):
        ok = self.macd.macd[0] > self.macd.signal[0]
        return ok, f"{self.get_name()} LONG MACD {self.macd.macd[0]:.2f} > signal {self.macd.signal[0]:.2f}"

    def short(self):
        ok = self.macd.macd[0] < self.macd.signal[0]
        return ok, f"{self.get_name()} SHORT MACD {self.macd.macd[0]:.2f} < signal {self.macd.signal[0]:.2f}"

    def exit_long(self):
        ok = self.macd.macd[0] < self.macd.signal[0]
        return ok, f"{self.get_name()} exit LONG MACD {self.macd.macd[0]:.2f} < signal {self.macd.signal[0]:.2f}"

    def exit_short(self):
        ok = self.macd.macd[0] > self.macd.signal[0]
        return ok, f"{self.get_name()} exit SHORT MACD {self.macd.macd[0]:.2f} > signal {self.macd.signal[0]:.2f}"


class MeanReversionMACDCond(Condition):
    """
    Mean reversion using MACD - enter when histogram at extremes, exit at zero cross
    """
    default_params = {
        "fast": 12,
        "slow": 26,
        "signal": 9,
        "hist_extreme": 0.5,  # Histogram threshold for entry
    }

    def __init__(self, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)
        self.macd = bt.indicators.MACD(
            price,
            period_me1=self.params["fast"],
            period_me2=self.params["slow"],
            period_signal=self.params["signal"]
        )

    def get_name(self):
        return f"MACD_MeanRev({self.params['fast']},{self.params['slow']},{self.params['signal']})"

    def _histogram(self):
        return self.macd.macd[0] - self.macd.signal[0]

    def long(self):
        """Enter long when histogram is extremely negative (oversold momentum)"""
        hist = self._histogram()
        ok = hist < -self.params["hist_extreme"]
        return ok, f"{self.get_name()} LONG hist={hist:.4f} < -{self.params['hist_extreme']}"

    def short(self):
        """Enter short when histogram is extremely positive (overbought momentum)"""
        hist = self._histogram()
        ok = hist > self.params["hist_extreme"]
        return ok, f"{self.get_name()} SHORT hist={hist:.4f} > {self.params['hist_extreme']}"

    def exit_long(self):
        """Exit long when histogram crosses back above zero"""
        hist = self._histogram()
        ok = hist > 0
        return ok, f"{self.get_name()} exit LONG hist={hist:.4f} > 0"

    def exit_short(self):
        """Exit short when histogram crosses back below zero"""
        hist = self._histogram()
        ok = hist < 0
        return ok, f"{self.get_name()} exit SHORT hist={hist:.4f} < 0"
