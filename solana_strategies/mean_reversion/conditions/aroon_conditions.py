from ._base_condition import Condition
import backtrader as bt


class AroonCond(Condition):
    """
    Aroon Indicator - Identifies trend strength and direction
    Aroon Up measures time since highest high
    Aroon Down measures time since lowest low
    """
    default_params = {
        "period": 25,
        "strong_threshold": 70,  # Above 70 = strong trend
        "weak_threshold": 30,    # Below 30 = weak trend
    }

    def __init__(self, high, low, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.aroon = bt.indicators.AroonIndicator(high, low, period=self.params["period"])

    def get_name(self):
        return f"Aroon({self.params['period']})"

    def long(self):
        """Enter long when Aroon Up > 70 and Aroon Down < 30"""
        up_strong = self.aroon.aroonup[0] > self.params["strong_threshold"]
        down_weak = self.aroon.aroondown[0] < self.params["weak_threshold"]
        ok = up_strong and down_weak
        msg = f"{self.get_name()} LONG AroonUp={self.aroon.aroonup[0]:.1f} AroonDown={self.aroon.aroondown[0]:.1f}"
        return ok, msg

    def short(self):
        """Enter short when Aroon Down > 70 and Aroon Up < 30"""
        down_strong = self.aroon.aroondown[0] > self.params["strong_threshold"]
        up_weak = self.aroon.aroonup[0] < self.params["weak_threshold"]
        ok = down_strong and up_weak
        msg = f"{self.get_name()} SHORT AroonUp={self.aroon.aroonup[0]:.1f} AroonDown={self.aroon.aroondown[0]:.1f}"
        return ok, msg

    def exit_long(self):
        """Exit long when trend weakens"""
        ok = self.aroon.aroonup[0] < self.params["weak_threshold"]
        msg = f"{self.get_name()} exit LONG AroonUp={self.aroon.aroonup[0]:.1f} weakening"
        return ok, msg

    def exit_short(self):
        """Exit short when trend weakens"""
        ok = self.aroon.aroondown[0] < self.params["weak_threshold"]
        msg = f"{self.get_name()} exit SHORT AroonDown={self.aroon.aroondown[0]:.1f} weakening"
        return ok, msg


class AroonOscillatorCond(Condition):
    """
    Aroon Oscillator - AroonUp - AroonDown
    Values from -100 to +100
    """
    default_params = {
        "period": 25,
        "bullish_threshold": 50,   # Above 50 = strong uptrend
        "bearish_threshold": -50,  # Below -50 = strong downtrend
    }

    def __init__(self, high, low, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.aroon = bt.indicators.AroonIndicator(high, low, period=self.params["period"])

    def get_name(self):
        return f"AroonOsc({self.params['period']})"

    def _oscillator(self):
        return self.aroon.aroonup[0] - self.aroon.aroondown[0]

    def long(self):
        """Enter long when oscillator strongly positive"""
        osc = self._oscillator()
        ok = osc > self.params["bullish_threshold"]
        msg = f"{self.get_name()} LONG Osc={osc:.1f} > {self.params['bullish_threshold']}"
        return ok, msg

    def short(self):
        """Enter short when oscillator strongly negative"""
        osc = self._oscillator()
        ok = osc < self.params["bearish_threshold"]
        msg = f"{self.get_name()} SHORT Osc={osc:.1f} < {self.params['bearish_threshold']}"
        return ok, msg

    def exit_long(self):
        """Exit long when oscillator turns negative"""
        osc = self._oscillator()
        ok = osc < 0
        msg = f"{self.get_name()} exit LONG Osc={osc:.1f} < 0"
        return ok, msg

    def exit_short(self):
        """Exit short when oscillator turns positive"""
        osc = self._oscillator()
        ok = osc > 0
        msg = f"{self.get_name()} exit SHORT Osc={osc:.1f} > 0"
        return ok, msg
