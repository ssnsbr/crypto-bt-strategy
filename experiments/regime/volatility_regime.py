
# ------------------------------------------------------------
# 1. Volatility Regime
# ------------------------------------------------------------
import numpy as np
from regime.base import MarketRegimeBase


# ------------------------------------------------------------
# 1. VOLATILITY REGIME
# ------------------------------------------------------------
class VolatilityRegime(MarketRegimeBase):
    def __init__(self, atr_period=14, lookback=100, bb_period=20):
        super().__init__("volatility")
        self.atr_period = atr_period
        self.lookback = lookback
        self.bb_period = bb_period

    def compute(self, df: pd.DataFrame):
        """
        Returns:
            {
                'score': 0–100,
                'label': 'low' | 'normal' | 'high' | 'ultra',
                'atr': float,
                'atr_ratio': float,
                'bb_width': float,
                'percentile': float
            }
        """

        # -----------------------------
        # ATR
        # -----------------------------
        hl = df["high"] - df["low"]
        hc = (df["high"] - df["close"].shift()).abs()
        lc = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)

        df["atr"] = tr.rolling(self.atr_period).mean()

        # -----------------------------
        # ATR Ratio = Current ATR / ATR lookback median
        # -----------------------------
        atr_now = df["atr"].iloc[-1]
        atr_med = df["atr"].iloc[-self.lookback:].median()

        if atr_med == 0 or pd.isna(atr_med):
            atr_ratio = 1.0
        else:
            atr_ratio = atr_now / atr_med

        # -----------------------------
        # Bollinger Band Width
        # -----------------------------
        mid = df["close"].rolling(self.bb_period).mean()
        std = df["close"].rolling(self.bb_period).std()
        upper = mid + 2 * std
        lower = mid - 2 * std

        df["bb_width"] = (upper - lower) / mid
        bb_now = df["bb_width"].iloc[-1]

        # -----------------------------
        # Percentile Rank of Volatility
        # -----------------------------
        bb_slice = df["bb_width"].iloc[-self.lookback:]
        percentile = scipy.stats.percentileofscore(bb_slice, bb_now)

        # -----------------------------
        # Convert to a 0–100 Volatility Score
        # -----------------------------
        # Weighting: ATR stronger than BB width
        score = (
            (min(atr_ratio, 4) / 4) * 0.6 +
            (percentile / 100) * 0.4
        ) * 100

        score = float(max(0, min(score, 100)))

        # -----------------------------
        # Regime Label
        # -----------------------------
        if score < 25:
            label = "low"
        elif score < 55:
            label = "normal"
        elif score < 80:
            label = "high"
        else:
            label = "ultra"

        return {
            "score": score,
            "label": label,
            "atr": float(atr_now),
            "atr_ratio": float(atr_ratio),
            "bb_width": float(bb_now),
            "percentile": float(percentile)
        }
