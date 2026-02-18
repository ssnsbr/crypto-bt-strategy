# config.py includes class StrategyConfig,TechnicalConfig
# actions.py for later use, includes all actions related
# strategy.py is the main strategy and positions
# state.py is for states and related logics
# tools.py is for indicators utils and other
# market_context.py is for market context anything related to price and indicators

# ============================================================================
# config.py - Configuration for Trading System
# ============================================================================

from dataclasses import dataclass, field
from typing import List


@dataclass
class TimeFrame:
    """Time frame definitions and utilities"""
    tf_1min: int = 1
    tf_5min: int = 5
    tf_15min: int = 15
    tf_30min: int = 30
    tf_1hour: int = 60
    tf_4hour: int = 240
    tf_1day: int = 1440
    tf_1week: int = 10080

    tf_list: List[int] = field(default_factory=lambda: [1, 5, 15, 30, 60, 240, 1440, 10080])

    def higher_tf(self, tf: int, steps: int = 1) -> int:
        """Get higher timeframe"""
        try:
            _index = self.tf_list.index(tf)
            if _index + steps < len(self.tf_list):
                return self.tf_list[_index + steps]
            return self.tf_list[-1]  # Return highest if exceeded
        except ValueError:
            # If tf not in list, return next higher
            for higher in self.tf_list:
                if higher > tf:
                    return higher
            return self.tf_list[-1]

    def lower_tf(self, tf: int, steps: int = 1) -> int:
        """Get lower timeframe"""
        try:
            _index = self.tf_list.index(tf)
            if _index - steps >= 0:
                return self.tf_list[_index - steps]
            return self.tf_list[0]  # Return lowest if exceeded
        except ValueError:
            # If tf not in list, return next lower
            for lower in reversed(self.tf_list):
                if lower < tf:
                    return lower
            return self.tf_list[0]


@dataclass
class TechnicalConfig:
    """Technical indicator configuration parameters"""

    # ========== Moving Averages ==========
    # Fast/Mid/Slow for trend identification
    ma_fast: int = 50
    ma_mid: int = 100
    ma_slow: int = 200

    # Additional EMAs for short-term signals
    ema_fast: int = 20
    ema_slow: int = 50

    # Multiple timeframe MAs (like in the video: 50, 100, 200 period)
    ma_periods: List[int] = field(default_factory=lambda: [9, 20, 50, 100, 240, 1440])

    # ========== State Detection Thresholds ==========
    # Trend confirmation - price distance from MA
    trend_threshold: float = 0.02  # 2% above MA to confirm trend

    # Correction detection - pullback percentage
    correction_threshold: float = 0.03  # 3% pullback for correction

    # Breakout/Momentum - significant move
    breakout_threshold: float = 0.05  # 5% move for breakout/momentum

    # Ranging market - price oscillation
    ranging_threshold: float = 0.02  # Price oscillating within 2% range

    # Strong momentum multiplier (for position sizing)
    strong_momentum_threshold: float = 0.10  # 10% move = strong momentum

    # ========== Momentum Indicators ==========
    rsi_period: int = 14
    rsi_ma_period: int = 14  # Smoothed RSI
    rsi_overbought: float = 70
    rsi_oversold: float = 30

    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    stoch_period: int = 14
    stoch_smooth_k: int = 3
    stoch_smooth_d: int = 3
    stoch_overbought: float = 80
    stoch_oversold: float = 20

    # ========== Trend Indicators ==========
    adx_period: int = 14
    adx_trending: float = 25  # ADX > 25 = trending
    adx_strong: float = 40    # ADX > 40 = strong trend

    # ========== Volatility Indicators ==========
    atr_period: int = 14
    atr_multiplier: float = 2.0  # For stop loss calculation

    bb_period: int = 20
    bb_std: float = 2.0

    # ========== ZigZag for Swing Detection ==========
    zigzag_threshold: float = 0.05  # 5% swing threshold

    # ========== Divergence Detection ==========
    divergence_lookback: int = 14  # Periods to look back for divergence

    # ========== Volume Analysis ==========
    volume_ma_period: int = 20
    volume_spike_threshold: float = 2.0  # 2x average volume = spike

    # Moving average periods
    ma_fast: int = 50
    ma_mid: int = 100
    ma_slow: int = 200
    ema_fast: int = 20
    ema_slow: int = 50

    # State detection thresholds
    trend_threshold: float = 0.02  # 2% above MA to confirm trend
    correction_threshold: float = 0.03  # 3% pullback for correction
    breakout_threshold: float = 0.05  # 5% move for breakout/momentum
    ranging_threshold: float = 0.02  # Price oscillating within 2% range

    # Momentum indicators
    rsi_period: int = 14
    rsi_ma_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    stoch_period: int = 14

    # Trend indicators
    adx_period: int = 14

    # Volatility indicators
    atr_period: int = 14
    bb_period: int = 20
    bb_std: int = 2

    # ZigZag
    zigzag_threshold: float = 0.05  # 5% swing threshold


