import backtrader as bt
from utils.utils import format_marketcap, format_price_to_marketcap


class BaseTradingStrategy(bt.Strategy):
    """
    Base class for trading strategies, containing common parameters,
    initialization logic, utility methods, and notification handlers.
    """
    params = (
        ('tp_percent', 0.05),
        ('sl_percent', 0.990),
        ('green_candle_streak_required', 2),
        ('data_in_market_cap', False),
        ('log', True),

        # Exit Strategy Enable/Disable Flags (with defaults)
        ('enable_emergency_exit', True),
        ('enable_stop_loss', True),
        ('enable_take_profit', True),
        ('enable_trailing_stop_loss', False),
        ('enable_trailing_take_profit', False),
        ('enable_dynamic_take_profit', False),  # Default Disabled

        # Trailing Stop Loss Parameters
        ('trailing_sl_percent', 0.02),
        ('trailing_sl_activation_profit_percent', 0.01),

        # Trailing Take Profit Parameters
        ('trailing_tp_percent', 0.01),
        ('trailing_tp_activation_profit_percent', 0.05),

        # Dynamic Take Profit Parameters
        ('dynamic_tp_peak_profit_percent', 0.10),  # Profit % from avg_buy_price to start tracking peak
        ('dynamic_tp_pullback_percent', 0.01),   # Percentage pullback from peak to trigger DTP

        # indicators
        ('rsi_period', 15),
        ('lookback_period', 50),  # Period to find the last significant high/low
        ('atr_period', 15),
        ('bb_period', 20),
        ('bb_devfactor', 2),
    )

    def __init__(self):
        self.index = 0
        # Data formatting for logging
        if self.p.data_in_market_cap:
            self._format_value_for_log_mcap = format_marketcap
            self.log("Price IS in Market Cap!")
        else:
            self._format_value_for_log_mcap = format_price_to_marketcap
            self.log("Price is NOT in Market Cap!")

        # Data feeds
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume
        self.rsi = bt.indicators.RSI(self.datas[0].close, period=self.p.rsi_period)
        self.sma60 = bt.indicators.SimpleMovingAverage(self.datas[0].close, period=60)
        self.sma30 = bt.indicators.SimpleMovingAverage(self.datas[0].close, period=30)
        self.sma15 = bt.indicators.SimpleMovingAverage(self.datas[0].close, period=15)
        self.atr = bt.indicators.ATR(self.datas[0], period=self.p.atr_period)
        self.bbands = bt.indicators.BollingerBands(self.dataclose,
                                                   period=self.p.bb_period,
                                                   devfactor=self.p.bb_devfactor)

        self.last_high = bt.indicators.Highest(self.datahigh, period=self.p.lookback_period)
        self.last_low = bt.indicators.Lowest(self.datalow, period=self.p.lookback_period)

        # self.kama = bt.indicators.KAMA(self.datas[0])

        self.order = None  # For tracking the current buy/sell order

        # Portfolio-wide tracking (updated after each trade completion)
        self.portfolio_avg_buy_price = 0.0          # Average entry price of current position
        self.portfolio_total_quantity = 0.0         # Total quantity of asset currently held
        self.portfolio_highest_price_since_buy = 0.0  # Highest price reached since the last buy (for dynamic TP)

        # ATH and Migration tracking
        self.ath = 0.0
        self.ath_changed = False
        self.migrated = False
        self.ath_update_thrshld = 1.05
        self.green_candle_streak = 0

        self.migration_market_cap = 70_000
        self.dead_coin_market_cap = 15_000
        self.dead_coin = False
        self.emergency_exit_triggered = False
        self.old_cash = 0
        self.old_value = 0  # Initialized for notify_cashvalue

        # Risk management will be instantiated in derived classes
        self.risk_manager = None
        self.current_price = 0.0
        self.current_marketcap_str = ""
        self.current_volume = 0  # Initialized for FastScalperStrategy

    # --- Utility Methods ---

    def cash_when_mcap(self, value):
        if self.p.data_in_market_cap:
            return value / 1_000_000_000
        else:
            return value

    def log(self, txt, dt=None):
        if self.params.log:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'[Strategy] [{self.__class__.__name__}] Index {self.index} {dt.isoformat()}, {txt}')

    def catch_migration(self, current_price):
        if self.migrated:
            return
        tmp = current_price if self.p.data_in_market_cap else current_price * 1_000_000_000
        if tmp > self.migration_market_cap:
            self.migrated = True
            self.log(f"Migration threshold crossed at {self._format_value_for_log_mcap(current_price)}")

    def catch_dead_coin(self, current_price):
        if self.migrated:  # Only check for dead coin after migration
            tmp = current_price if self.p.data_in_market_cap else current_price * 1_000_000_000
            if tmp < self.dead_coin_market_cap:
                self.log(f"Announcing coin death at {self._format_value_for_log_mcap(current_price)}")
                self.dead_coin = True

    def green_candle_ok(self):
        return self.green_candle_streak >= self.p.green_candle_streak_required

    def update_green_candle_streak(self):
        if self.dataclose[0] > self.dataopen[0]:
            self.green_candle_streak += 1
        else:
            self.green_candle_streak = 0

    def update_ath(self):
        if self.ath == 0.0 or self.dataclose[0] > self.ath * self.ath_update_thrshld:
            self.ath = max(self.ath, self.datahigh[0])
            self.log(f"New ATH updated to {self._format_value_for_log_mcap(self.ath)}")
            self.ath_changed = True  # make it False if you need it in your strategy. BaseTradingStrategy only set it to true.
            return True
        return False

    # --- Notification Handlers ---
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {self._format_value_for_log_mcap(order.executed.price)}, Cost: {self.cash_when_mcap(order.executed.value):.6f}, Comm: {self.cash_when_mcap(order.executed.comm):.6f}, Size: {order.executed.size:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {self._format_value_for_log_mcap(order.executed.price)}, Cost: {self.cash_when_mcap(order.executed.value ):.6f}, Comm: {self.cash_when_mcap(order.executed.comm):.6f}, Size: {order.executed.size:.2f}')
                if not self.getposition(self.datas[0]):
                    self.log("All positions closed. Resetting strategy state.")
                    self._reset_strategy_state()
            self._update_portfolio_stats()
            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected: Status {order.getstatusname(order.status)}, Ref {order.ref}')
            self.order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            pnl_gross = trade.pnl / 1_000_000_000 if self.p.data_in_market_cap else trade.pnl
            pnl_net = trade.pnlcomm / 1_000_000_000 if self.p.data_in_market_cap else trade.pnlcomm
            self.log(f'TRADE PNL, Gross {pnl_gross:.6f}, Net {pnl_net:.6f}')

    def notify_cashvalue(self, cash, value):
        if cash != self.old_cash:
            self.log(f"Change in cash/value cash:{self.cash_when_mcap(cash):.6f} ,value:{self.cash_when_mcap(value):.6f}")
            self.old_cash = cash
            self.old_value = value

    # --- Portfolio Management ---
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
            self.portfolio_avg_buy_price = current_pos.price
            # Update highest price for dynamic TP from the current bar's close
            self.portfolio_highest_price_since_buy = max(self.portfolio_highest_price_since_buy, self.dataclose[0])
        else:
            # No open position, reset portfolio stats
            self.portfolio_total_quantity = 0.0
            self.portfolio_avg_buy_price = 0.0
            self.portfolio_highest_price_since_buy = 0.0

    def _reset_strategy_state(self):
        if hasattr(self, 'sizer') and hasattr(self.sizer, 'reset'):
            self.sizer.reset()

        self.next_buy_amount_quantity = 0.0  # Will be re-set on the next initial buy's completion
        self.portfolio_avg_buy_price = 0.0
        self.portfolio_total_quantity = 0.0
        self.portfolio_highest_price_since_buy = 0.0
        # self.ath = 0.0 # Consider if ATH should be reset here or only when a new migration occurs
        # self.green_candle_streak = 0 # Consider if streak should be reset here
        self.log("Strategy state reset.")

    def next(self):
        """
        This method will be called for all remaining data points when the minimum period for all datas/indicators have been meet.
        The main logic of the strategy, executed on each new bar (candle).
        Handles migration, ATH tracking, green candle streak, stop loss,
        take profit, initial buy, and Fibo retracement buys.
        """
        self.index += 1

        # If an order is already pending, do not place new orders in this bar
        if self.order or self.emergency_exit_triggered:
            return

        self.current_price = self.dataclose[0]
        self.current_volume = self.datavolume[0]
        self.current_marketcap_str = self._format_value_for_log_mcap(self.current_price)

        self.catch_migration(self.current_price)
        self.catch_dead_coin(self.current_price)

        if not self.migrated:
            return

        self.update_ath()
        self.update_green_candle_streak()

        # Placeholders for strategy-specific logic

        # Execute risk management first
        if self._execute_risk_management():
            return  # If a risk management action (SL/TP/Emergency Exit) was taken, stop further trading logic for this bar
        # Execute strategy-specific trading logic
        self._execute_trading_logic()

    def _execute_risk_management(self) -> bool:
        """
        Executes the risk management checks in priority order,
        respecting the enable/disable parameters.
        Returns True if any risk management action was taken (order placed), False otherwise.
        """
        if not self.risk_manager:
            self.log("Warning: Risk manager not initialized for this strategy.")
            return False

        # Order of priority for exits: SL > Emergency Exit > Trailing SL > Trailing TP > Dynamic TP > Fixed TP
        if self.p.enable_stop_loss and self.risk_manager.check_and_execute_stop_loss(self.current_price):
            return True
        if self.p.enable_emergency_exit and self.risk_manager.check_and_execute_emergency_exit(self.current_price):
            return True
        if self.p.enable_trailing_stop_loss and self.risk_manager.check_and_execute_trailing_stop_loss(self.current_price):
            return True
        if self.p.enable_trailing_take_profit and self.risk_manager.check_and_execute_trailing_take_profit(self.current_price):
            return True
        if self.p.enable_dynamic_take_profit and self.risk_manager.check_and_execute_dynamic_take_profit(self.current_price):
            return True
        if self.p.enable_take_profit and self.risk_manager.check_and_execute_take_profit(self.current_price):
            return True
        return False

    def _execute_trading_logic(self):
        # This method MUST be overridden by derived classes
        raise NotImplementedError("Derived strategies must implement _execute_trading_logic method.")
