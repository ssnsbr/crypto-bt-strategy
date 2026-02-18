import datetime
import backtrader as bt

from run_results.regime_analyser.regime_analyzer_helpers import P2Quantile, StreamingStats, TimeframeAlignment, ReturnStats, EWStreamingStats, TradePathStats


class RegimeFeature:
    def on_trade_open(self, trade):
        pass

    def on_bar(self):
        pass

    def on_trade_close(self, trade):
        pass

    def export(self) -> dict:
        return {}


class VolatilityFeature(RegimeFeature):
    """
    Volatility regime feature using:
        - ATR (LTF + HTF)
        - EW volatility (reactive)
        - Return-based volatility & entropy
        - MAE / MFE regime capture
        - HTF-LTF alignment
    """

    def __init__(self, analyzer):
        self.analyzer = analyzer

        # -------- LTF --------
        d = analyzer.data_ltf
        self.atr = bt.ind.ATR(d, period=14)
        self.atr_sma = bt.ind.SMA(self.atr, period=50)

        self.returns = ReturnStats()
        self.ew_atr = EWStreamingStats(alpha=0.2)

        # -------- HTF --------
        self.htf_enabled = hasattr(analyzer, "data_htf")
        if self.htf_enabled:
            d_htf = analyzer.data_htf
            self.atr_htf = bt.ind.ATR(d_htf, period=14)
            self.tf_align = TimeframeAlignment()

        # -------- Trade-path --------
        self.trade_path = None
        self.vol_at_mae = None
        self.vol_at_mfe = None

        # -------- Stats --------
        self.atr_stats = StreamingStats()
        self.atr_ratio_stats = StreamingStats()

        self.atr_percentile = P2Quantile(0.80)   # configurable percentile (e.g. 80%)

        # ---- ATR normalized ----
        self.atr_norm_stats = StreamingStats()   # atr / close

    # --------------------------------------------------

    def on_trade_open(self, trade):
        entry_price = trade.price
        direction = 1 if trade.size > 0 else -1

        self.trade_path = TradePathStats(entry_price, direction)
        self.vol_at_mae = None
        self.vol_at_mfe = None

        self.atr_norm_stats = StreamingStats()
        self.atr_percentile = P2Quantile(0.80)

        # reset streaming stats
        self.atr_stats = StreamingStats()
        self.atr_ratio_stats = StreamingStats()
        self.returns = ReturnStats()
        self.ew_atr = EWStreamingStats(alpha=0.2)

    # --------------------------------------------------
    def on_bar(self):

        price = self.analyzer.data_ltf.close[0]
        close = self.analyzer.data_ltf.close[0]

        # ---- ATR stats ----
        atr = self.atr[0]
        atr_sma = self.atr_sma[0]
        atr_ratio = atr / atr_sma if atr_sma else 0.0

        self.atr_stats.update(atr)
        self.atr_ratio_stats.update(atr_ratio)
        self.ew_atr.update(atr)
        self.atr_percentile.update(atr)

        # ---- Return-based volatility ----
        self.returns.update(price)

        # --- ATR normalized ---
        atr_norm = atr / close if close else 0.0
        self.atr_norm_stats.update(atr_norm)

        # ---- Trade path ----
        if self.trade_path:
            self.trade_path.update(price)

            # capture volatility regime at MAE / MFE
            if self.trade_path.t == self.trade_path.t_mae:
                self.vol_at_mae = atr

            if self.trade_path.t == self.trade_path.t_mfe:
                self.vol_at_mfe = atr

        # ---- HTF-LTF alignment ----
        if self.htf_enabled and len(self.analyzer.data_htf):
            self.tf_align.update(atr, self.atr_htf[0])

    # --------------------------------------------------
    def on_trade_close(self, trade):
        pass

    # --------------------------------------------------
    def export(self):
        out = {}

        # --- ATR core ---
        out.update({
            'atr_mean': self.atr_stats.mean,
            'atr_std': self.atr_stats.std(),
            'atr_slope': self.atr_stats.slope(),
            'atr_drift': self.atr_stats.drift(),
            'atr_iqr': self.atr_stats.iqr(),
        })

        # --- ATR ratio (compression / expansion) ---
        out.update({
            'atr_ratio_mean': self.atr_ratio_stats.mean,
            'atr_ratio_std': self.atr_ratio_stats.std(),
            'atr_ratio_slope': self.atr_ratio_stats.slope(),
        })

        # ---- ATR percentile ----
        out.update({'atr_pctl_80': self.atr_percentile.value()})
        # ---- Normalized ATR ----
        out.update({'atr_norm': self.atr_norm_stats.last,
                    'atr_norm_mean': self.atr_norm_stats.mean})

        # --- Reactive volatility ---
        out.update(self.ew_atr.export())

        # --- Return-based ---
        out.update(self.returns.export())

        # --- MAE / MFE ---
        if self.trade_path:
            out.update(self.trade_path.export())
            out.update({
                'atr_at_mae': self.vol_at_mae,
                'atr_at_mfe': self.vol_at_mfe,
            })

        # --- HTF alignment ---
        if self.htf_enabled:
            out.update(self.tf_align.export())

        return {f'vol_{k}': v for k, v in out.items()}


