
# ============================================================================
# TRADING ACTIONS (What we do)
# ============================================================================

from dataclasses import dataclass
from enum import Enum

from markof.state import MarketContext, PositionState


# ============================================================================
# TRADING ACTIONS (Pure Decision)
# ============================================================================

class TradingAction(Enum):
    """Actions we can take"""
    DO_NOTHING = 0
    ENTER_LONG = 1
    ADD_TO_LONG = 2
    EXIT_LONG = 3
    ENTER_SHORT = 4
    ADD_TO_SHORT = 5
    EXIT_SHORT = 6
    FLIP_TO_LONG = 7  # Exit short and go long (fail fast)
    FLIP_TO_SHORT = 8  # Exit long and go short (fail fast)


@dataclass
class ActionSignal:
    """Represents a trading action decision with context"""
    action: TradingAction
    tranches: int = 1  # How many tranches to trade
    reason: str = ""  # Why we're taking this action
    is_urgent: bool = False  # For fail-fast exits

    @property
    def should_execute(self) -> bool:
        """Check if action should be executed"""
        return self.action != TradingAction.DO_NOTHING


# ============================================================================
# ACTION DECIDER (Decision Making)
# ============================================================================

class ActionDecider:
    """
    Decides what ACTION to take based on:
    1. Current market state (observation)
    2. Current position state (what we hold)
    3. State transitions (have we changed our mind?)
    """

    def __init__(self, config: StrategyConfig):
        self.config = config

    def decide_action(self,
                      market_state: MarketState,
                      prev_market_state: MarketState,
                      position_state: PositionState,
                      market_context: MarketContext) -> ActionSignal:
        """
        Main decision logic: what action should we take?

        This is where THINKING becomes ACTION
        """
        # Priority 1: Handle state transitions (fail fast)
        transition_action = self._check_state_transition(
            prev_market_state, market_state, position_state
        )
        if transition_action.should_execute:
            return transition_action

        # Priority 2: Check risk management exits
        exit_action = self._check_risk_exits(position_state, market_context)
        if exit_action.should_execute:
            return exit_action

        # Priority 3: Check for entries or additions
        entry_action = self._check_entry_opportunities(
            market_state, position_state, market_context
        )
        if entry_action.should_execute:
            return entry_action

        # Default: Do nothing
        return ActionSignal(TradingAction.DO_NOTHING)

    def _check_state_transition(self,
                                old_state: MarketState,
                                new_state: MarketState,
                                position_state: PositionState) -> ActionSignal:
        """
        Check if state transition requires immediate action (fail fast)

        If we changed our mind about market direction, exit immediately
        """
        # No state change
        if old_state == new_state:
            return ActionSignal(TradingAction.DO_NOTHING)

        # Changed from bullish to bearish - exit longs immediately
        if old_state.is_bullish_bias() and new_state.is_bearish_bias():
            if position_state.is_long:
                return ActionSignal(
                    TradingAction.EXIT_LONG,
                    reason=f"FAIL FAST: State changed {old_state.name} -> {new_state.name}",
                    is_urgent=True
                )

        # Changed from bearish to bullish - exit shorts immediately
        elif old_state.is_bearish_bias() and new_state.is_bullish_bias():
            if position_state.is_short:
                return ActionSignal(
                    TradingAction.EXIT_SHORT,
                    reason=f"FAIL FAST: State changed {old_state.name} -> {new_state.name}",
                    is_urgent=True
                )

        # Changed to undecided - exit everything
        elif new_state == MarketState.UNDECIDED and not position_state.is_flat:
            action = TradingAction.EXIT_LONG if position_state.is_long else TradingAction.EXIT_SHORT
            return ActionSignal(
                action,
                reason="Market became UNDECIDED",
                is_urgent=True
            )

        return ActionSignal(TradingAction.DO_NOTHING)

    def _check_risk_exits(self,
                          position_state: PositionState,
                          market_context: MarketContext) -> ActionSignal:
        """Check if we should exit due to risk management"""

        if position_state.is_flat:
            return ActionSignal(TradingAction.DO_NOTHING)

        price = market_context.price
        avg_entry = position_state.avg_entry_price

        if position_state.is_long:
            # Stop loss
            if price < avg_entry * (1 - self.config.stop_loss_pct):
                pnl_pct = ((price / avg_entry) - 1) * 100
                return ActionSignal(
                    TradingAction.EXIT_LONG,
                    reason=f"Stop loss hit: {pnl_pct:.2f}%"
                )

            # Take profit
            if price > avg_entry * (1 + self.config.take_profit_pct):
                pnl_pct = ((price / avg_entry) - 1) * 100
                return ActionSignal(
                    TradingAction.EXIT_LONG,
                    reason=f"Take profit hit: {pnl_pct:.2f}%"
                )

            # Trailing stop
            profit_pct = (position_state.highest_since_entry / avg_entry) - 1
            if profit_pct > self.config.trailing_stop_trigger:
                trail_level = position_state.highest_since_entry * (
                    1 - self.config.trailing_stop_distance
                )
                if price < trail_level:
                    pnl_pct = ((price / avg_entry) - 1) * 100
                    return ActionSignal(
                        TradingAction.EXIT_LONG,
                        reason=f"Trailing stop hit: {pnl_pct:.2f}%"
                    )

        elif position_state.is_short:
            # Stop loss
            if price > avg_entry * (1 + self.config.stop_loss_pct):
                pnl_pct = ((avg_entry / price) - 1) * 100
                return ActionSignal(
                    TradingAction.EXIT_SHORT,
                    reason=f"Stop loss hit: {pnl_pct:.2f}%"
                )

            # Take profit
            if price < avg_entry * (1 - self.config.take_profit_pct):
                pnl_pct = ((avg_entry / price) - 1) * 100
                return ActionSignal(
                    TradingAction.EXIT_SHORT,
                    reason=f"Take profit hit: {pnl_pct:.2f}%"
                )

            # Trailing stop
            profit_pct = 1 - (position_state.lowest_since_entry / avg_entry)
            if profit_pct > self.config.trailing_stop_trigger:
                trail_level = position_state.lowest_since_entry * (
                    1 + self.config.trailing_stop_distance
                )
                if price > trail_level:
                    pnl_pct = ((avg_entry / price) - 1) * 100
                    return ActionSignal(
                        TradingAction.EXIT_SHORT,
                        reason=f"Trailing stop hit: {pnl_pct:.2f}%"
                    )

        return ActionSignal(TradingAction.DO_NOTHING)

    def _check_entry_opportunities(self,
                                   market_state: MarketState,
                                   position_state: PositionState,
                                   market_context: MarketContext) -> ActionSignal:
        """Check if we should enter or add to position"""

        ctx = market_context

        # Can't add more if at max tranches
        if (not position_state.is_flat and
                position_state.tranche_count >= self.config.max_tranches):
            return ActionSignal(TradingAction.DO_NOTHING)

        # Entry logic based on market state
        if market_state == MarketState.UNDECIDED:
            return ActionSignal(TradingAction.DO_NOTHING)

        # LONG opportunities
        elif market_state == MarketState.TRENDING_UP:
            if position_state.is_flat:
                # Initial entry above MA50
                if ctx.price > ctx.ma_fast * (1 + self.config.trend_threshold):
                    return ActionSignal(
                        TradingAction.ENTER_LONG,
                        tranches=1,
                        reason="Trend up confirmed above MA50"
                    )
            else:
                # Add tranches at key levels
                return self._check_add_long_tranches(position_state, ctx)

        elif market_state == MarketState.CORRECTING_IN_UPTREND:
            # Buy the dip
            if ctx.price <= ctx.ma_fast * 1.01:
                action = TradingAction.ADD_TO_LONG if position_state.is_long else TradingAction.ENTER_LONG
                return ActionSignal(
                    action,
                    tranches=1,
                    reason="Buy the dip in uptrend"
                )

        elif market_state == MarketState.BREAKING_OUT_UP:
            if position_state.is_flat:
                return ActionSignal(
                    TradingAction.ENTER_LONG,
                    tranches=2,  # Aggressive entry
                    reason="Strong breakout momentum"
                )

        # SHORT opportunities
        elif market_state == MarketState.TRENDING_DOWN:
            if position_state.is_flat:
                # Initial entry below MA50
                if ctx.price < ctx.ma_fast * (1 - self.config.trend_threshold):
                    return ActionSignal(
                        TradingAction.ENTER_SHORT,
                        tranches=1,
                        reason="Trend down confirmed below MA50"
                    )
            else:
                # Add tranches at key levels
                return self._check_add_short_tranches(position_state, ctx)

        elif market_state == MarketState.CORRECTING_IN_DOWNTREND:
            # Short the rally
            if ctx.price >= ctx.ma_fast * 0.99:
                action = TradingAction.ADD_TO_SHORT if position_state.is_short else TradingAction.ENTER_SHORT
                return ActionSignal(
                    action,
                    tranches=1,
                    reason="Short the rally in downtrend"
                )

        elif market_state == MarketState.BREAKING_OUT_DOWN:
            if position_state.is_flat:
                return ActionSignal(
                    TradingAction.ENTER_SHORT,
                    tranches=2,  # Aggressive entry
                    reason="Strong breakdown momentum"
                )

        return ActionSignal(TradingAction.DO_NOTHING)

    def _check_add_long_tranches(self,
                                 position_state: PositionState,
                                 ctx: MarketContext) -> ActionSignal:
        """Check for adding tranches to long position"""
        count = position_state.tranche_count

        # Add at MA100
        if count == 1 and ctx.ma_mid * 0.98 < ctx.price < ctx.ma_mid * 1.02:
            return ActionSignal(
                TradingAction.ADD_TO_LONG,
                tranches=1,
                reason="Add tranche at MA100"
            )

        # Add bigger chunk at MA200
        elif count == 2 and ctx.ma_slow * 0.98 < ctx.price < ctx.ma_slow * 1.02:
            return ActionSignal(
                TradingAction.ADD_TO_LONG,
                tranches=2,
                reason="Add 2x tranches at MA200"
            )

        return ActionSignal(TradingAction.DO_NOTHING)

    def _check_add_short_tranches(self,
                                  position_state: PositionState,
                                  ctx: MarketContext) -> ActionSignal:
        """Check for adding tranches to short position"""
        count = position_state.tranche_count

        # Add at MA100
        if count == 1 and ctx.ma_mid * 0.98 < ctx.price < ctx.ma_mid * 1.02:
            return ActionSignal(
                TradingAction.ADD_TO_SHORT,
                tranches=1,
                reason="Add tranche at MA100"
            )

        # Add bigger chunk at MA200
        elif count == 2 and ctx.ma_slow * 0.98 < ctx.price < ctx.ma_slow * 1.02:
            return ActionSignal(
                TradingAction.ADD_TO_SHORT,
                tranches=2,
                reason="Add 2x tranches at MA200"
            )

        return ActionSignal(TradingAction.DO_NOTHING)
