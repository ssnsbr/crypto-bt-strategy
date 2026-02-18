

from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass
class PriceData:
    """Raw price data"""
    open: float
    high: float
    low: float
    close: float
    volume: float

# ============================================================================
#  TREND
# ============================================================================


@dataclass
class TrendIndicators:
    """Trend strength indicators"""
    adx: float  # Average Directional Index
    plus_di: float  # +DI
    minus_di: float  # -DI

    @property
    def trending(self) -> bool:
        """Strong trend if ADX > 25"""
        return self.adx > 25

    @property
    def strong_trend(self) -> bool:
        """Very strong trend if ADX > 40"""
        return self.adx > 40

    @property
    def bullish_trend(self) -> bool:
        return self.plus_di > self.minus_di

    @property
    def bearish_trend(self) -> bool:
        return self.minus_di > self.plus_di


@dataclass
class MovingAverages:
    """Moving average values"""
    tema_9: float  # 9
    tema_20: float
    tema_50: float
    tema_100: float
    tema_240: float
    tema_1440: float

    ema_9: float  # 9
    ema_20: float
    ema_50: float
    ema_100: float
    ema_240: float
    ema_1440: float

    sma_9: float  # 9
    sma_20: float
    sma_50: float
    sma_100: float
    sma_240: float
    sma_1440: float

    @property
    def aligned_up(self) -> bool:
        """MAs aligned for uptrend"""
        return self.ma_fast > self.ma_mid > self.ma_slow

    @property
    def aligned_down(self) -> bool:
        """MAs aligned for downtrend"""
        return self.ma_fast < self.ma_mid < self.ma_slow

# ============================================================================
#  MOMENTUM
# ============================================================================


@dataclass
class MomentumIndicators:
    """Momentum-based indicators"""
    rsi: float
    rsi_ma: float  # MA of RSI for smoothing
    macd: float
    macd_signal: float
    macd_histogram: float
    stochastic_k: float
    stochastic_d: float

    @property
    def rsi_overbought(self) -> bool:
        return self.rsi > 70

    @property
    def rsi_oversold(self) -> bool:
        return self.rsi < 30

    @property
    def macd_bullish(self) -> bool:
        return self.macd > self.macd_signal

    @property
    def macd_bearish(self) -> bool:
        return self.macd < self.macd_signal

    @property
    def stoch_overbought(self) -> bool:
        return self.stochastic_k > 80

    @property
    def stoch_oversold(self) -> bool:
        return self.stochastic_k < 20

# ============================================================================
#  VOTALITY
# ============================================================================


@dataclass
class VolatilityIndicators:
    """Volatility-based indicators"""
    atr: float  # Average True Range
    bb_upper: float  # Bollinger Band Upper
    bb_middle: float  # Bollinger Band Middle
    bb_lower: float  # Bollinger Band Lower
    bb_width: float  # BB Width (upper - lower)

    @property
    def bb_percent(self) -> float:
        """Price position within Bollinger Bands (0-1)"""
        if self.bb_width > 0:
            return (self.bb_middle - self.bb_lower) / self.bb_width
        return 0.5

    @property
    def high_volatility(self) -> bool:
        """High volatility if BB width is expanding"""
        # This would need historical comparison in real implementation
        return self.bb_width > self.bb_middle * 0.1


# ============================================================================
# DIVERGENCE DETECTOR
# ============================================================================
@dataclass
class Divergences:
    """Price-indicator divergences"""
    rsi_bullish_divergence: bool = False  # Price lower low, RSI higher low
    rsi_bearish_divergence: bool = False  # Price higher high, RSI lower high
    macd_bullish_divergence: bool = False
    macd_bearish_divergence: bool = False
    volume_divergence: bool = False  # Price up but volume down