class StochRSI(bt.Indicator):
    lines = ('percK', 'percD',)
    params = (('rsi_period', 14), ('stoch_period', 14), ('smooth_k', 3), ('smooth_d', 3),)

    def __init__(self):
        rsi = bt.ind.RSI(self.data, period=self.p.rsi_period)
        highest_rsi = bt.ind.Highest(rsi, period=self.p.stoch_period)
        lowest_rsi = bt.ind.Lowest(rsi, period=self.p.stoch_period)
        stoch = (rsi - lowest_rsi) / (highest_rsi - lowest_rsi) * 100
        self.lines.percK = bt.ind.SMA(stoch, period=self.p.smooth_k)
        self.lines.percD = bt.ind.SMA(self.lines.percK, period=self.p.smooth_d)


class MomentumFeature(RegimeFeature):
    """
    Momentum / Balance regime feature

    Includes:
        RSI level, slope, distance from 50
        RSI variance / compression
        Stochastic RSI range
        MACD (value, histogram, slope)
        Return-based momentum structure
        HTF-LTF momentum alignment
    """

    def __init__(self, analyzer):
        self.analyzer = analyzer
        d = analyzer.data_ltf

        # ---------- RSI ----------
        self.rsi = bt.ind.RSI(d, period=14)
        self.rsi_stats = StreamingStats()
        self.rsi_slope_stats = StreamingStats()

        # ---------- Stochastic RSI ----------
        self.stoch = bt.ind.Stochastic(d, period=14, period_dfast=3, period_dslow=3)
        self.stoch_range = StreamingStats()

        # Then compute Stochastic on RSI
        self.stoch_rsi = StochRSI(d)
        self.stoch_rsi_range = StreamingStats()

        # ---------- MACD ----------
        self.macd = bt.ind.MACDHisto(d)
        self.macd_stats = StreamingStats()
        self.macd_hist_stats = StreamingStats()

        # ---------- Returns (momentum structure) ----------
        self.returns = ReturnStats()

        # ---------- HTF ----------
        self.htf_enabled = hasattr(analyzer, "data_htf")
        if self.htf_enabled:
            self.rsi_htf = bt.ind.RSI(analyzer.data_htf, period=14)
            self.tf_align = TimeframeAlignment()

        self.prev_rsi = None

    # --------------------------------------------------
    def on_trade_open(self, trade):
        self.rsi_stats = StreamingStats()
        self.rsi_slope_stats = StreamingStats()
        self.stoch_range = StreamingStats()
        self.stoch_rsi_range = StreamingStats()

        self.macd_stats = StreamingStats()
        self.macd_hist_stats = StreamingStats()
        self.returns = ReturnStats()
        self.prev_rsi = None

    # --------------------------------------------------
    def on_bar(self):
        price = self.analyzer.data_ltf.close[0]

        # ----- RSI -----
        rsi = self.rsi[0]
        self.rsi_stats.update(rsi)

        if self.prev_rsi is not None:
            self.rsi_slope_stats.update(rsi - self.prev_rsi)
        self.prev_rsi = rsi

        # ----- Stoch RSI Range -----
        stoch_range = abs(self.stoch.percK[0] - self.stoch.percD[0])
        self.stoch_range.update(stoch_range)
        # ----- Stoch RSI Range -----
        stoch_rsi_range = abs(self.stoch_rsi.percK[0] - self.stoch_rsi.percD[0])
        self.stoch_rsi_range.update(stoch_rsi_range)

        # ----- MACD -----
        macd_val = self.macd.macd[0]
        macd_hist = self.macd.histo[0]

        self.macd_stats.update(macd_val)
        self.macd_hist_stats.update(macd_hist)

        # ----- Return-based structure -----
        self.returns.update(price)

        # ----- HTF-LTF alignment -----
        if self.htf_enabled and len(self.analyzer.data_htf):
            self.tf_align.update(rsi, self.rsi_htf[0])

    # --------------------------------------------------
    def export(self):
        out = {}

        # ----- RSI -----
        out.update({
            'rsi_mean': self.rsi_stats.mean,
            'rsi_std': self.rsi_stats.std(),
            'rsi_slope': self.rsi_stats.slope(),
            'rsi_dist_50': self.rsi_stats.last - 50,
            'rsi_compression': self.rsi_stats.std(),  # low std = compression
        })

        # ----- RSI delta slope -----
        out.update({
            'rsi_delta_mean': self.rsi_slope_stats.mean,
            'rsi_delta_std': self.rsi_slope_stats.std(),
        })

        # ----- Stochastic RSI -----
        out.update({
            'stoch_range_mean': self.stoch_range.mean,
            'stoch_range_std': self.stoch_range.std(),
            'stoch_rsi_range_mean': self.stoch_rsi_range.mean,
            'stoch_rsi_range_std': self.stoch_rsi_range.std(),
        })

        # ----- MACD -----
        out.update({
            'macd_mean': self.macd_stats.mean,
            'macd_std': self.macd_stats.std(),
            'macd_slope': self.macd_stats.slope(),
            'macd_hist_mean': self.macd_hist_stats.mean,
            'macd_hist_slope': self.macd_hist_stats.slope(),
        })

        # ----- Return-based momentum -----
        out.update(self.returns.export())

        # ----- HTF alignment -----
        if self.htf_enabled:
            out.update(self.tf_align.export())

        return {f'mom_{k}': v for k, v in out.items()}


