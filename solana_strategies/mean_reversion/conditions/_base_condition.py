

class Condition:
    def __init__(self):
        pass

    def get_params(self):
        return self.params

    def get_name(self):
        return "no name"

    def long(self):
        return False, ""

    def short(self):
        return False, ""

    def exit_long(self):
        return False, ""

    def exit_short(self):
        return False, ""


# conditions = [
#     ChaikinVolatilityCond(h, l, high_threshold=15),  # High CV
#     ATRBreakoutCond(h, l, c, atr_multiplier=2.0),
#     ADXTrendCond(h, l, c, adx_threshold=25)
# ]
# # Momentum trading in high volatility

# conditions = [
#     HistoricalVolatilityRankCond(c, high_rank=30),  # Low HVR
#     MeanReversionBBCond(c, period=20),
#     RSICond(c, oversold=30, overbought=70)
# ]
# # Mean reversion works best in low volatility

# conditions = [
#     ChaikinVolatilityBreakoutCond(h, l, c, squeeze_bars=5),
#     DonchianChannelCond(h, l, c, period=20),
#     VolumeSpikeCond(c, v, spike_multiplier=2.0)
# ]
# # Trade breakouts after volatility contraction

# # Basic Chaikin Volatility - Breakout on expansion
# chaikin_vol = ChaikinVolatilityCond(
#     data.high, data.low,
#     ema_period=10,
#     roc_period=10,
#     high_threshold=10,
#     low_threshold=-10
# )

# # Chaikin Volatility as filter - Only trade in expanding volatility
# chaikin_filter = ChaikinVolatilityFilterCond(
#     data.high, data.low,
#     regime="expanding",
#     expansion_threshold=5
# )

# # Volatility Squeeze Breakout - Classic pattern
# squeeze_breakout = ChaikinVolatilityBreakoutCond(
#     data.high, data.low, data.close,
#     squeeze_bars=5,
#     expansion_threshold=15
# )

# # Historical Volatility - Standard deviation approach
# hist_vol = HistoricalVolatilityCond(
#     data.close,
#     period=20,
#     annualize=True,
#     high_threshold=60,
#     low_threshold=25
# )

# # Historical Volatility Rank - Relative volatility
# hvr = HistoricalVolatilityRankCond(
#     data.close,
#     hv_period=20,
#     rank_period=252,
#     high_rank=80,
#     low_rank=20
# )

# conditions = [
#     PivotPointsCond(h, l, c),
#     MeanReversionBBCond(c, period=20),
#     ChaikinMoneyFlowCond(h, l, c, v, threshold=0.05)
# ]

# conditions = [
#     RSICond(c, oversold=30, overbought=70),
#     OBVCond(c, v, ma_period=20),
#     MFICond(h, l, c, v, oversold=20)
# ]

# conditions = [
#     DonchianChannelCond(h, l, c, period=20),
#     VolumeSpikeCond(c, v, spike_multiplier=2.0),
#     ADXTrendCond(h, l, c, adx_threshold=25)
# ]

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

# # Mean reversion combo: Low ADX + IBS oversold + ATR channel
# conditions_long = [
#     ADXMeanReversionCond(data.high, data.low, data.close, adx_low=20),
#     IBSCond(data.high, data.low, data.close, oversold=0.2),
#     ATRChannelCond(data.high, data.low, data.close, atr_multiplier=2.0)
# ]

# # Trend following combo: High ADX + ATR breakout + volatility filter
# conditions_long = [
#     ADXTrendCond(data.high, data.low, data.close, adx_threshold=25),
#     ATRBreakoutCond(data.high, data.low, data.close, atr_multiplier=1.5),
#     ATRVolatilityFilterCond(data.high, data.low, data.close, max_atr_pct=0.05)
# ]

# # IBS - Mean reversion (classic)
# ibs = IBSCond(data.high, data.low, data.close, oversold=0.15, overbought=0.85)

# # ADX - Trend following
# adx_trend = ADXTrendCond(data.high, data.low, data.close, period=14, adx_threshold=25)

# # ADX - Mean reversion (trade only in ranging markets)
# adx_range = ADXMeanReversionCond(data.high, data.low, data.close, adx_low=20, adx_exit=30)

# # ATR - Volatility filter (avoid dead and crazy markets)
# atr_filter = ATRVolatilityFilterCond(data.high, data.low, data.close,
#                                      min_atr_pct=0.01, max_atr_pct=0.04)

# # ATR - Breakout trading
# atr_breakout = ATRBreakoutCond(data.high, data.low, data.close,
#                                atr_multiplier=2.0, lookback=1)

# # ATR - Channel mean reversion (like Bollinger Bands)
# atr_channel = ATRChannelCond(data.high, data.low, data.close,
#                              ma_period=20, atr_multiplier=2.5)


# # Mean reversion with RSI
# rsi_mr = MeanReversionRSICond(data.close, period=14, oversold=20, overbought=80)

# # Mean reversion with Bollinger Bands
# bb_mr = MeanReversionBBCond(data.close, period=20, devfactor=2.5, exit_mid=True)

# # Mean reversion with Z-Score (statistical)
# zscore_mr = MeanReversionZScoreCond(data.close, entry_threshold=2.5, exit_threshold=0.5)

# # Mean reversion with CCI (extreme values)
# cci_mr = MeanReversionCCICond(data.high, data.low, data.close, oversold=-250, overbought=250)

# # Mean reversion with MACD histogram
# macd_mr = MeanReversionMACDCond(data.close, hist_extreme=1.0)


# # Conservative mean reversion (1% distance, exit at MA)
# mean_rev_conservative = MeanReversionPriceMACond(
#     data.close,
#     ma_type="ema",
#     period=20,
#     distance_pct=0.01,
#     exit_at_ma=True
# )

# # Aggressive mean reversion (3% distance, wait for opposite extreme)
# mean_rev_aggressive = MeanReversionPriceMACond(
#     data.close,
#     ma_type="sma",
#     period=50,
#     distance_pct=0.03,
#     exit_at_ma=False
# )

# # Fast mean reversion with Hull MA
# mean_rev_fast = MeanReversionPriceMACond(
#     data.close,
#     ma_type="hull",
#     period=10,
#     distance_pct=0.02
# )
# ```

# ## Visual Example:
# ```
# Price action:
#            MA (20)
#       /\    -----    /\
#      /  \          /    \
#     /    \        /      \
#    /      v------v        \

# TREND FOLLOWING:
#   Long:  ↑ (price crosses ABOVE MA)
#   Exit:  ↓ (price crosses BELOW MA)

# MEAN REVERSION:
#   Long:  ↓ (price 2%+ BELOW MA)
#   Exit:  ↑ (price returns TO/ABOVE MA)


#   # EMA-based trend following (default)
# trend_ema = TrendFollowPriceMACond(data.close, ma_type="ema", period=20)

# # Hull Moving Average (faster response)
# trend_hull = TrendFollowPriceMACond(data.close, ma_type="hull", period=50)

# # Simple Moving Average (smoother)
# trend_sma = TrendFollowPriceMACond(data.close, ma_type="sma", period=100)

# # Triple EMA (very smooth)
# trend_tema = TrendFollowPriceMACond(data.close, ma_type="tema", period=30)
