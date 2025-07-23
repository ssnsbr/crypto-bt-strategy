
import backtrader as bt

from riskmanagers.FiboRiskManagement import FiboRiskManagement


class FiboMartingaleStrategy(bt.Strategy):
    """
    A trading strategy implementing a Fibonacci Martingale approach.
    It initiates a buy after a 'migration' price threshold is crossed,
    then places subsequent buys at Fibonacci retracement levels from the
    All-Time High (ATH) since the last portfolio reset, using a Martingale multiplier.
    It includes both a dynamic Take Profit (TP) and a Stop Loss (SL).
    """
    params = (
        ('initial_buy_amount_factor', 0.01),  # Factor of available cash for initial buy
        ('martingale_multiplier', 2.0),      # Multiplier for subsequent Fibo buy quantities
        ('tp_percent', 0.3),        # Initial Take Profit percentage from average buy price
        ('sl_percent', 0.990),         # Stop Loss percentage from average buy price
        ('fibo_levels_for_grid', [0.786, 0.618, 0.5, 0.382, 0.236]),  # Sorted descending Fibonacci retracement levels
        ('green_candle_streak_required', 2),  # Number of consecutive green candles required for Fibo buy
        ('data_in_market_cap', False),  # Number of consecutive green candles required for Fibo buy
        ('log', True)

    )

    def __init__(self):
        super().__init__()  # Call the base class constructor

        self.has_done_initial_buy = False           # Flag to ensure initial buy happens only once per cycle
        self.current_fibo_buy_level_idx = 0         # Index to track which Fibo level is next for a buy
        self.next_buy_amount_quantity = 0.0         # Calculated quantity for the next martingale buy

        # Strategy State Variables
        self.has_done_initial_buy = False
        self.current_fibo_buy_level_idx = 0
        self.next_buy_amount_quantity = 0.0
        self.risk_manager = FiboRiskManagement(self)

    def _reset_strategy_state(self):
        super()._reset_strategy_state()

        self.has_done_initial_buy = False
        self.current_fibo_buy_level_idx = 0

    def _execute_trading_logic(self):
        # ------------------------ MAIN STRATEGY - GET IN ------------------------
        # --- Rule 1: Initial Buy ---
        cond_position_open = self.getposition(self.datas[0]).size > 0
        cond_rsi = self.rsi < 40

        if not cond_position_open and cond_rsi:
            if self.broker.getcash() > 0:
                self.log(f'Initial BUY: Attempting to buy at {self.current_marketcap_str}')
                self.order = self.buy()  # Let the sizer determine the size
            return  # Always return after attempting initial buy, wait for next bar/order completion

        # These buys occur when the price retraces to specific Fibonacci levels,
        cond_green_candle = self.green_candle_streak > self.p.green_candle_streak_required()
        cond_fibo_level = self.current_fibo_buy_level_idx < len(self.p.fibo_levels_for_grid)
        print(cond_green_candle, cond_rsi, cond_position_open, cond_position_open, cond_fibo_level)
        if cond_position_open and cond_position_open:

            # Get the target Fibonacci factor for the current level
            target_fibo_factor = self.p.fibo_levels_for_grid[self.current_fibo_buy_level_idx]
            # Calculate the target price for this Fibonacci level based on the ATH
            target_fibo_price = self.ath * target_fibo_factor

            if self.current_price <= target_fibo_price:
                self.log(f'FIBO BUY (Level {self.current_fibo_buy_level_idx}): Attempting buy @ {self.current_marketcap_str} (Target Fibo Price {self._format_value_for_log_mcap(target_fibo_price)})')
                # Tell the sizer what kind of buy this is
                self.sizer.p.buy_type_next = 'fibo_martingale_buy'
                self.order = self.buy()  # Let the sizer determine the size
                self.current_fibo_buy_level_idx += 1  # Strategy still tracks which Fibo level is next
