import backtrader as bt

from run_results.regime_analyser.regime_analyzer_features import MomentumFeature, ParticipationFeature, TimeFeature, TrendFeature, VolatilityFeature
# from run_results.regime_analyzer_helpers import P2Quantile, StreamingStats, TimeframeAlignment, ReturnStats, EWStreamingStats, TradePathStats

# cerebro = bt.Cerebro()

# # data0 = 1m
# # data1 = 15m (example)
# cerebro.adddata(data0)
# cerebro.adddata(data1)

# cerebro.addstrategy(RegimeStrategy)
# cerebro.addanalyzer(InTradeStatsAnalyzer, _name='intrade')

# results = cerebro.run()

# analyzer = results[0].analyzers.intrade.get_analysis()

# import pandas as pd
# df = pd.DataFrame(analyzer)
# df.groupby(pd.qcut(df.htf_ema_slope_drift, 5))['pnl'].mean()
# df.groupby(pd.qcut(df.ltf_atr_mean, 5))['pnl'].mean()
# df.corr()['pnl'].sort_values()


# 6 How you’ll analyze this (very important)
# df.groupby(pd.qcut(df.atr_mean, 5))['pnl'].mean()
# df.groupby(pd.qcut(df.ema_slope_drift, 5))['pnl'].mean()

# class HTFRegimeAnalyzer(bt.Analyzer):
#     params = dict(
#         # ---- LTF params ----
#         atr_period=14,
#         rsi_period=14,
#         adx_period=14,
#         ema_period=50,
#         vol_period=20,

#         # ---- HTF params ----
#         htf_index=1,      # data1 by default
#     )
#     # =====================================================
#     # LIFECYCLE
#     # =====================================================

#     def start(self):
#         self.active = {}
#         self.results = []


class RegimeAnalyzer(bt.Analyzer):
    """
    For each Trade:
        For each indicator:
            At ENTRY:
                trade_id
                entry_time
                indicator_at_entry

            Inside the trade, track all indicators
            We will use Online aggregation (no heavy memory) and do NOT need to store full series.
            We Use streaming statistics per trade: Welford’s algorithm (mean & std)
            Drift: store entry value, update with last value
            (For each indicator while trade is open, compute):
                Central tendency : mean(X), median(X)
                Dispersion: std(X), iqr(X) 
                Drift (very important): slope(X) via linear regression,  (X_exit - X_entry) / duration
                Extremes:   min(X), max(X),    
                Variance...
                regime_flip_count...
                time....

            At EXIT:
                indicator_at_exit
                exit_reason (TP / SL / TIME / REVERSE)
                pnl_R

    List of Indicators
    Price, Time
    Participation:
        volume
        volume MA
        vol_z
        volume_ratio = volume / sma(volume)
        Liquidity & Volume Regime , Volume MA, Volume Z, Volume Ratio   

    Momentum / Balance
        rsi
        rsi_slope
        rsi_dist_50 = rsi - 50
        RSI Variance/ Compression
        Stochastic RSI Range
        MACD

    Trend 
        adx
        ma
        ema_slope
        ema_slope_norm = ema_slope / atr
        price_dist_ema = (close - ema) / atr

    Regime Directional Bias

    Volatility  done
        ATR: ATR, SMA(ATR, N), ATR percentile, ATR / price
        atr
        atr_norm = atr / close
        atr_z = (atr - mean_atr) / std_atr
        atr_slope

    Time
        bar_index_in_session
        Hour_of_day
        minute_of_day
        Session Filters NY,London,...
        Day of week

    Other-Must-have
        bb_width, bb_breakout
        return_volatility
        MAE (max adverse excursion)
        MFE (max favorable excursion)
        Regime at MAE
        Regime at MFE
        Time to MAE vs time to MFE
        Parkinson / Yang-Zhang Volatility
        Range High-Low Compression
        Volume Delta / CVD
        VWAP
        Hurst Exponent
        Z-Score of Returns
        Entropy

    Other-for-later
        ZigZag and Swings
        BoS,BoC,HH HL LH LL
        Pivot Points
    """
    pass

    """
    Collects multiple RegimeFeatures for each trade.
    """

    def __init__(self):
        self.features = {}

    def start(self):
        # Initialize each feature with the strategy / analyzer context
        self.features['vol'] = VolatilityFeature(self.strategy)
        self.features['mom'] = MomentumFeature(self.strategy)
        self.features['trend'] = TrendFeature(self.strategy)
        self.features['part'] = ParticipationFeature(self.strategy)
        self.features['time'] = TimeFeature(self.strategy)

        # Storage per trade
        self.trades_data = []

    # Called when trade opens
    def notify_trade(self, trade):
        bt.Trade
        if trade.isopen:
            for f in self.features.values():
                f.on_trade_open(trade)

        elif trade.isclosed:
            # Export feature stats at exit
            export_dict = {}
            for k, f in self.features.items():
                export_dict.update(f.export())
            export_dict.update({
                'trade_id': id(trade),
                'pnl': trade.pnl,
                'size': trade.size,
                'entry_bar': trade.baropen,
                'exit_bar': trade.barclose,
                'entry_price': trade.price,
                'exit_price': trade.price
            })
            self.trades_data.append(export_dict)

    # Called on each new bar
    def next(self):
        for f in self.features.values():
            f.on_bar()

    # Export after backtest
    def get_analysis(self):
        return self.trades_data