class TrendFeature(RegimeFeature):
    """
    Trend regime feature

    Captures:
        EMA level & slope
        EMA slope normalized by ATR
        Price distance from EMA (normalized)
        ADX (trend strength)
        Trend stability (variance of slope)
        HTF–LTF trend alignment
    """

    def __init__(self, analyzer):
        self.analyzer = analyzer
        d = analyzer.data_ltf

        # ---------- EMAs ----------
        self.ema_fast = bt.ind.EMA(d, period=20)
        self.ema_slow = bt.ind.EMA(d, period=50)

        self.ema_fast_stats = StreamingStats()
        self.ema_slow_stats = StreamingStats()
        self.ema_slope_stats = StreamingStats()
        self.ema_slope_norm_stats = StreamingStats()
        self.price_dist_ema_stats = StreamingStats()

        # ---------- Volatility normalization ----------
        self.atr = bt.ind.ATR(d, period=14)

        # ---------- ADX ----------
        self.adx = bt.ind.ADX(d, period=14)
        self.adx_stats = StreamingStats()

        # ---------- HTF ----------
        self.htf_enabled = hasattr(analyzer, "data_htf")
        if self.htf_enabled:
            self.ema_htf = bt.ind.EMA(analyzer.data_htf, period=50)
            self.atr_htf = bt.ind.ATR(analyzer.data_htf, period=14)
            self.tf_align = TimeframeAlignment()

        self.prev_ema = None

    # --------------------------------------------------
    def on_trade_open(self, trade):
        self.ema_fast_stats = StreamingStats()
        self.ema_slow_stats = StreamingStats()
        self.ema_slope_stats = StreamingStats()
        self.ema_slope_norm_stats = StreamingStats()
        self.price_dist_ema_stats = StreamingStats()
        self.adx_stats = StreamingStats()
        self.prev_ema = None

    # --------------------------------------------------
    def on_bar(self):
        close = self.analyzer.data_ltf.close[0]

        ema_fast = self.ema_fast[0]
        ema_slow = self.ema_slow[0]
        atr = self.atr[0]

        # ----- EMA levels -----
        self.ema_fast_stats.update(ema_fast)
        self.ema_slow_stats.update(ema_slow)

        # ----- EMA slope -----
        if self.prev_ema is not None:
            slope = ema_fast - self.prev_ema
            self.ema_slope_stats.update(slope)

            # ATR-normalized slope
            self.ema_slope_norm_stats.update(
                slope / (atr + 1e-9)
            )

        self.prev_ema = ema_fast

        # ----- Price distance from EMA -----
        self.price_dist_ema_stats.update(
            (close - ema_fast) / (atr + 1e-9)
        )

        # ----- ADX -----
        self.adx_stats.update(self.adx[0])

        # ----- HTF alignment -----
        if self.htf_enabled and len(self.analyzer.data_htf):
            htf_slope = (
                self.ema_htf[0] - self.ema_htf[-1]
                if len(self.analyzer.data_htf) > 1 else 0
            )
            self.tf_align.update(
                self.ema_slope_stats.last or 0.0,
                htf_slope / (self.atr_htf[0] + 1e-9)
            )

    # --------------------------------------------------
    def export(self):
        out = {}

        # ----- EMA slopes -----
        out.update({
            'ema_slope_mean': self.ema_slope_stats.mean,
            'ema_slope_std': self.ema_slope_stats.std(),
            'ema_slope_norm_mean': self.ema_slope_norm_stats.mean,
            'ema_slope_norm_std': self.ema_slope_norm_stats.std(),
        })

        # ----- Price location -----
        out.update({
            'price_dist_ema_mean': self.price_dist_ema_stats.mean,
            'price_dist_ema_std': self.price_dist_ema_stats.std(),
        })

        # ----- Trend strength -----
        out.update({
            'adx_mean': self.adx_stats.mean,
            'adx_std': self.adx_stats.std(),
            'adx_slope': self.adx_stats.slope(),
        })

        # ----- HTF alignment -----
        if self.htf_enabled:
            out.update(self.tf_align.export())

        return {f'trend_{k}': v for k, v in out.items()}


