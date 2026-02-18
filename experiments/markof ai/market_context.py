
# ============================================================================
# market_context.py
# ============================================================================

from dataclasses import dataclass

from markof.tools import Divergences, MomentumIndicators, MovingAverages, PriceData, TrendIndicators, VolatilityIndicators, ZigZagData


@dataclass
class MarketContext:
    """
    Complete market context - all observable data
    This is PURE DATA - no logic, just observations
    """
    price: PriceData
    moving_averages: MovingAverages
    momentum: MomentumIndicators
    trend: TrendIndicators
    volatility: VolatilityIndicators
    divergences: Divergences
    zigzag: ZigZagData

    @property
    def price_distance_from_slow_ma(self) -> float:
        """Price distance from slow MA as percentage"""
        ma = self.moving_averages.ma_slow
        return (self.price.close - ma) / ma if ma > 0 else 0

    @property
    def price_above_mas(self) -> bool:
        """Price above all major MAs"""
        return (self.price.close > self.moving_averages.ma_fast and
                self.price.close > self.moving_averages.ma_mid and
                self.price.close > self.moving_averages.ma_slow)

    @property
    def price_below_mas(self) -> bool:
        """Price below all major MAs"""
        return (self.price.close < self.moving_averages.ma_fast and
                self.price.close < self.moving_averages.ma_mid and
                self.price.close < self.moving_averages.ma_slow)

    @property
    def ma_aligned_up(self) -> bool:
        """MAs aligned for uptrend"""
        return self.ma_fast > self.ma_mid > self.ma_slow

    @property
    def ma_aligned_down(self) -> bool:
        """MAs aligned for downtrend"""
        return self.ma_fast < self.ma_mid < self.ma_slow

    @property
    def price_distance_from_slow_ma(self) -> float:
        """Price distance from slow MA as percentage"""
        return (self.price - self.ma_slow) / self.ma_slow if self.ma_slow > 0 else 0


@dataclass
class TrendDetector:
    """
    """
    price: PriceData
    moving_averages: MovingAverages
    momentum: MomentumIndicators
    trend: TrendIndicators
    volatility: VolatilityIndicators
    divergences: Divergences
    zigzag: ZigZagData
# price: float
#     ma_fast: float
#     ma_mid: float
#     ma_slow: float
#     rsi: float
#     atr: float
    # Derived metrics

    @property
    def mega_trend(self) -> float:
        pass
        return -1 0 1

    @property
    def _trend(self) -> bool:
        """Price above all major MAs"""
        return (self.price.close > self.moving_averages.ma_fast and
                self.price.close > self.moving_averages.ma_mid and
                self.price.close > self.moving_averages.ma_slow)

    @property
    def trend(self) -> bool:
        """Price below all major MAs"""
        return (self.price.close < self.moving_averages.ma_fast and
                self.price.close < self.moving_averages.ma_mid and
                self.price.close < self.moving_averages.ma_slow)
