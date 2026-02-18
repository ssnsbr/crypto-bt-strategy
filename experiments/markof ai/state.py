
# ============================================================================
# state.py - Market State Detection
# ============================================================================

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
from markof.config import StrategyConfig
from markof.market_context import MarketContext


class MarketState(Enum):
    """
    Market states based on the video:
    1. Undecided (starting, unclear)
    2. Trending (clear direction established)
    3. Correction (pullback in trend - BUY THE DIP / SELL THE RALLY)
    4. Breaking Out (momentum, going to the moon)
    5. Ranging (sideways, mean reversion)
    """
    UNDECIDED = 0

    # Trending states
    TRENDING_UP = 1
    TRENDING_DOWN = 2

    # Ranging/Mean reversion
    RANGING = 3

    # Correction states (buy dips/sell rallies)
    CORRECTING_IN_UPTREND = 11  # Pullback in uptrend - BUY
    CORRECTING_IN_DOWNTREND = 21  # Rally in downtrend - SELL

    # Breakout/Momentum states (going to the moon)
    BREAKING_OUT_UP = 12  # Strong upward breakout
    BREAKING_OUT_DOWN = 22  # Strong downward breakdown

    # End of trend signals
    TREND_EXHAUSTION_UP = 13  # Uptrend showing exhaustion
    TREND_EXHAUSTION_DOWN = 23  # Downtrend showing exhaustion

    def is_bullish_bias(self) -> bool:
        """Market has bullish bias (long opportunities)"""
        return self in [
            self.TRENDING_UP,
            self.CORRECTING_IN_UPTREND,
            self.BREAKING_OUT_UP
        ]

    def is_bearish_bias(self) -> bool:
        """Market has bearish bias (short opportunities)"""
        return self in [
            self.TRENDING_DOWN,
            self.CORRECTING_IN_DOWNTREND,
            self.BREAKING_OUT_DOWN
        ]

    def is_ranging(self) -> bool:
        """Market is ranging/sideways"""
        return self == self.RANGING

    def is_correction(self) -> bool:
        """Market is in correction (buy dip/sell rally opportunity)"""
        return self in [
            self.CORRECTING_IN_UPTREND,
            self.CORRECTING_IN_DOWNTREND
        ]

    def is_breakout(self) -> bool:
        """Market is breaking out (momentum play)"""
        return self in [
            self.BREAKING_OUT_UP,
            self.BREAKING_OUT_DOWN
        ]

    def is_exhaustion(self) -> bool:
        """Trend showing exhaustion (prepare to exit/reverse)"""
        return self in [
            self.TREND_EXHAUSTION_UP,
            self.TREND_EXHAUSTION_DOWN
        ]

    def get_direction(self) -> int:
        """Get direction: 1=bullish, -1=bearish, 0=neutral"""
        if self.is_bullish_bias():
            return 1
        elif self.is_bearish_bias():
            return -1
        return 0


@dataclass
class StateHistory:
    """Track state history for transitions"""
    current_state: MarketState
    previous_state: MarketState
    bars_in_state: int = 0
    state_change_count: int = 0

    def update(self, new_state: MarketState):
        """Update state history"""
        if new_state != self.current_state:
            self.previous_state = self.current_state
            self.current_state = new_state
            self.bars_in_state = 1
            self.state_change_count += 1
        else:
            self.bars_in_state += 1

    def just_changed(self) -> bool:
        """Did state just change?"""
        return self.bars_in_state == 1

    def stable(self, min_bars: int = 3) -> bool:
        """Is state stable (been in state for min bars)?"""
        return self.bars_in_state >= min_bars

# ============================================================================
# STATE DETECTOR
# ============================================================================


