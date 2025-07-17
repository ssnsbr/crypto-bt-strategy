
import backtrader as bt

from strategies import RiskManagement
from utils.utils import format_marketcap, format_price_to_marketcap


class FiboMartingaleStrategy(bt.Strategy):
    """
    A trading strategy implementing a Fibonacci Martingale approach.
    It initiates a buy after a 'migration' price threshold is crossed,
    then places subsequent buys at Fibonacci retracement levels from the
    All-Time High (ATH) since the last portfolio reset, using a Martingale multiplier.
    It includes both a dynamic Take Profit (TP) and a Global Stop Loss (SL).
    """
    params = (
        ('initial_buy_amount_factor', 0.01),  # Factor of available cash for initial buy
        ('martingale_multiplier', 2.0),      # Multiplier for subsequent Fibo buy quantities
        ('initial_tp_percent', 0.3),        # Initial Take Profit percentage from average buy price
        ('global_sl_percent', 0.990),         # Global Stop Loss percentage from average buy price
        ('fibo_levels_for_grid', [0.786, 0.618, 0.5, 0.382, 0.236]),  # Sorted descending Fibonacci retracement levels
        ('green_candle_streak_required', 2),  # Number of consecutive green candles required for Fibo buy
        ('data_in_market_cap', False),  # Number of consecutive green candles required for Fibo buy
        ('log', True)

    )

    def __init__(self):
        if self.p.data_in_market_cap:
            self._format_value_for_log_mcap = format_marketcap
            self.log("Price IS in Market Cap!")
        else:
            self._format_value_for_log_mcap = format_price_to_marketcap
            self.log("Price is NOT in Market Cap!")

        # Data feeds (assuming only one data feed)
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low

        self.order = None  # For tracking the current buy/sell order
        self.has_done_initial_buy = False           # Flag to ensure initial buy happens only once per cycle
        self.current_fibo_buy_level_idx = 0         # Index to track which Fibo level is next for a buy
        self.next_buy_amount_quantity = 0.0         # Calculated quantity for the next martingale buy

        # Portfolio-wide tracking (updated after each trade completion)
        self.portfolio_avg_buy_price = 0.0          # Average entry price of current position
        self.portfolio_total_quantity = 0.0         # Total quantity of asset currently held
        self.portfolio_highest_price_since_buy = 0.0  # Highest price reached since the last buy (for dynamic TP)

        # ATH (All-Time High) tracking for Fibonacci calculations
        self.ath = 0.0                              # All-Time High price since the last portfolio reset
        self.migrated = False                       # Flag indicating if the price has crossed the initial threshold
        self.ath_update_thrshld = 1.05
        # Green candle streak counter
        self.green_candle_streak = 0
        # Strategy State Variables
        self.has_done_initial_buy = False
        self.current_fibo_buy_level_idx = 0
        self.next_buy_amount_quantity = 0.0
        # Access position dynamically via self.getposition() when needed.
        self.migration_market_cap = 70_000
        self.dead_coin_market_cap = 15_000
        self.dead_coin = False
        self.finish_and_runaway = False
        self.old_cash = 0
        # Instantiate the RiskManagement class
        self.risk_manager = RiskManagement(self)
        self.index = 0

    # ----------------------- utils ##########################
    def cash_when_mcap(self, value):
        """
        when using marketcap, the cash was multiplied by 1B for math reasons, so when logging divid it by 1B
        """
        if self.p.data_in_market_cap:
            return value / 1_000_000_000
        else:
            return value

    def log(self, txt, dt=None):
        ''' Logging function for this strategy to print messages with date'''
        dt = dt or self.datas[0].datetime.date(0)
        if self.params.log:
            print(f'{self.index} {dt.isoformat()}, {txt}')

    def catch_migration(self, current_price):
        if self.p.data_in_market_cap:
            if current_price > self.migration_market_cap:
                self.migrated = True
        else:
            if current_price * 1_000_000_000 > self.migration_market_cap:
                self.migrated = True

        # If not migrated and price is still below threshold, do nothing
        # This check prevents unnecessary updates if migration hasn't happened yet
        if not self.migrated and (self.p.data_in_market_cap and current_price < self.migration_market_cap or
                                  not self.p.data_in_market_cap and current_price * 1_000_000_000 < self.migration_market_cap):
            return

    def catch_dead_coin(self, current_price):
        if self.migrated:
            if self.p.data_in_market_cap:
                if current_price < self.dead_coin_market_cap:
                    self.log(f"Announcing coin death at {current_price}")
                    self.dead_coin = True
            else:
                if current_price * 1_000_000_000 < self.dead_coin_market_cap:
                    self.log(f"Announcing coin death at {current_price}")
                    self.dead_coin = True

    def green_candle_ok(self):
        return self.green_candle_streak >= self.p.green_candle_streak_required

    def update_green_candle_streak(self):
        if self.dataclose[0] > self.dataopen[0]:
            self.green_candle_streak += 1
        else:
            self.green_candle_streak = 0

    def update_ath(self):
        # Update ATH (All-Time High) since the last portfolio reset
        # This ATH is crucial for calculating Fibonacci retracement levels for new buys.
        # update on each 5%
        if self.ath == 0.0 or self.ath * self.ath_update_thrshld < self.dataclose[0]:
            self.ath = max(self.ath, self.datahigh[0])

    # -------------------------- utils end ##########################
    # ------------------------ notifies ##########################

    def notify_order(self, order):
        """
        Receives an order whenever there has been a change in one
        Handles notifications about order status changes.
        Crucial for updating strategy state based on order execution.
        """
        if order.status in [order.Submitted, order.Accepted]:
            # Order is pending or accepted, nothing to do yet
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {self._format_value_for_log_mcap(order.executed.price)}, Cost: {self.cash_when_mcap(order.executed.value):.6f}, Comm: {self.cash_when_mcap(order.executed.comm):.6f}, Size: {order.executed.size:.2f}')
                # If this is the very first buy of a cycle, set the base quantity for subsequent martingale buys
                if not self.has_done_initial_buy:
                    self.has_done_initial_buy = True
                    # using sizer to adjust size of buy and sell

            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {self._format_value_for_log_mcap(order.executed.price)}, Cost: {self.cash_when_mcap(order.executed.value ):.6f}, Comm: {self.cash_when_mcap(order.executed.comm):.6f}, Size: {order.executed.size:.2f}')
                # If all positions are closed after a sell (either TP or SL), reset the strategy state
                if not self.getposition(self.datas[0]):  # Check if position size is zero
                    self.log("All positions closed. Resetting strategy state.")
                    self._reset_strategy_state()
            self._update_portfolio_stats()
            self.order = None  # Clear the pending order as it's completed

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected: Status {order.getstatusname(order.status)}, Ref {order.ref}')
            self.order = None  # Clear the pending order

    def notify_trade(self, trade):
        """
        Receives a trade whenever there has been a change in one
        Handles notifications about trade closures (when a buy and sell fully offset).
        """
        if trade.isclosed:
            if self.p.data_in_market_cap:
                self.log(f'TRADE PNL, Gross {trade.pnl/1_000_000_000:.6f}, Net {trade.pnlcomm/1_000_000_000:.6f}')
            else:
                self.log(f'TRADE PNL, Gross {trade.pnl:.2f}, Net {trade.pnlcomm:.2f}')

    def notify_cashvalue(self, cash, value):
        """
        Receives the current fund value, value status of the strategy’s broker
        """
        if cash != self.old_cash:
            self.log(f"Change in cash/value cash:{self.cash_when_mcap(cash):.6f} ,value:{self.cash_when_mcap(value):.6f}")
            self.old_cash = cash
            self.old_value = value

    # --------------- notifies end ##########################
    # --------------- functions ##########################

    def _update_portfolio_stats(self):
        """
        Calculates and updates the current average buy price and total quantity
        of the asset using Backtrader's internal position tracking.
        Also updates the highest price seen since the last buy.
        """
        """Calculates the current average buy price and total quantity of the asset using Backtrader's position."""

        current_pos = self.getposition(self.datas[0])  # Get the current position for the data feed

        if current_pos.size > 0:
            self.portfolio_total_quantity = current_pos.size
            self.portfolio_avg_buy_price = current_pos.price  # Backtrader tracks the average entry price
            # Update highest price for dynamic TP from the current bar's close
            self.portfolio_highest_price_since_buy = max(self.portfolio_highest_price_since_buy, self.dataclose[0])
        else:
            # No open position, reset portfolio stats
            self.portfolio_total_quantity = 0.0
            self.portfolio_avg_buy_price = 0.0
            self.portfolio_highest_price_since_buy = 0.0
            # Note: next_buy_amount_quantity is reset in _reset_strategy_state when position is fully closed.
            # Note: No need to reset next_buy_amount_quantity here; it's handled in _reset_strategy_state
            # after a full close.

    def _reset_strategy_state(self):
        """
        Resets all strategy-specific state variables.
        Called after a full position closure (either Take Profit or Global Stop Loss).
        """
        # Tell the sizer to reset its internal state
        if hasattr(self, 'sizer') and hasattr(self.sizer, 'reset'):
            self.sizer.reset()

        self.has_done_initial_buy = False
        self.current_fibo_buy_level_idx = 0
        self.next_buy_amount_quantity = 0.0  # Will be re-set on the next initial buy's completion
        self.portfolio_avg_buy_price = 0.0
        self.portfolio_total_quantity = 0.0
        self.portfolio_highest_price_since_buy = 0.0
        # self.ath = 0.0 # Reset ATH so it can be re-established for the next trading cycle
        # self.green_candle_streak = 0 # Reset streak
        self.log("Strategy state reset.")

    def next(self):
        """
        This method will be called for all remaining data points when the minimum period for all datas/indicators have been meet.
        The main logic of the strategy, executed on each new bar (candle).
        Handles migration, ATH tracking, green candle streak, stop loss,
        take profit, initial buy, and Fibo retracement buys.
        """
        self.index += 1
        # ------------------------ Part 1 : Updates ------------------------
        if self.order:
            # If an order is already pending, do not place new orders in this bar
            return

        if self.finish_and_runaway:
            return

        current_price = self.dataclose[0]  # Use the closing price of the current bar
        self.current_price = current_price
        self.current_marketcap_str = self._format_value_for_log_mcap(current_price)

        # --- Migration Logic ---
        self.catch_migration(current_price)
        self.catch_dead_coin(current_price)

        # The strategy only becomes active once the price crosses a certain threshold.
        if not self.migrated:
            return

        # --- Update ATH (All-Time High)
        self.update_ath()

        # --- Green Candle Streak Tracking ---
        self.update_green_candle_streak()

        # ------------------------ FULL EXIT ------------------------
        # --- Global Stop Loss Check (Highest Priority) ---
        # This rule is checked first to stop losing.
        # Exit and End Operation. No Buying happens again later.

        # ------------------------ FULL EXIT (Managed by RiskManagement) ------------------------
        # --- Global Stop Loss Check (Highest Priority) ---
        if self.risk_manager.check_and_execute_global_stop_loss(current_price):
            return  # Exit next() after placing SL order, wait for order completion

        # --- Dead Coin Exit Check ---
        if self.risk_manager.check_and_execute_dead_coin_exit(current_price):
            return  # Exit next() after placing dead coin exit order, wait for order completion

        # ------------------------ MAIN STRATEGY ------------------------
        # 1- Get in after migration!
        # BUY- If it goes to lower fibo like 87 77 61 50 38 Buy at each level
        # -- Buy amount is calculated.
        # SELL ALL at [TODO test] +30% profit of ALL
        # If not in, get in.
        # No Stop loss
        # ------------------------ MAIN STRATEGY - GET IN ------------------------
        # --- Rule 1: Initial Buy ---
        # Executes the very first buy once the migration condition is met
        # If coin is migrated and no position is open.
        if not self.has_done_initial_buy:
            if self.broker.getcash() > 0:
                self.log(f'Initial BUY: Attempting to buy at {self.current_marketcap_str}')
                # Tell the sizer what kind of buy this is
                self.sizer.p.buy_type_next = 'initial_buy'
                self.order = self.buy()  # Let the sizer determine the size
            return  # Always return after attempting initial buy, wait for next bar/order completion

        # ------------------------ Part 3 : 2 - IF in Profit (Managed by RiskManagement) ------------------------
        # --- Take Profit Check ---
        if self.risk_manager.check_and_execute_take_profit(current_price):
            return  # Exit next() after placing TP order

        # ------------------------ Part 3 : 3 - IF in Loss ------------------------
        # --- Rules 3 & 4: Martingale Fibonacci Retracement Buys ---
        # These buys occur when the price retraces to specific Fibonacci levels,
        # provided a green candle streak confirms a potential bounce.
        #  self.green_candle_ok() and \
        if self.getposition(self.datas[0]).size > 0 and \
           self.current_fibo_buy_level_idx < len(self.p.fibo_levels_for_grid):

            # Get the target Fibonacci factor for the current level
            target_fibo_factor = self.p.fibo_levels_for_grid[self.current_fibo_buy_level_idx]
            # Calculate the target price for this Fibonacci level based on the ATH
            target_fibo_price = self.ath * target_fibo_factor

            if current_price <= target_fibo_price:
                self.log(f'FIBO BUY (Level {self.current_fibo_buy_level_idx}): Attempting buy @ {self.current_marketcap_str} (Target Fibo Price {self._format_value_for_log_mcap(target_fibo_price)})')
                # Tell the sizer what kind of buy this is
                self.sizer.p.buy_type_next = 'fibo_martingale_buy'
                self.order = self.buy()  # Let the sizer determine the size
                self.current_fibo_buy_level_idx += 1  # Strategy still tracks which Fibo level is next
