
from ._base_condition import Condition
import backtrader as bt


class ADXTrendCond(Condition):
    """
    ADX for trend strength - Trend Following version
    ADX > threshold = strong trend (trade with +DI/-DI direction)
    """
    default_params = {
        "period": 14,
        "adx_threshold": 25,  # ADX > 25 indicates trending market
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        # ADX indicator includes DI+ and DI-
        self.adx = bt.indicators.AverageDirectionalMovementIndex(
            high, low, close,
            period=self.params["period"]
        )

    def get_name(self):
        return f"ADX_Trend({self.params['period']},{self.params['adx_threshold']})"

    def long(self):
        """Enter long when ADX shows strong trend AND +DI > -DI"""
        strong_trend = self.adx.adx[0] > self.params["adx_threshold"]
        bullish_direction = self.adx.plusDI[0] > self.adx.minusDI[0]
        ok = strong_trend and bullish_direction
        msg = f"{self.get_name()} LONG ADX={self.adx.adx[0]:.2f} +DI={self.adx.plusDI[0]:.2f} -DI={self.adx.minusDI[0]:.2f}"
        return ok, msg

    def short(self):
        """Enter short when ADX shows strong trend AND -DI > +DI"""
        strong_trend = self.adx.adx[0] > self.params["adx_threshold"]
        bearish_direction = self.adx.minusDI[0] > self.adx.plusDI[0]
        ok = strong_trend and bearish_direction
        msg = f"{self.get_name()} SHORT ADX={self.adx.adx[0]:.2f} +DI={self.adx.plusDI[0]:.2f} -DI={self.adx.minusDI[0]:.2f}"
        return ok, msg

    def exit_long(self):
        """Exit long when trend weakens or direction reverses"""
        weak_trend = self.adx.adx[0] < self.params["adx_threshold"]
        direction_change = self.adx.minusDI[0] > self.adx.plusDI[0]
        ok = weak_trend or direction_change
        msg = f"{self.get_name()} exit LONG (trend weak or reversed) ADX={self.adx.adx[0]:.2f}"
        return ok, msg

    def exit_short(self):
        """Exit short when trend weakens or direction reverses"""
        weak_trend = self.adx.adx[0] < self.params["adx_threshold"]
        direction_change = self.adx.plusDI[0] > self.adx.minusDI[0]
        ok = weak_trend or direction_change
        msg = f"{self.get_name()} exit SHORT (trend weak or reversed) ADX={self.adx.adx[0]:.2f}"
        return ok, msg


class ADXMeanReversionCond(Condition):
    """
    ADX for mean reversion - enter when ADX is LOW (ranging market)
    Low ADX = no trend = good for mean reversion strategies
    """
    default_params = {
        "period": 14,
        "adx_low": 20,      # ADX < 20 indicates ranging/choppy market
        "adx_exit": 30,     # Exit when trend starts (ADX > 30)
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.adx = bt.indicators.AverageDirectionalMovementIndex(
            high, low, close,
            period=self.params["period"]
        )
        self.close = close

    def get_name(self):
        return f"ADX_MeanRev({self.params['period']},{self.params['adx_low']})"

    def long(self):
        """Enter long when ADX is low (ranging) AND price action suggests reversal"""
        ranging_market = self.adx.adx[0] < self.params["adx_low"]
        ok = ranging_market  # Can combine with other mean reversion signals
        msg = f"{self.get_name()} LONG (ranging market) ADX={self.adx.adx[0]:.2f} < {self.params['adx_low']}"
        return ok, msg

    def short(self):
        """Enter short when ADX is low (ranging) AND price action suggests reversal"""
        ranging_market = self.adx.adx[0] < self.params["adx_low"]
        ok = ranging_market
        msg = f"{self.get_name()} SHORT (ranging market) ADX={self.adx.adx[0]:.2f} < {self.params['adx_low']}"
        return ok, msg

    def exit_long(self):
        """Exit when trend starts forming (ADX rising above threshold)"""
        ok = self.adx.adx[0] > self.params["adx_exit"]
        msg = f"{self.get_name()} exit LONG (trend starting) ADX={self.adx.adx[0]:.2f} > {self.params['adx_exit']}"
        return ok, msg

    def exit_short(self):
        """Exit when trend starts forming (ADX rising above threshold)"""
        ok = self.adx.adx[0] > self.params["adx_exit"]
        msg = f"{self.get_name()} exit SHORT (trend starting) ADX={self.adx.adx[0]:.2f} > {self.params['adx_exit']}"
        return ok, msg