class StateDetector:
    """
    Detects market state using comprehensive technical analysis
    """

    def __init__(self, config: StrategyConfig):
        self.config = config
        self.state_history = StateHistory(
            current_state=MarketState.UNDECIDED,
            previous_state=MarketState.UNDECIDED
        )
        # Track recent price swings for correction detection
        self.recent_high: Optional[float] = None
        self.recent_low: Optional[float] = None

    def detect_state(self,
                     market_context: MarketContext) -> MarketState:
        """
        Detect market state using comprehensive technical analysis
        Priority order (like the video):
        1. Check for RANGING first (no directional bias)
        2. Check for BREAKOUT/BREAKDOWN (strong momentum)
        3. Check for TRENDING (established direction)
        4. Check for CORRECTION within trend (buy dip/sell rally)
        5. Check for EXHAUSTION (trend ending)
        """
        ctx = market_context
        current = self.state_history.current_state

        # Update price swing tracking
        self._update_swing_levels(ctx.price.high, ctx.price.low)

        # 1. RANGING MARKET - highest priority for risk management
        if self._is_ranging(ctx):
            new_state = MarketState.RANGING

        # 2. BREAKOUT/BREAKDOWN - catch momentum "going to the moon"
        elif self._is_breaking_out_up(ctx):
            new_state = MarketState.BREAKING_OUT_UP
        elif self._is_breaking_out_down(ctx):
            new_state = MarketState.BREAKING_OUT_DOWN

        # 3. TRENDING - established directional move
        elif self._is_trending_up(ctx):
            # Check for correction within uptrend (buy the dip)
            if self._is_correcting_in_uptrend(ctx, current):
                new_state = MarketState.CORRECTING_IN_UPTREND
            # Check for exhaustion (prepare to exit)
            elif self._is_trend_exhaustion_up(ctx, current):
                new_state = MarketState.TREND_EXHAUSTION_UP
            else:
                new_state = MarketState.TRENDING_UP

        elif self._is_trending_down(ctx):
            # Check for correction within downtrend (sell the rally)
            if self._is_correcting_in_downtrend(ctx, current):
                new_state = MarketState.CORRECTING_IN_DOWNTREND
            # Check for exhaustion
            elif self._is_trend_exhaustion_down(ctx, current):
                new_state = MarketState.TREND_EXHAUSTION_DOWN
            else:
                new_state = MarketState.TRENDING_DOWN

        else:
            new_state = MarketState.UNDECIDED

        # Update state history
        self.state_history.update(new_state)

        return new_state

    def detect_state(self,
                     market_context: MarketContext) -> MarketState:
        """
        Detect market state using comprehensive technical analysis
        Priority order (like the video):
        1. Check for RANGING first (no directional bias)
        2. Check for BREAKOUT/BREAKDOWN (strong momentum)
        3. Check for TRENDING (established direction)
        4. Check for CORRECTION within trend (buy dip/sell rally)
        5. Check for EXHAUSTION (trend ending)
        """
        ctx = market_context
        current = self.state_history.current_state

        # Update price swing tracking
        self._update_swing_levels(ctx.price.high, ctx.price.low)

        # 1. RANGING MARKET - highest priority for risk management
        if self._is_ranging(ctx):
            new_state = MarketState.RANGING

        # 2. BREAKOUT/BREAKDOWN - catch momentum "going to the moon"
        elif self._is_breaking_out_up(ctx):
            new_state = MarketState.BREAKING_OUT_UP
        elif self._is_breaking_out_down(ctx):
            new_state = MarketState.BREAKING_OUT_DOWN

        # 3. TRENDING - established directional move
        elif self._is_trending_up(ctx):
            # Check for correction within uptrend (buy the dip)
            if self._is_correcting_in_uptrend(ctx, current):
                new_state = MarketState.CORRECTING_IN_UPTREND
            # Check for exhaustion (prepare to exit)
            elif self._is_trend_exhaustion_up(ctx, current):
                new_state = MarketState.TREND_EXHAUSTION_UP
            else:
                new_state = MarketState.TRENDING_UP

        elif self._is_trending_down(ctx):
            # Check for correction within downtrend (sell the rally)
            if self._is_correcting_in_downtrend(ctx, current):
                new_state = MarketState.CORRECTING_IN_DOWNTREND
            # Check for exhaustion
            elif self._is_trend_exhaustion_down(ctx, current):
                new_state = MarketState.TREND_EXHAUSTION_DOWN
            else:
                new_state = MarketState.TRENDING_DOWN

        else:
            new_state = MarketState.UNDECIDED

        # Update state history
        self.state_history.update(new_state)

        return new_state

    def detect_state2(self,
                      market_context: MarketContext,
                      current_state: MarketState) -> MarketState:
        """
        Detect market state using comprehensive technical analysis
        """
        ctx = market_context
        # price = ctx.price.close

        # Check for RANGING market first
        if self._is_ranging(ctx):
            return MarketState.RANGING

        # Check for BREAKOUT states (highest priority after ranging)
        if self._is_breaking_out_up(ctx):
            return MarketState.BREAKING_OUT_UP
        elif self._is_breaking_out_down(ctx):
            return MarketState.BREAKING_OUT_DOWN

        # Check for TRENDING states
        if self._is_trending_up(ctx):
            # Check for correction within uptrend
            if self._is_correcting_in_uptrend(ctx, current_state):
                return MarketState.CORRECTING_IN_UPTREND
            return MarketState.TRENDING_UP

        elif self._is_trending_down(ctx):
            # Check for correction within downtrend
            if self._is_correcting_in_downtrend(ctx, current_state):
                return MarketState.CORRECTING_IN_DOWNTREND
            return MarketState.TRENDING_DOWN

        return MarketState.UNDECIDED

    # ========================================================================
    # RANGING DETECTION
    # ========================================================================

    def _is_ranging(self, ctx: MarketContext) -> bool:
        """
        Detect ranging/sideways market
        Video: "sometimes they don't break out, they just come back to mean"
        """
        conditions = []

        # 1. Low ADX (weak trend)
        conditions.append(ctx.trend.adx < 20)

        # 2. Price oscillating around MAs
        ma_mid = ctx.moving_averages.ma_mid
        price_range = abs(ctx.price.close - ma_mid) / ma_mid
        conditions.append(price_range < self.config.technical.ranging_threshold)

        # 3. RSI in middle range (not overbought/oversold)
        conditions.append(ctx.momentum.rsi_neutral)

        # 4. MAs not aligned (flat or choppy)
        conditions.append(not ctx.moving_averages.aligned_up and
                          not ctx.moving_averages.aligned_down)

        # 5. MAs converging (losing direction)
        conditions.append(ctx.moving_averages.mas_converging)

        # 6. Low volume (consolidation)
        conditions.append(ctx.volume.low_volume)

        # Need most conditions true
        return sum(conditions) >= 4

    def _is_ranging(self, ctx: MarketContext) -> bool:
        """Detect ranging/sideways market"""
        # Multiple conditions for ranging market
        conditions = []

        # 1. Low ADX (weak trend)
        conditions.append(ctx.trend.adx < 20)

        # 2. Price oscillating around MAs
        ma_mid = ctx.moving_averages.ma_mid
        price_range = abs(ctx.price.close - ma_mid) / ma_mid
        conditions.append(price_range < self.config.ranging_threshold)

        # 3. RSI in middle range (not overbought/oversold)
        conditions.append(30 < ctx.momentum.rsi < 70)

        # 4. MAs not aligned (flat or choppy)
        conditions.append(not ctx.moving_averages.aligned_up and
                          not ctx.moving_averages.aligned_down)

        # Need most conditions to be true
        return sum(conditions) >= 3

    # ========================================================================
    # BREAKOUT DETECTION (Going to the moon!)
    # ========================================================================

    def _is_breaking_out_up(self, ctx: MarketContext) -> bool:
        """
        Detect upward breakout - "going to the moon"
        Video: "if it's wrong and starts going to the moon, identify right away"
        """
        conditions = []

        # 1. Strong momentum (RSI extended)
        conditions.append(ctx.momentum.rsi_overbought)

        # 2. Price significantly above slow MA
        conditions.append(
            ctx.price_distance_from_slow_ma > self.config.technical.breakout_threshold
        )

        # 3. MACD strongly bullish
        conditions.append(ctx.momentum.macd_bullish)

        # 4. Strong ADX with bullish trend
        conditions.append(ctx.trend.strong_trend and ctx.trend.bullish_trend)

        # 5. MAs aligned up
        conditions.append(ctx.moving_averages.aligned_up)

        # 6. Price above BB upper band (expansion)
        conditions.append(ctx.price.close > ctx.volatility.bb_upper)

        # 7. Volume confirmation
        conditions.append(ctx.volume.high_volume)

        # 8. ZigZag confirms upswing
        conditions.append(ctx.zigzag.in_upswing)

        # Need strong confirmation (most conditions true)
        return sum(conditions) >= 5

    def _is_breaking_out_down(self, ctx: MarketContext) -> bool:
        """Detect downward breakout/breakdown"""
        conditions = []

        conditions.append(ctx.momentum.rsi_oversold)
        conditions.append(
            ctx.price_distance_from_slow_ma < -self.config.technical.breakout_threshold
        )
        conditions.append(ctx.momentum.macd_bearish)
        conditions.append(ctx.trend.strong_trend and ctx.trend.bearish_trend)
        conditions.append(ctx.moving_averages.aligned_down)
        conditions.append(ctx.price.close < ctx.volatility.bb_lower)
        conditions.append(ctx.volume.high_volume)
        conditions.append(ctx.zigzag.in_downswing)

        return sum(conditions) >= 5

    def _is_breaking_out_up(self, ctx: MarketContext) -> bool:
        """Detect upward breakout"""
        conditions = []

        # 1. Strong momentum (RSI overbought)
        conditions.append(ctx.momentum.rsi_overbought)

        # 2. Price significantly above slow MA
        conditions.append(ctx.price_distance_from_slow_ma > self.config.breakout_threshold)

        # 3. MACD bullish
        conditions.append(ctx.momentum.macd_bullish)

        # 4. Strong ADX
        conditions.append(ctx.trend.strong_trend and ctx.trend.bullish_trend)

        # 5. MAs aligned up
        conditions.append(ctx.moving_averages.aligned_up)

        # 6. Price above BB upper band (expansion)
        conditions.append(ctx.price.close > ctx.volatility.bb_upper)

        # Need strong confirmation (most conditions true)
        return sum(conditions) >= 4

    def _is_breaking_out_down(self, ctx: MarketContext) -> bool:
        """Detect downward breakout"""
        conditions = []

        conditions.append(ctx.momentum.rsi_oversold)
        conditions.append(ctx.price_distance_from_slow_ma < -self.config.breakout_threshold)
        conditions.append(ctx.momentum.macd_bearish)
        conditions.append(ctx.trend.strong_trend and ctx.trend.bearish_trend)
        conditions.append(ctx.moving_averages.aligned_down)
        conditions.append(ctx.price.close < ctx.volatility.bb_lower)

        return sum(conditions) >= 4

    # ========================================================================
    # TRENDING DETECTION
    # ========================================================================

    def _is_trending_up(self, ctx: MarketContext) -> bool:
        """
        Detect uptrend
        Video: "buy trend where is the trend? above 50, 100, 200 MA"
        """
        conditions = []

        # 1. MAs aligned up
        conditions.append(ctx.moving_averages.aligned_up)

        # 2. Price above MAs
        conditions.append(ctx.price_above_mas)

        # 3. ADX shows trending market with bullish bias
        conditions.append(ctx.trend.trending and ctx.trend.bullish_trend)

        # 4. MACD bullish
        conditions.append(ctx.momentum.macd_bullish)

        # 5. ZigZag shows uptrend
        conditions.append(ctx.zigzag.in_upswing)

        # 6. Recent higher highs
        conditions.append(ctx.zigzag.current_trend > 0)

        return sum(conditions) >= 4

    def _is_trending_down(self, ctx: MarketContext) -> bool:
        """Detect downtrend"""
        conditions = []

        conditions.append(ctx.moving_averages.aligned_down)
        conditions.append(ctx.price_below_mas)
        conditions.append(ctx.trend.trending and ctx.trend.bearish_trend)
        conditions.append(ctx.momentum.macd_bearish)
        conditions.append(ctx.zigzag.in_downswing)
        conditions.append(ctx.zigzag.current_trend < 0)

        return sum(conditions) >= 4

    def _is_trending_up(self, ctx: MarketContext) -> bool:
        """Detect uptrend"""
        conditions = []

        # 1. MAs aligned up
        conditions.append(ctx.moving_averages.aligned_up)

        # 2. Price above MAs
        conditions.append(ctx.price_above_mas)

        # 3. ADX shows trending market
        conditions.append(ctx.trend.trending and ctx.trend.bullish_trend)

        # 4. MACD bullish
        conditions.append(ctx.momentum.macd_bullish)

        # 5. ZigZag shows uptrend
        conditions.append(ctx.zigzag.current_trend > 0)

        return sum(conditions) >= 3

    def _is_trending_down(self, ctx: MarketContext) -> bool:
        """Detect downtrend"""
        conditions = []

        conditions.append(ctx.moving_averages.aligned_down)
        conditions.append(ctx.price_below_mas)
        conditions.append(ctx.trend.trending and ctx.trend.bearish_trend)
        conditions.append(ctx.momentum.macd_bearish)
        conditions.append(ctx.zigzag.current_trend < 0)

        return sum(conditions) >= 3

    # ========================================================================
    # CORRECTION DETECTION (Buy the dip / Sell the rally)
    # ========================================================================

    def _is_correcting_in_uptrend(self, ctx: MarketContext,
                                  current_state: MarketState) -> bool:
        """
        Detect correction/pullback in uptrend - BUY THE DIP
        Video: "reversion to the mean trade"
        Only detect if previously in uptrend
        """
        # Must be coming from uptrend or already in correction
        if not (current_state == MarketState.TRENDING_UP or
                current_state == MarketState.CORRECTING_IN_UPTREND):
            return False

        # Calculate pullback from recent high
        if self.recent_high is None:
            return False

        pullback_pct = ((self.recent_high - ctx.price.close) / self.recent_high) * 100

        # Pullback conditions
        conditions = []

        # 1. Significant pullback
        conditions.append(
            pullback_pct > self.config.technical.correction_threshold * 100
        )

        # 2. Price pulled back below fast MA
        conditions.append(ctx.price.close < ctx.moving_averages.ma_fast)

        # 3. RSI pulled back but not oversold
        conditions.append(30 < ctx.momentum.rsi < 50)

        # 4. Bullish divergence (price lower but RSI higher)
        conditions.append(ctx.divergences.rsi_bullish_divergence)

        # 5. Still above slow MA (trend intact)
        conditions.append(ctx.price.close > ctx.moving_averages.ma_slow)

        # 6. Volume declining (profit taking, not panic)
        conditions.append(ctx.volume.low_volume)

        return sum(conditions) >= 3

    def _is_correcting_in_downtrend(self, ctx: MarketContext,
                                    current_state: MarketState) -> bool:
        """
        Detect correction/rally in downtrend - SELL THE RALLY
        Video: "short that trade because it doesn't think it's going to moon"
        """
        # Must be coming from downtrend or already in correction
        if not (current_state == MarketState.TRENDING_DOWN or
                current_state == MarketState.CORRECTING_IN_DOWNTREND):
            return False

        # Calculate rally from recent low
        if self.recent_low is None:
            return False

        rally_pct = ((ctx.price.close - self.recent_low) / self.recent_low) * 100

        conditions = []

        conditions.append(
            rally_pct > self.config.technical.correction_threshold * 100
        )
        conditions.append(ctx.price.close > ctx.moving_averages.ma_fast)
        conditions.append(50 < ctx.momentum.rsi < 70)
        conditions.append(ctx.divergences.rsi_bearish_divergence)
        conditions.append(ctx.price.close < ctx.moving_averages.ma_slow)
        conditions.append(ctx.volume.low_volume)

        return sum(conditions) >= 3

    def _is_correcting_in_uptrend(self, ctx: MarketContext,
                                  current_state: MarketState) -> bool:
        """Detect correction/pullback in uptrend"""
        if current_state != MarketState.TRENDING_UP:
            return False

        # Check for pullback
        pullback = None
        # pullback = pullback_from_high_pct TODO

        # Pullback conditions
        conditions = []
        conditions.append(pullback > self.config.correction_threshold * 100)
        conditions.append(ctx.price.close < ctx.moving_averages.ma_fast)
        conditions.append(ctx.momentum.rsi < 50)  # RSI pulled back
        conditions.append(ctx.divergences.rsi_bullish_divergence)  # Bullish divergence

        return sum(conditions) >= 2

    def _is_correcting_in_downtrend(self, ctx: MarketContext,
                                    current_state: MarketState) -> bool:
        """Detect correction/rally in downtrend"""
        if current_state != MarketState.TRENDING_DOWN:
            return False
        rally = None
        # rally =  rally_from_low_pct TODO

        conditions = []
        conditions.append(rally > self.config.correction_threshold * 100)
        conditions.append(ctx.price.close > ctx.moving_averages.ma_fast)
        conditions.append(ctx.momentum.rsi > 50)
        conditions.append(ctx.divergences.rsi_bearish_divergence)

        return sum(conditions) >= 2

    # ========================================================================
    # EXHAUSTION DETECTION (Trend ending - prepare to exit)
    # ========================================================================

    def _is_trend_exhaustion_up(self, ctx: MarketContext,
                                current_state: MarketState) -> bool:
        """
        Detect uptrend exhaustion - signs trend is ending
        Video: "fails fast" - get out when wrong
        """
        if not current_state.is_bullish_bias():
            return False

        conditions = []

        # 1. RSI divergence (price higher but RSI lower)
        conditions.append(ctx.divergences.rsi_bearish_divergence)

        # 2. MACD losing momentum
        conditions.append(ctx.momentum.macd_bearish)

        # 3. Volume divergence (price up but volume down)
        conditions.append(ctx.divergences.volume_divergence)

        # 4. ADX declining (trend weakening)
        conditions.append(ctx.trend.adx < 30)

        # 5. Price far from MA (overextended)
        conditions.append(
            ctx.price_distance_from_slow_ma > self.config.technical.strong_momentum_threshold
        )

        # 6. MAs starting to flatten
        conditions.append(abs(ctx.moving_averages.ma_separation) < 2.0)

        return sum(conditions) >= 3

    def _is_trend_exhaustion_down(self, ctx: MarketContext,
                                  current_state: MarketState) -> bool:
        """Detect downtrend exhaustion"""
        if not current_state.is_bearish_bias():
            return False

        conditions = []

        conditions.append(ctx.divergences.rsi_bullish_divergence)
        conditions.append(ctx.momentum.macd_bullish)
        conditions.append(ctx.trend.adx < 30)
        conditions.append(
            ctx.price_distance_from_slow_ma < -self.config.technical.strong_momentum_threshold
        )
        conditions.append(abs(ctx.moving_averages.ma_separation) < 2.0)

        # Volume drying up
        conditions.append(ctx.volume.low_volume)

        return sum(conditions) >= 3

    # ========================================================================
    # HELPERS
    # ========================================================================

    def get_state_confidence(self, ctx: MarketContext) -> float:
        """
        Get confidence level in current state (0-1)
        More aligned indicators = higher confidence
        """
        score = 0.0
        total = 0.0

        # Trend alignment
        if ctx.moving_averages.aligned_up or ctx.moving_averages.aligned_down:
            score += 1
        total += 1

        # Momentum alignment
        if ctx.momentum.macd_bullish == ctx.trend.bullish_trend:
            score += 1
        total += 1

        # Volume confirmation
        if ctx.volume.volume_confirmation:
            score += 1
        total += 1

        # ADX strength
        if ctx.trend.trending:
            score += 1
        total += 1

        return score / total if total > 0 else 0.5

    def _update_swing_levels(self, high: float, low: float):
        """Track recent swing highs/lows for correction detection"""
        if self.recent_high is None or high > self.recent_high:
            self.recent_high = high
        if self.recent_low is None or low < self.recent_low:
            self.recent_low = low