class ParticipationFeature(RegimeFeature):
    """
    Participation / Liquidity regime feature

    Captures:
        Volume level, trend, compression
        Volume Z-score
        Volume ratio (vol / vol_sma)
        Volume slope
        Volume-Price agreement
        HTF-LTF participation alignment
    """

    def __init__(self, analyzer):
        self.analyzer = analyzer
        d = analyzer.data_ltf

        # ---------- Volume ----------
        self.volume = d.volume
        self.vol_sma = bt.ind.SMA(self.volume, period=50)

        self.vol_stats = StreamingStats()
        self.vol_ratio_stats = StreamingStats()
        self.vol_slope_stats = StreamingStats()

        # ---------- Volume-price relationship ----------
        self.vol_price_corr = StreamingStats()

        # ---------- HTF ----------
        self.htf_enabled = hasattr(analyzer, "data_htf")
        if self.htf_enabled:
            self.vol_htf = analyzer.data_htf.volume
            self.tf_align = TimeframeAlignment()

        self.prev_vol = None
        self.prev_price = None

    # --------------------------------------------------
    def on_trade_open(self, trade):
        self.vol_stats = StreamingStats()
        self.vol_ratio_stats = StreamingStats()
        self.vol_slope_stats = StreamingStats()
        self.vol_price_corr = StreamingStats()

        self.prev_vol = None
        self.prev_price = None

    # --------------------------------------------------
    def on_bar(self):
        close = self.analyzer.data_ltf.close[0]
        vol = self.volume[0]
        vol_sma = self.vol_sma[0]

        # ----- Volume core -----
        self.vol_stats.update(vol)

        # ----- Volume ratio -----
        vol_ratio = vol / vol_sma if vol_sma else 0.0
        self.vol_ratio_stats.update(vol_ratio)

        # ----- Volume slope -----
        if self.prev_vol is not None:
            self.vol_slope_stats.update(vol - self.prev_vol)
        self.prev_vol = vol

        # ----- Volume-price agreement -----
        if self.prev_price is not None:
            price_move = close - self.prev_price
            agreement = vol * price_move
            self.vol_price_corr.update(agreement)

        self.prev_price = close

        # ----- HTF alignment -----
        if self.htf_enabled and len(self.analyzer.data_htf):
            self.tf_align.update(vol_ratio, self.vol_htf[0])

    # --------------------------------------------------
    def export(self):
        out = {}

        mean_vol = self.vol_stats.mean
        std_vol = self.vol_stats.std()

        out.update({
            # ----- Volume -----
            'volume_mean': mean_vol,
            'volume_std': std_vol,
            'volume_slope': self.vol_stats.slope(),

            # ----- Volume Z -----
            'volume_z': (
                (self.vol_stats.last - mean_vol) /
                (std_vol + 1e-9)
            ),

            # ----- Volume ratio -----
            'volume_ratio_mean': self.vol_ratio_stats.mean,
            'volume_ratio_std': self.vol_ratio_stats.std(),
            'volume_ratio_slope': self.vol_ratio_stats.slope(),

            # ----- Volume-price -----
            'vol_price_agreement_mean': self.vol_price_corr.mean,
            'vol_price_agreement_std': self.vol_price_corr.std(),
        })

        # ----- HTF alignment -----
        if self.htf_enabled:
            out.update(self.tf_align.export())

        return {f'part_{k}': v for k, v in out.items()}