class DivergenceDetector:
    """Detects price-indicator divergences"""

    def __init__(self, lookback: int = 14):
        self.lookback = lookback
        self.price_history = []
        self.rsi_history = []
        self.macd_history = []
        self.volume_history = []

    def update(self, price: float, rsi: float, macd: float, volume: float):
        """Update history"""
        self.price_history.append(price)
        self.rsi_history.append(rsi)
        self.macd_history.append(macd)
        self.volume_history.append(volume)

        # Keep only lookback periods
        if len(self.price_history) > self.lookback:
            self.price_history.pop(0)
            self.rsi_history.pop(0)
            self.macd_history.pop(0)
            self.volume_history.pop(0)

    def detect(self) -> Divergences:
        """Detect divergences"""
        if len(self.price_history) < self.lookback:
            return Divergences()

        # Simple divergence detection (can be made more sophisticated)
        rsi_bull_div = self._check_bullish_divergence(
            self.price_history, self.rsi_history
        )
        rsi_bear_div = self._check_bearish_divergence(
            self.price_history, self.rsi_history
        )
        macd_bull_div = self._check_bullish_divergence(
            self.price_history, self.macd_history
        )
        macd_bear_div = self._check_bearish_divergence(
            self.price_history, self.macd_history
        )

        # Volume divergence: price up but volume declining
        vol_div = False
        if len(self.volume_history) >= 5:
            price_trend_up = self.price_history[-1] > self.price_history[-5]
            volume_trend_down = self.volume_history[-1] < np.mean(self.volume_history[-5:])
            vol_div = price_trend_up and volume_trend_down

        return Divergences(
            rsi_bullish_divergence=rsi_bull_div,
            rsi_bearish_divergence=rsi_bear_div,
            macd_bullish_divergence=macd_bull_div,
            macd_bearish_divergence=macd_bear_div,
            volume_divergence=vol_div
        )

    def _check_bullish_divergence(self, prices: List[float],
                                  indicator: List[float]) -> bool:
        """Check for bullish divergence: lower low in price, higher low in indicator"""
        if len(prices) < 10:
            return False

        # Find recent lows
        price_low_1 = min(prices[-10:-5])
        price_low_2 = min(prices[-5:])
        ind_low_1 = min(indicator[-10:-5])
        ind_low_2 = min(indicator[-5:])

        # Bullish divergence: price making lower low, indicator making higher low
        return price_low_2 < price_low_1 and ind_low_2 > ind_low_1

    def _check_bearish_divergence(self, prices: List[float],
                                  indicator: List[float]) -> bool:
        """Check for bearish divergence: higher high in price, lower high in indicator"""
        if len(prices) < 10:
            return False

        price_high_1 = max(prices[-10:-5])
        price_high_2 = max(prices[-5:])
        ind_high_1 = max(indicator[-10:-5])
        ind_high_2 = max(indicator[-5:])

        # Bearish divergence: price making higher high, indicator making lower high
        return price_high_2 > price_high_1 and ind_high_2 < ind_high_1


# ============================================================================
# ZIGZAG CALCULATOR
# ============================================================================

@dataclass
class ZigZagData:
    """ZigZag indicator data for swing highs/lows"""
    last_swing_high: float = 0.0
    last_swing_low: float = 0.0
    current_trend: int = 0  # 1=up, -1=down, 0=undecided
    swing_magnitude: float = 0.0  # % move of last swing


class ZigZagCalculator:
    """Calculates ZigZag indicator for swing highs/lows"""

    def __init__(self, threshold_pct: float = 0.05):
        self.threshold = threshold_pct
        self.last_pivot_price = 0.0
        self.last_pivot_type = 0  # 1=high, -1=low
        self.current_trend = 0
        self.swing_high = 0.0
        self.swing_low = float('inf')

    def update(self, high: float, low: float, close: float) -> ZigZagData:
        """Update ZigZag calculation"""
        if self.last_pivot_price == 0:
            self.last_pivot_price = close
            self.swing_high = high
            self.swing_low = low
            return ZigZagData()

        # Check for new swing high
        if high > self.swing_high:
            self.swing_high = high
            pct_move = (high - self.last_pivot_price) / self.last_pivot_price
            if pct_move > self.threshold and self.last_pivot_type != 1:
                # New swing high confirmed
                self.last_pivot_price = high
                self.last_pivot_type = 1
                self.current_trend = 1
                magnitude = pct_move * 100
                self.swing_low = low  # Reset swing low
                return ZigZagData(
                    last_swing_high=high,
                    last_swing_low=self.swing_low,
                    current_trend=1,
                    swing_magnitude=magnitude
                )

        # Check for new swing low
        if low < self.swing_low:
            self.swing_low = low
            pct_move = (self.last_pivot_price - low) / self.last_pivot_price
            if pct_move > self.threshold and self.last_pivot_type != -1:
                # New swing low confirmed
                self.last_pivot_price = low
                self.last_pivot_type = -1
                self.current_trend = -1
                magnitude = pct_move * 100
                self.swing_high = high  # Reset swing high
                return ZigZagData(
                    last_swing_high=self.swing_high,
                    last_swing_low=low,
                    current_trend=-1,
                    swing_magnitude=magnitude
                )

        return ZigZagData(
            last_swing_high=self.swing_high,
            last_swing_low=self.swing_low,
            current_trend=self.current_trend,
            swing_magnitude=0.0
        )
