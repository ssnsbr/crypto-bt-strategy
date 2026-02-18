from ._base_condition import Condition
import backtrader as bt


class OBVCond(Condition):
    """
    On-Balance Volume - Volume trend confirmation
    Rising OBV confirms uptrend, falling OBV confirms downtrend
    """
    default_params = {
        "ma_period": 20,      # MA of OBV for trend
        "ma_type": "ema",
    }

    def __init__(self, close, volume, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.obv = bt.indicators.OBV(close, volume)

        if self.params["ma_type"].lower() == "sma":
            self.obv_ma = bt.indicators.SMA(self.obv, period=self.params["ma_period"])
        else:
            self.obv_ma = bt.indicators.EMA(self.obv, period=self.params["ma_period"])

    def get_name(self):
        return f"OBV({self.params['ma_period']})"

    def long(self):
        """Enter long when OBV crosses above its MA (volume accumulation)"""
        ok = self.obv[0] > self.obv_ma[0] and self.obv[-1] <= self.obv_ma[-1]
        msg = f"{self.get_name()} LONG OBV={self.obv[0]:.0f} crosses above MA={self.obv_ma[0]:.0f}"
        return ok, msg

    def short(self):
        """Enter short when OBV crosses below its MA (volume distribution)"""
        ok = self.obv[0] < self.obv_ma[0] and self.obv[-1] >= self.obv_ma[-1]
        msg = f"{self.get_name()} SHORT OBV={self.obv[0]:.0f} crosses below MA={self.obv_ma[0]:.0f}"
        return ok, msg

    def exit_long(self):
        """Exit long when OBV crosses back below MA"""
        ok = self.obv[0] < self.obv_ma[0] and self.obv[-1] >= self.obv_ma[-1]
        msg = f"{self.get_name()} exit LONG OBV crosses below MA"
        return ok, msg

    def exit_short(self):
        """Exit short when OBV crosses back above MA"""
        ok = self.obv[0] > self.obv_ma[0] and self.obv[-1] <= self.obv_ma[-1]
        msg = f"{self.get_name()} exit SHORT OBV crosses above MA"
        return ok, msg


class OBVDivergenceCond(Condition):
    """
    OBV Divergence - Price vs Volume divergence detection
    Bullish divergence: Price makes lower low, OBV makes higher low
    Bearish divergence: Price makes higher high, OBV makes lower high
    """
    default_params = {
        "lookback": 20,     # Period to look for divergence
        "min_swing": 0.02,  # Minimum 2% price move to count as swing
    }

    def __init__(self, close, volume, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close
        self.obv = bt.indicators.OBV(close, volume)

    def get_name(self):
        return f"OBV_Div({self.params['lookback']})"

    def _find_bullish_divergence(self):
        """Price lower low but OBV higher low"""
        lb = self.params["lookback"]

        # Current price lower than lookback
        price_lower = self.close[0] < self.close[-lb]
        # But OBV higher
        obv_higher = self.obv[0] > self.obv[-lb]
        # Significant move
        price_change = abs(self.close[0] - self.close[-lb]) / self.close[-lb]
        significant = price_change > self.params["min_swing"]

        return price_lower and obv_higher and significant

    def _find_bearish_divergence(self):
        """Price higher high but OBV lower high"""
        lb = self.params["lookback"]

        # Current price higher than lookback
        price_higher = self.close[0] > self.close[-lb]
        # But OBV lower
        obv_lower = self.obv[0] < self.obv[-lb]
        # Significant move
        price_change = abs(self.close[0] - self.close[-lb]) / self.close[-lb]
        significant = price_change > self.params["min_swing"]

        return price_higher and obv_lower and significant

    def long(self):
        """Enter long on bullish divergence"""
        ok = self._find_bullish_divergence()
        msg = f"{self.get_name()} LONG bullish divergence detected"
        return ok, msg

    def short(self):
        """Enter short on bearish divergence"""
        ok = self._find_bearish_divergence()
        msg = f"{self.get_name()} SHORT bearish divergence detected"
        return ok, msg

    def exit_long(self):
        """Exit on bearish divergence"""
        ok = self._find_bearish_divergence()
        msg = f"{self.get_name()} exit LONG bearish divergence"
        return ok, msg

    def exit_short(self):
        """Exit on bullish divergence"""
        ok = self._find_bullish_divergence()
        msg = f"{self.get_name()} exit SHORT bullish divergence"
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