class TimeFeature(RegimeFeature):
    """
    Time / Session regime feature

    Captures:
        Bar index in trade
        Minute-of-day, Hour-of-day
        Day-of-week
        Session participation (NY / London / Asia)
        Time-in-trade structure
        HTF-LTF time alignment (optional)
    """

    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.data = analyzer.data_ltf

        # ---------- Time stats ----------
        self.bar_index_stats = StreamingStats()
        self.minute_stats = StreamingStats()
        self.hour_stats = StreamingStats()
        self.dow_stats = StreamingStats()

        # ---------- Trade time ----------
        self.trade_start_bar = None

        # ---------- HTF ----------
        self.htf_enabled = hasattr(analyzer, "data_htf")
        if self.htf_enabled:
            self.htf_minute_stats = StreamingStats()
            self.tf_align = TimeframeAlignment()

    # --------------------------------------------------
    def on_trade_open(self, trade):
        self.bar_index_stats = StreamingStats()
        self.minute_stats = StreamingStats()
        self.hour_stats = StreamingStats()
        self.dow_stats = StreamingStats()

        self.trade_start_bar = len(self.data)

    # --------------------------------------------------
    def on_bar(self):
        dt = self.data.datetime.datetime(0)

        minute = dt.hour * 60 + dt.minute
        hour = dt.hour
        dow = dt.weekday()

        # ----- In-trade bar index -----
        if self.trade_start_bar is not None:
            bar_index = len(self.data) - self.trade_start_bar
            self.bar_index_stats.update(bar_index)

        # ----- Time-of-day -----
        self.minute_stats.update(minute)
        self.hour_stats.update(hour)
        self.dow_stats.update(dow)

        # ----- HTF alignment -----
        if self.htf_enabled and len(self.analyzer.data_htf):
            htf_dt = self.analyzer.data_htf.datetime.datetime(0)
            htf_minute = htf_dt.hour * 60 + htf_dt.minute

            self.tf_align.update(minute, htf_minute)

    # --------------------------------------------------
    def export(self):
        out = {}

        # ----- Time-in-trade -----
        out.update({
            'bars_in_trade_mean': self.bar_index_stats.mean,
            'bars_in_trade_std': self.bar_index_stats.std(),
        })

        # ----- Minute / Hour / DOW -----
        out.update({
            'minute_mean': self.minute_stats.mean,
            'minute_std': self.minute_stats.std(),
            'hour_mean': self.hour_stats.mean,
            'hour_std': self.hour_stats.std(),
            'dow_mean': self.dow_stats.mean,
            'dow_std': self.dow_stats.std(),
        })

        # ----- HTF alignment -----
        if self.htf_enabled:
            out.update(self.tf_align.export())

        return {f'time_{k}': v for k, v in out.items()}
