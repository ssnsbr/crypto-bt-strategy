
from ._base_condition import Condition
import backtrader as bt


class DonchianChannelCond(Condition):
    """
    Donchian Channel - Breakout trading system
    Buy at upper band breakout, sell at lower band breakout
    """
    default_params = {
        "period": 20,
        "breakout_type": "close",  # "close" or "touch" (high/low)
        "exit_opposite": False,     # Exit on opposite band or middle
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.high = high
        self.low = low
        self.close = close
        self.highest = bt.indicators.Highest(high, period=self.params["period"])
        self.lowest = bt.indicators.Lowest(low, period=self.params["period"])

    def get_name(self):
        return f"Donchian({self.params['period']})"

    def _middle_band(self):
        return (self.highest[0] + self.lowest[0]) / 2

    def long(self):
        """Enter long on breakout above upper band"""
        if self.params["breakout_type"] == "close":
            ok = self.close[0] > self.highest[-1]  # Close above previous highest
        else:
            ok = self.high[0] > self.highest[-1]   # Touch above previous highest

        msg = f"{self.get_name()} LONG breakout above {self.highest[-1]:.2f}"
        return ok, msg

    def short(self):
        """Enter short on breakdown below lower band"""
        if self.params["breakout_type"] == "close":
            ok = self.close[0] < self.lowest[-1]   # Close below previous lowest
        else:
            ok = self.low[0] < self.lowest[-1]     # Touch below previous lowest

        msg = f"{self.get_name()} SHORT breakdown below {self.lowest[-1]:.2f}"
        return ok, msg

    def exit_long(self):
        """Exit long at opposite band or middle"""
        if self.params["exit_opposite"]:
            ok = self.close[0] < self.lowest[0]
            msg = f"{self.get_name()} exit LONG at lower band {self.lowest[0]:.2f}"
        else:
            middle = self._middle_band()
            ok = self.close[0] < middle
            msg = f"{self.get_name()} exit LONG at middle {middle:.2f}"
        return ok, msg

    def exit_short(self):
        """Exit short at opposite band or middle"""
        if self.params["exit_opposite"]:
            ok = self.close[0] > self.highest[0]
            msg = f"{self.get_name()} exit SHORT at upper band {self.highest[0]:.2f}"
        else:
            middle = self._middle_band()
            ok = self.close[0] > middle
            msg = f"{self.get_name()} exit SHORT at middle {middle:.2f}"
        return ok, msg


class IchimokuCond(Condition):
    """
    Ichimoku Cloud - Comprehensive trend system
    Simplified version focusing on key signals
    """
    default_params = {
        "tenkan": 9,    # Conversion line
        "kijun": 26,    # Base line
        "senkou": 52,   # Leading span B
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close
        self.ichimoku = bt.indicators.Ichimoku(
            high, low, close,
            tenkan=self.params["tenkan"],
            kijun=self.params["kijun"],
            senkou=self.params["senkou"]
        )

    def get_name(self):
        return f"Ichimoku({self.params['tenkan']},{self.params['kijun']})"

    def long(self):
        """Enter long when price above cloud and TK cross bullish"""
        # Price above cloud
        above_cloud = self.close[0] > self.ichimoku.senkou_span_a[0]
        # Tenkan crosses above Kijun
        tk_cross = (self.ichimoku.tenkan_sen[0] > self.ichimoku.kijun_sen[0] and
                    self.ichimoku.tenkan_sen[-1] <= self.ichimoku.kijun_sen[-1])

        ok = above_cloud and tk_cross
        msg = f"{self.get_name()} LONG TK bullish cross above cloud"
        return ok, msg

    def short(self):
        """Enter short when price below cloud and TK cross bearish"""
        # Price below cloud
        below_cloud = self.close[0] < self.ichimoku.senkou_span_a[0]
        # Tenkan crosses below Kijun
        tk_cross = (self.ichimoku.tenkan_sen[0] < self.ichimoku.kijun_sen[0] and
                    self.ichimoku.tenkan_sen[-1] >= self.ichimoku.kijun_sen[-1])

        ok = below_cloud and tk_cross
        msg = f"{self.get_name()} SHORT TK bearish cross below cloud"
        return ok, msg

    def exit_long(self):
        """Exit long when price enters cloud or TK bearish cross"""
        in_cloud = self.close[0] < self.ichimoku.senkou_span_a[0]
        tk_cross = (self.ichimoku.tenkan_sen[0] < self.ichimoku.kijun_sen[0] and
                    self.ichimoku.tenkan_sen[-1] >= self.ichimoku.kijun_sen[-1])

        ok = in_cloud or tk_cross
        msg = f"{self.get_name()} exit LONG signal reversal"
        return ok, msg

    def exit_short(self):
        """Exit short when price enters cloud or TK bullish cross"""
        in_cloud = self.close[0] > self.ichimoku.senkou_span_a[0]
        tk_cross = (self.ichimoku.tenkan_sen[0] > self.ichimoku.kijun_sen[0] and
                    self.ichimoku.tenkan_sen[-1] <= self.ichimoku.kijun_sen[-1])

        ok = in_cloud or tk_cross
        msg = f"{self.get_name()} exit SHORT signal reversal"
        return ok, msg


class MAEnvelopeCond(Condition):
    """
    Moving Average Envelope - Percentage bands around MA
    Mean reversion trading
    """
    default_params = {
        "ma_period": 20,
        "ma_type": "sma",
        "envelope_pct": 0.025,  # 2.5% bands
        "exit_ma": True,        # Exit at MA or opposite band
    }

    def __init__(self, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close

        if self.params["ma_type"].lower() == "sma":
            self.ma = bt.indicators.SMA(close, period=self.params["ma_period"])
        else:
            self.ma = bt.indicators.EMA(close, period=self.params["ma_period"])

    def get_name(self):
        return f"MAEnv({self.params['ma_period']},{self.params['envelope_pct']*100:.1f}%)"

    def _upper_band(self):
        return self.ma[0] * (1 + self.params["envelope_pct"])

    def _lower_band(self):
        return self.ma[0] * (1 - self.params["envelope_pct"])

    def long(self):
        """Enter long when price touches lower envelope"""
        lower = self._lower_band()
        ok = self.close[0] <= lower
        msg = f"{self.get_name()} LONG price={self.close[0]:.2f} <= lower={lower:.2f}"
        return ok, msg

    def short(self):
        """Enter short when price touches upper envelope"""
        upper = self._upper_band()
        ok = self.close[0] >= upper
        msg = f"{self.get_name()} SHORT price={self.close[0]:.2f} >= upper={upper:.2f}"
        return ok, msg

    def exit_long(self):
        """Exit long at MA or upper band"""
        if self.params["exit_ma"]:
            ok = self.close[0] >= self.ma[0]
            msg = f"{self.get_name()} exit LONG at MA={self.ma[0]:.2f}"
        else:
            upper = self._upper_band()
            ok = self.close[0] >= upper
            msg = f"{self.get_name()} exit LONG at upper={upper:.2f}"
        return ok, msg

    def exit_short(self):
        """Exit short at MA or lower band"""
        if self.params["exit_ma"]:
            ok = self.close[0] <= self.ma[0]
            msg = f"{self.get_name()} exit SHORT at MA={self.ma[0]:.2f}"
        else:
            lower = self._lower_band()
            ok = self.close[0] <= lower
            msg = f"{self.get_name()} exit SHORT at lower={lower:.2f}"
        return ok, msg


class ParabolicSARCond(Condition):
    """
    Parabolic SAR - Trend Following
    Long when price above SAR, short when below
    """
    default_params = {
        "af": 0.02,      # Acceleration factor
        "maximum": 0.2,  # Maximum acceleration
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close
        self.psar = bt.indicators.ParabolicSAR(
            high, low,
            af=self.params["af"],
            maximum=self.params["maximum"]
        )

    def get_name(self):
        return f"PSAR({self.params['af']},{self.params['maximum']})"

    def long(self):
        """Enter long when price crosses above SAR"""
        ok = self.close[0] > self.psar[0]
        msg = f"{self.get_name()} LONG price={self.close[0]:.2f} > SAR={self.psar[0]:.2f}"
        return ok, msg

    def short(self):
        """Enter short when price crosses below SAR"""
        ok = self.close[0] < self.psar[0]
        msg = f"{self.get_name()} SHORT price={self.close[0]:.2f} < SAR={self.psar[0]:.2f}"
        return ok, msg

    def exit_long(self):
        """Exit long when price crosses back below SAR"""
        ok = self.close[0] < self.psar[0]
        msg = f"{self.get_name()} exit LONG price={self.close[0]:.2f} < SAR={self.psar[0]:.2f}"
        return ok, msg

    def exit_short(self):
        """Exit short when price crosses back above SAR"""
        ok = self.close[0] > self.psar[0]
        msg = f"{self.get_name()} exit SHORT price={self.close[0]:.2f} > SAR={self.psar[0]:.2f}"
        return ok, msg


# # Donchian Channel - Classic breakout system
# donchian = DonchianChannelCond(
#     data.high, data.low, data.close,
#     period=20,
#     breakout_type="close",
#     exit_opposite=False
# )

# # OBV - Volume trend confirmation
# obv = OBVCond(data.close, data.volume, ma_period=20, ma_type="ema")

# # OBV Divergence - Spot reversals
# obv_div = OBVDivergenceCond(data.close, data.volume, lookback=20, min_swing=0.02)

# # MFI - Volume-weighted momentum
# mfi = MFICond(data.high, data.low, data.close, data.volume,
#               period=14, oversold=20, overbought=80)

# # Pivot Points - Intraday support/resistance
# pivots = PivotPointsCond(data.high, data.low, data.close, timeframe="daily")

# # Volume Spike - Detect breakouts
# vol_spike = VolumeSpikeCond(data.close, data.volume,
#                             spike_multiplier=2.5,
#                             price_confirmation=True)

# # Chaikin Money Flow - Smart money tracking
# cmf = ChaikinMoneyFlowCond(data.high, data.low, data.close, data.volume,
#                            period=20, threshold=0.05)
