import numpy as np
import pandas as pd
from scipy.stats import linregress
from numpy.linalg import lstsq


# ------------------------------------------------------------
# Base Class
# ------------------------------------------------------------
class MarketRegimeBase:
    def __init__(self, name):
        self.name = name

    def compute(self, df: pd.DataFrame):
        """
        Return a score 0–100 or a label string.
        Override in children.
        """
        raise NotImplementedError


# ------------------------------------------------------------
# 2. Compression / Squeeze Regime
# ------------------------------------------------------------
class SqueezeRegime(MarketRegimeBase):
    def __init__(self, bb_period=20):
        super().__init__("squeeze")
        self.bb_period = bb_period

    def compute(self, df):
        std = df["close"].rolling(self.bb_period).std()
        bb_width = (std / df["close"]).iloc[-1]

        # Low width = close to breakout
        score = float(np.clip((1 - bb_width * 5) * 100, 0, 100))
        return score


# ------------------------------------------------------------
# 3. Trend Strength Regime
# ------------------------------------------------------------
class TrendStrengthRegime(MarketRegimeBase):
    def __init__(self, period=50):
        super().__init__("trend_strength")
        self.period = period

    def compute(self, df):
        closes = df["close"].tail(self.period).values
        x = np.arange(len(closes))
        slope, _, r_value, _, _ = linregress(x, closes)

        trend_quality = abs(r_value) * 100  # R² gives trend strength
        return float(np.clip(trend_quality, 0, 100))


# ------------------------------------------------------------
# 4. Liquidity Regime
# ------------------------------------------------------------
class LiquidityRegime(MarketRegimeBase):
    def __init__(self, vol_period=20):
        super().__init__("liquidity")
        self.vol_period = vol_period

    def compute(self, df):
        avg_vol = df["volume"].tail(self.vol_period).mean()
        last_vol = df["volume"].iloc[-1]

        liquidity_ratio = last_vol / avg_vol
        score = float(np.clip(liquidity_ratio * 50, 0, 100))
        return score


# ------------------------------------------------------------
# 5. Structural (Wave) Regime
# ------------------------------------------------------------
class StructuralRegime(MarketRegimeBase):
    def __init__(self, window=50):
        super().__init__("structure")
        self.window = window

    def compute(self, df):
        segment = df["close"].tail(self.window)
        diffs = np.abs(np.diff(segment))
        noise = diffs.mean()

        range_ = segment.max() - segment.min()
        shape_ratio = noise / range_ if range_ != 0 else 0

        score = float(np.clip((1 - shape_ratio) * 100, 0, 100))
        return score


# ------------------------------------------------------------
# 6. Hurst Exponent Regime
# ------------------------------------------------------------
class HurstRegime(MarketRegimeBase):
    def __init__(self, lags=20):
        super().__init__("hurst")
        self.lags = lags

    def hurst(self, ts):
        lags = range(2, self.lags)

        tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]

        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        hurst = poly[0] * 2.0

        return hurst

    def compute(self, df):
        h = self.hurst(df["close"].values[-200:])
        # Trending > .55, Mean-reversion < .45
        score = float(np.clip((h - 0.45) * 1000, 0, 100))
        return score


# ------------------------------------------------------------
# 7. Noise Regime
# ------------------------------------------------------------
class NoiseRegime(MarketRegimeBase):
    def __init__(self, period=20):
        super().__init__("noise")
        self.period = period

    def compute(self, df):
        o = df["open"].tail(self.period)
        c = df["close"].tail(self.period)
        h = df["high"].tail(self.period)
        _low = df["low"].tail(self.period)

        efficiency_ratio = abs(c.iloc[-1] - o.iloc[0]) / (h.max() - _low.min() + 1e-9)

        score = float(np.clip(efficiency_ratio * 100, 0, 100))
        return score


# ------------------------------------------------------------
# 8. HMM Regime (Machine Learning)
# ------------------------------------------------------------
class HMMRegime(MarketRegimeBase):
    def __init__(self):
        super().__init__("hmm")

    def compute(self, df):
        # Placeholder – ML model needed
        return 50.0