@dataclass
class StrategyConfig:
    """Main strategy configuration - position sizing, risk, entry/exit rules"""

    # ========== Time Frame ==========
    time_frame: int = 1  # Default 1 minute
    timeframe_helper: TimeFrame = field(default_factory=TimeFrame)

    # ========== Position Sizing (Like video: layers at 50, 100, 200 MA) ==========
    # Base position per tranche
    base_position_pct: float = 0.25  # 25% of capital per entry
    max_tranches: int = 4  # Maximum number of entries (like video: at 50, 70, 100, 200)

    # Position allocation per tranche (should sum to 1.0)
    tranche_allocation: List[float] = field(default_factory=lambda: [0.15, 0.20, 0.25, 0.40])
    # Example: 15% at MA50, 20% at MA100, 25% at MA150, 40% at MA200

    # Momentum multiplier - increase size for breakout/momentum
    momentum_multiplier: float = 2.0  # 2x position for strong momentum

    time_frame = TimeFrame.tf_1min
    # Position sizing
    base_position_pct: float = 0.25  # 25% of capital per entry
    max_tranches: int = 4  # Maximum number of tranches
    momentum_multiplier: float = 2.0  # Position size multiplier for momentum


@dataclass
class RiskManagementConfig:
    # Maximum portfolio exposure
    max_portfolio_exposure: float = 1.0  # 100% max exposure

    # ========== Risk Management ==========
    # Stop loss
    stop_loss_pct: float = 0.10  # 10% stop loss
    use_atr_stop: bool = True  # Use ATR-based stop instead of fixed %
    atr_stop_multiplier: float = 2.0  # 2 * ATR for stop

    # Take profit
    take_profit_pct: float = 0.15  # 15% take profit target
    use_dynamic_tp: bool = True  # Adjust TP based on market state

    # Trailing stop (video: "fails fast")
    trailing_stop_trigger: float = 0.05  # Start trailing after 5% profit
    trailing_stop_distance: float = 0.05  # Trail by 5%
    use_atr_trailing: bool = True  # Use ATR for trailing distance

    # ========== Entry Rules (Trend + Breakout + Mean Reversion) ==========
    # Trend following entries
    enter_on_trend_at_mas: bool = True  # Enter at MA levels (like video)
    ma_entry_levels: List[int] = field(default_factory=lambda: [50, 100, 200])

    # Breakout entries
    enter_on_breakout: bool = True
    breakout_volume_confirm: bool = True  # Require volume confirmation

    # Mean reversion entries (correction in trend)
    enter_on_correction: bool = True  # Buy dips in uptrend
    correction_entry_levels: List[float] = field(default_factory=lambda: [0.03, 0.05, 0.08])
    # Enter at 3%, 5%, 8% pullbacks

    # ========== Exit Rules (Quick Exit if Wrong) ==========
    # Fast fail (video: "identifies wrong pretty much right away")
    quick_exit_enabled: bool = True
    quick_exit_loss_pct: float = 0.02  # Exit if 2% against position
    quick_exit_bars: int = 3  # Exit if wrong after N bars

    # Mean reversion profit taking
    mean_reversion_tp_pct: float = 0.10  # 10% target for mean reversion

    # Momentum ride
    momentum_hold_enabled: bool = True  # Hold winners longer
    momentum_trailing_only: bool = True  # Use trailing stop for momentum

    # ========== State Transition Rules ==========
    # How many bars to confirm state change
    state_confirmation_bars: int = 2

    # Minimum bars in state before transition
    min_bars_in_state: int = 3

    # ========== Filters ==========
    # Volume filter
    min_volume_filter: bool = True
    min_volume_multiplier: float = 0.5  # At least 50% of average volume

    # Volatility filter
    max_volatility_filter: bool = True
    max_atr_multiplier: float = 3.0  # Don't trade if ATR > 3x average

    # Time filters
    trade_start_hour: int = 9  # Market hours
    trade_end_hour: int = 16

    # ========== Technical Configuration ==========
    technical: TechnicalConfig = field(default_factory=TechnicalConfig)

    # ========== Performance Tracking ==========
    track_performance: bool = True
    performance_window: int = 100  # Last N trades to track

    # Risk management
    stop_loss_pct: float = 0.10  # 10% stop loss
    take_profit_pct: float = 0.15  # 15% take profit
    trailing_stop_trigger: float = 0.05  # Start trailing after 5% profit
    trailing_stop_distance: float = 0.05  # Trail by 5%


@dataclass
class BacktestConfig:
    """Backtesting specific configuration"""
    initial_capital: float = 100000.0
    commission: float = 0.001  # 0.1% commission
    slippage: float = 0.0005  # 0.05% slippage

    # Data requirements
    warmup_period: int = 200  # Bars needed to warm up indicators

    # Output
    save_trades: bool = True
    save_equity_curve: bool = True
    verbose: bool = True
