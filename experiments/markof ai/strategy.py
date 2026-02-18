

# ============================================================================
# POSITION ANALYZER (Pure Logic - No Data Storage)
# ============================================================================

class PositionAnalyzer:
    """Analyzes position data - pure logic, no state"""

    @staticmethod
    def is_long(position_data: PositionData) -> bool:
        return position_data.size > 0

    @staticmethod
    def is_short(position_data: PositionData) -> bool:
        return position_data.size < 0

    @staticmethod
    def is_flat(position_data: PositionData) -> bool:
        return position_data.size == 0

    @staticmethod
    def avg_entry_price(position_data: PositionData) -> float:
        """Calculate average entry price"""
        if not position_data.entry_prices:
            return 0.0
        return np.mean(position_data.entry_prices)

    @staticmethod
    def unrealized_pnl_pct_long(position_data: PositionData, current_price: float) -> float:
        """Calculate unrealized P&L % for long position"""
        avg_entry = PositionAnalyzer.avg_entry_price(position_data)
        if avg_entry == 0:
            return 0.0
        return ((current_price / avg_entry) - 1) * 100

    @staticmethod
    def unrealized_pnl_pct_short(position_data: PositionData, current_price: float) -> float:
        """Calculate unrealized P&L % for short position"""
        avg_entry = PositionAnalyzer.avg_entry_price(position_data)
        if avg_entry == 0:
            return 0.0
        return ((avg_entry / current_price) - 1) * 100

    @staticmethod
    def pullback_from_high_pct(position_data: PositionData, current_price: float) -> float:
        """Calculate pullback from highest point"""
        if position_data.highest_since_entry == 0:
            return 0.0
        return ((position_data.highest_since_entry - current_price) /
                position_data.highest_since_entry) * 100

    @staticmethod
    def rally_from_low_pct(position_data: PositionData, current_price: float) -> float:
        """Calculate rally from lowest point"""
        if position_data.lowest_since_entry == float('inf'):
            return 0.0
        return ((current_price - position_data.lowest_since_entry) /
                position_data.lowest_since_entry) * 100


# ============================================================================
# MAIN STRATEGY (Orchestrator)
# ============================================================================

class MarkovStateStrategy(bt.Strategy):
    """
    Main strategy - orchestrates components

    Flow:
    1. Observe market -> MarketState (what we think)
    2. Decide action -> TradingAction (what we do)
    3. Execute action -> Buy/Sell/Close (how we do it)
    """

    params = (
        ('config', None),  # StrategyConfig object
    )

    def __init__(self):
        # Configuration
        self.config = self.params.config or StrategyConfig()

        # Components
        self.state_detector = StateDetector(self.config)
        self.action_decider = ActionDecider(self.config)
        self.position_sizer = PositionSizer(self.config)

        # State tracking
        self.market_state = MarketState.UNDECIDED
        self.prev_market_state = MarketState.UNDECIDED
        self.position_state = PositionState()

        # Indicators
        self.ma_fast = bt.indicators.SMA(
            self.data.close, period=self.config.ma_fast
        )
        self.ma_mid = bt.indicators.SMA(
            self.data.close, period=self.config.ma_mid
        )
        self.ma_slow = bt.indicators.SMA(
            self.data.close, period=self.config.ma_slow
        )
        self.rsi = bt.indicators.RSI(
            self.data.close, period=self.config.rsi_period
        )
        self.atr = bt.indicators.ATR(
            self.data, period=self.config.atr_period
        )

    def next(self):
        """Main strategy loop"""
        # Step 1: Update position state
        self.position_state.size = self.position.size
        if self.position:
            self.position_state.update_extremes(self.data.close[0])

        # Step 2: Gather market context (observations)
        market_context = MarketContext(
            price=self.data.close[0],
            ma_fast=self.ma_fast[0],
            ma_mid=self.ma_mid[0],
            ma_slow=self.ma_slow[0],
            rsi=self.rsi[0],
            atr=self.atr[0]
        )

        # Step 3: Detect market state (what we think)
        new_market_state = self.state_detector.detect_state(
            market_context=market_context,
            current_state=self.market_state,
            position_state=self.position_state
        )

        # Log state changes
        if new_market_state != self.market_state:
            self.log(f"STATE: {self.market_state.name} -> {new_market_state.name}")
            self.prev_market_state = self.market_state
            self.market_state = new_market_state

        # Step 4: Decide action (what we should do)
        action_signal = self.action_decider.decide_action(
            market_state=self.market_state,
            prev_market_state=self.prev_market_state,
            position_state=self.position_state,
            market_context=market_context
        )

        # Step 5: Execute action
        if action_signal.should_execute:
            self._execute_action(action_signal, market_context)

    def _execute_action(self, signal: ActionSignal, ctx: MarketContext):
        """Execute the trading action"""

        self.log(f"ACTION: {signal.action.name} | {signal.reason}")

        # Exit actions
        if signal.action in [TradingAction.EXIT_LONG, TradingAction.EXIT_SHORT]:
            self.close()
            self.position_state.reset()

        # Entry/Add long actions
        elif signal.action in [TradingAction.ENTER_LONG, TradingAction.ADD_TO_LONG]:
            is_momentum = self.market_state == MarketState.BREAKING_OUT_UP
            size = self.position_sizer.calculate_size(
                cash=self.broker.get_cash(),
                price=ctx.price,
                tranches=signal.tranches,
                is_momentum=is_momentum
            )
            self.buy(size=size)
            self.position_state.add_entry(ctx.price, signal.tranches)
            self.log(f"  -> BUY {size} shares @ {ctx.price:.2f}")

        # Entry/Add short actions
        elif signal.action in [TradingAction.ENTER_SHORT, TradingAction.ADD_TO_SHORT]:
            is_momentum = self.market_state == MarketState.BREAKING_OUT_DOWN
            size = self.position_sizer.calculate_size(
                cash=self.broker.get_cash(),
                price=ctx.price,
                tranches=signal.tranches,
                is_momentum=is_momentum
            )
            self.sell(size=size)
            self.position_state.add_entry(ctx.price, signal.tranches)
            self.log(f"  -> SELL {size} shares @ {ctx.price:.2f}")

    def log(self, txt: str):
        """Logging"""
        dt = self.data.datetime.date(0)
        pos_str = f"Pos:{self.position_state.size:+5d}" if self.position_state.size else "Pos: FLAT"
        print(f"{dt} | {self.market_state.name:25} | {pos_str} | {txt}")
