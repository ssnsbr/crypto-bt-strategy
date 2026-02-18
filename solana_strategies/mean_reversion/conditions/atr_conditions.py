
from ._base_condition import Condition
import backtrader as bt


class ATRVolatilityFilterCond(Condition):
    """
    ATR as volatility filter - only trade when volatility meets criteria
    Can be used with both trend following and mean reversion
    """
    default_params = {
        "period": 14,
        "min_atr_pct": 0.01,   # Minimum 1% ATR (avoid low volatility)
        "max_atr_pct": 0.05,   # Maximum 5% ATR (avoid extreme volatility)
        "use_max": True,       # Whether to enforce maximum
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close
        self.atr = bt.indicators.ATR(high, low, close, period=self.params["period"])

    def get_name(self):
        return f"ATR_Filter({self.params['period']})"

    def _atr_percent(self):
        """Calculate ATR as percentage of price"""
        return self.atr[0] / self.close[0] if self.close[0] != 0 else 0

    def long(self):
        """Enter long when volatility is in acceptable range"""
        atr_pct = self._atr_percent()
        min_ok = atr_pct > self.params["min_atr_pct"]
        max_ok = not self.params["use_max"] or atr_pct < self.params["max_atr_pct"]
        ok = min_ok and max_ok
        msg = f"{self.get_name()} LONG ATR={atr_pct*100:.2f}% in range"
        return ok, msg

    def short(self):
        """Enter short when volatility is in acceptable range"""
        atr_pct = self._atr_percent()
        min_ok = atr_pct > self.params["min_atr_pct"]
        max_ok = not self.params["use_max"] or atr_pct < self.params["max_atr_pct"]
        ok = min_ok and max_ok
        msg = f"{self.get_name()} SHORT ATR={atr_pct*100:.2f}% in range"
        return ok, msg

    def exit_long(self):
        """Exit long if volatility becomes too extreme"""
        if self.params["use_max"]:
            atr_pct = self._atr_percent()
            ok = atr_pct > self.params["max_atr_pct"]
            msg = f"{self.get_name()} exit LONG (high volatility) ATR={atr_pct*100:.2f}%"
            return ok, msg
        return False, ""

    def exit_short(self):
        """Exit short if volatility becomes too extreme"""
        if self.params["use_max"]:
            atr_pct = self._atr_percent()
            ok = atr_pct > self.params["max_atr_pct"]
            msg = f"{self.get_name()} exit SHORT (high volatility) ATR={atr_pct*100:.2f}%"
            return ok, msg
        return False, ""


class ATRBreakoutCond(Condition):
    """
    ATR Breakout - Trend following when price moves > N * ATR
    Enter when strong directional move occurs
    """
    default_params = {
        "period": 14,
        "atr_multiplier": 1.5,  # Price must move 1.5x ATR to trigger
        "lookback": 1,          # Compare with N bars ago
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close
        self.atr = bt.indicators.ATR(high, low, close, period=self.params["period"])

    def get_name(self):
        return f"ATR_Breakout({self.params['period']},{self.params['atr_multiplier']})"

    def long(self):
        """Enter long when price breaks up by more than N * ATR"""
        lb = self.params["lookback"]
        price_move = self.close[0] - self.close[-lb]
        threshold = self.atr[0] * self.params["atr_multiplier"]
        ok = price_move > threshold
        msg = f"{self.get_name()} LONG move={price_move:.2f} > threshold={threshold:.2f}"
        return ok, msg

    def short(self):
        """Enter short when price breaks down by more than N * ATR"""
        lb = self.params["lookback"]
        price_move = self.close[-lb] - self.close[0]
        threshold = self.atr[0] * self.params["atr_multiplier"]
        ok = price_move > threshold
        msg = f"{self.get_name()} SHORT move={price_move:.2f} > threshold={threshold:.2f}"
        return ok, msg

    def exit_long(self):
        """Exit long when price reverses by ATR amount"""
        lb = self.params["lookback"]
        price_move = self.close[-lb] - self.close[0]  # Negative move
        threshold = self.atr[0] * self.params["atr_multiplier"]
        ok = price_move > threshold
        msg = f"{self.get_name()} exit LONG (reversal) move={price_move:.2f}"
        return ok, msg

    def exit_short(self):
        """Exit short when price reverses by ATR amount"""
        lb = self.params["lookback"]
        price_move = self.close[0] - self.close[-lb]  # Positive move
        threshold = self.atr[0] * self.params["atr_multiplier"]
        ok = price_move > threshold
        msg = f"{self.get_name()} exit SHORT (reversal) move={price_move:.2f}"
        return ok, msg


class ATRChannelCond(Condition):
    """
    ATR Channel - Mean reversion using ATR bands around moving average
    Similar to Bollinger Bands but uses ATR instead of standard deviation
    """
    default_params = {
        "ma_period": 20,
        "atr_period": 14,
        "atr_multiplier": 2.0,  # Distance from MA in ATR units
        "ma_type": "ema",
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close
        self.atr = bt.indicators.ATR(high, low, close, period=self.params["atr_period"])

        # Create MA based on type
        if self.params["ma_type"].lower() == "sma":
            self.ma = bt.indicators.SMA(close, period=self.params["ma_period"])
        else:
            self.ma = bt.indicators.EMA(close, period=self.params["ma_period"])

    def get_name(self):
        return f"ATR_Channel({self.params['ma_period']},{self.params['atr_multiplier']})"

    def _upper_band(self):
        return self.ma[0] + (self.atr[0] * self.params["atr_multiplier"])

    def _lower_band(self):
        return self.ma[0] - (self.atr[0] * self.params["atr_multiplier"])

    def long(self):
        """Enter long when price touches/breaks below lower ATR band"""
        lower = self._lower_band()
        ok = self.close[0] <= lower
        msg = f"{self.get_name()} LONG price={self.close[0]:.2f} <= lower={lower:.2f}"
        return ok, msg

    def short(self):
        """Enter short when price touches/breaks above upper ATR band"""
        upper = self._upper_band()
        ok = self.close[0] >= upper
        msg = f"{self.get_name()} SHORT price={self.close[0]:.2f} >= upper={upper:.2f}"
        return ok, msg

    def exit_long(self):
        """Exit long when price returns to MA"""
        ok = self.close[0] >= self.ma[0]
        msg = f"{self.get_name()} exit LONG price={self.close[0]:.2f} >= MA={self.ma[0]:.2f}"
        return ok, msg

    def exit_short(self):
        """Exit short when price returns to MA"""
        ok = self.close[0] <= self.ma[0]
        msg = f"{self.get_name()} exit SHORT price={self.close[0]:.2f} <= MA={self.ma[0]:.2f}"
        return ok, msg


class KeltnerChannelCond(Condition):
    """
    Keltner Channel - Mean Reversion (similar to Bollinger Bands but uses ATR)
    """
    default_params = {
        "ma_period": 20,
        "atr_period": 10,
        "atr_multiplier": 2.0,
        "ma_type": "ema",
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close
        self.atr = bt.indicators.ATR(high, low, close, period=self.params["atr_period"])

        if self.params["ma_type"].lower() == "sma":
            self.ma = bt.indicators.SMA(close, period=self.params["ma_period"])
        else:
            self.ma = bt.indicators.EMA(close, period=self.params["ma_period"])

    def get_name(self):
        return f"Keltner({self.params['ma_period']},{self.params['atr_multiplier']})"

    def _upper_band(self):
        return self.ma[0] + (self.atr[0] * self.params["atr_multiplier"])

    def _lower_band(self):
        return self.ma[0] - (self.atr[0] * self.params["atr_multiplier"])

    def long(self):
        """Enter long when price touches lower Keltner band"""
        lower = self._lower_band()
        ok = self.close[0] <= lower
        msg = f"{self.get_name()} LONG price={self.close[0]:.2f} <= lower={lower:.2f}"
        return ok, msg

    def short(self):
        """Enter short when price touches upper Keltner band"""
        upper = self._upper_band()
        ok = self.close[0] >= upper
        msg = f"{self.get_name()} SHORT price={self.close[0]:.2f} >= upper={upper:.2f}"
        return ok, msg

    def exit_long(self):
        """Exit long when price returns to middle line"""
        ok = self.close[0] >= self.ma[0]
        msg = f"{self.get_name()} exit LONG price={self.close[0]:.2f} >= MA={self.ma[0]:.2f}"
        return ok, msg

    def exit_short(self):
        """Exit short when price returns to middle line"""
        ok = self.close[0] <= self.ma[0]
        msg = f"{self.get_name()} exit SHORT price={self.close[0]:.2f} <= MA={self.ma[0]:.2f}"
        return ok, msg
