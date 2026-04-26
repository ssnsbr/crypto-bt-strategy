

from riskmanagers.noneRiskManagement import NoneRiskManagement
import backtrader as bt

from backtrader_extended.strategies.Base_Crypto import BaseCryptoTradingStrategy
import backtrader as bt

from riskmanagers.noneRiskManagement import NoneRiskManagement


class BaseCryptoTradingStrategy(bt.Strategy):
    """
    Base class for trading strategies, containing common parameters,
    initialization logic, utility methods, and notification handlers.
    """
    params = (
        ('tp_percent', 0.05),
        ('sl_percent', 0.990),
        ('green_candle_streak_required', 2),
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
        ('dynamic_tp_peak_profit_percent', 0.10),  # Profit % from  to start tracking peak
        ('dynamic_tp_pullback_percent', 0.01),   # Percentage pullback from peak to trigger DTP

        # indicators
        ('rsi_period', 14),
        ('lookback_period', 50),  # Period to find the last significant high/low
        ('atr_period', 15),
        ('bb_period', 20),
        ('bb_devfactor', 2),
    )

    def __init__(self):
        self.index = 0

        # Data feeds
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume
        # self.rsi = bt.indicators.RSI_Safe(self.datas[0].close, period=self.p.rsi_period)
        # self.rsi = SafeRSI(self.datas[0].close, period=self.p.rsi_period)

        # self.sma60 = bt.indicators.SimpleMovingAverage(self.datas[0].close, period=60)
        # self.sma30 = bt.indicators.SimpleMovingAverage(self.datas[0].close, period=30)
        # self.sma15 = bt.indicators.SimpleMovingAverage(self.datas[0].close, period=15)
        # self.atr = bt.indicators.ATR(self.datas[0], period=self.p.atr_period)
        # self.bbands = bt.indicators.BollingerBands(self.dataclose,
        #                                            period=self.p.bb_period,
        #                                            devfactor=self.p.bb_devfactor)

        # self.last_high = bt.indicators.Highest(self.datahigh, period=self.p.lookback_period)
        # self.last_low = bt.indicators.Lowest(self.datalow, period=self.p.lookback_period)

        # self.kama = bt.indicators.KAMA(self.datas[0])

        self.order = None  # For tracking the current b/s order

        # Portfolio-wide tracking (updated after each trade completion)
        self.portfolio_avg_entry_price = 0.0          # Average entry price of current position
        self.portfolio_total_quantity = 0.0         # Total quantity of asset currently held
        self.portfolio_highest_price_since_buy = 0.0  # Highest price reached since the last buy (for dynamic TP)

        self.green_candle_streak = 0

        self.emergency_exit_triggered = False
        self.old_cash = 0
        self.old_value = 0  # Initialized for notify_cashvalue

        # Risk management will be instantiated in derived classes
        self.risk_manager = NoneRiskManagement(self)
        self.current_price = 0.0
        self.current_marketcap_str = ""
        self.current_volume = 0  # Initialized for FastScalperStrategy
        self.print_risk_management_once = True
        print("Base Trading Strategy Initialized")
    # --- Utility Methods ---

    def log(self, txt, dt=None):
        if self.params.log:
            dt = dt or self.datas[0].datetime.datetime(0)
            print(f'[Strategy] [{self.__class__.__name__}] Index {self.index} {dt.isoformat()}, {txt}')

    def green_candle_ok(self):
        return self.green_candle_streak >= self.p.green_candle_streak_required

    def update_green_candle_streak(self):
        if self.dataclose[0] > self.dataopen[0]:
            self.green_candle_streak += 1
        else:
            self.green_candle_streak = 0

    # --- Notification Handlers ---

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {(order.executed.price)}, Cost: {order.executed.value:.6f}, Comm: {order.executed.comm:.6f}, Size: {order.executed.size:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {(order.executed.price)}, Cost: {order.executed.value:.6f}, Comm: {order.executed.comm:.6f}, Size: {order.executed.size:.2f}')
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
            pnl_gross = trade.pnl
            pnl_net = trade.pnlcomm
            self.log(f'TRADE PNL, Gross {pnl_gross:.6f}, Net {pnl_net:.6f}')

        if hasattr(self, 'sizer') and hasattr(self.sizer, 'notify_trade'):
            self.sizer.notify_trade(trade)

    def notify_cashvalue(self, cash, value):
        if cash != self.old_cash:
            self.log(f"Change in cash/value cash:{cash:.6f} ,value:{cash:.6f}")
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
        if current_pos.size != 0:
            self.portfolio_total_quantity = current_pos.size
            self.portfolio_avg_entry_price = current_pos.price
            # Update highest price for dynamic TP from the current bar's close
            self.portfolio_highest_price_since_buy = max(self.portfolio_highest_price_since_buy, self.dataclose[0])
        else:
            # No open position, reset portfolio stats
            self.portfolio_total_quantity = 0.0
            self.portfolio_avg_entry_price = 0.0
            self.portfolio_highest_price_since_buy = 0.0

    def _reset_strategy_state(self):
        if hasattr(self, 'sizer') and hasattr(self.sizer, 'reset'):
            self.sizer.reset()

        self.next_entry_amount_quantity = 0.0  # Will be re-set on the next initial entry's completion
        self.portfolio_avg_entry_price = 0.0
        self.portfolio_total_quantity = 0.0
        self.portfolio_highest_price_since_buy = 0.0
        # self.green_candle_streak = 0 # Consider if streak should be reset here
        self.log("Strategy state reset.")

    def stop(self):
        if self.getposition(self.datas[0]).size != 0:
            self.log(f'AT END OF BACKTEST! MarketCap {(self.current_price)}, '
                     f'Selling all {self.getposition(self.datas[0]).size:.2f} units.')
            self.order = self.close()
        return super().stop()

    # def prenext(self): before indicators

    def next(self):
        """
        This method will be called for all remaining data points when the minimum period for all datas/indicators have been meet.
        The main logic of the strategy, executed on each new bar (candle).
        Handles , , green candle streak, stop loss,
        take profit, initial entry, and Fibo retracement entrys.
        """
        self.index += 1  # starts after indicators
        # Check if this is the last bar
        # print(len(self),  (self._last()), len(self.dataclose))
        if len(self) == self.data.buflen() - 1:
            self.log(f"Final bar reached. at index {self.index}, bar {len(self)}.")
            if self.getposition().size != 0:
                self.log(f"Final bar reached. Selling all {self.getposition().size:.2f} units at {self.current_price}")
                self.order = self.close()
            return

        # If an order is already pending, do not place new orders in this bar
        if self.order or self.emergency_exit_triggered:
            return

        self.current_price = self.dataclose[0]
        self.current_volume = self.datavolume[0]
        self.current_marketcap_str = (self.current_price)

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
        if not self.risk_manager and self.print_risk_management_once:
            self.print_risk_management_once = False
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


class OrderHandler():

    def __init__(self, strategy, is_short=False, tp=1.1, sl=0.9, ea=0.95, dynamic_ea=0.00, tsl_init=480, tsl_again=240, min_delay=2):
        if is_short:
            self.is_short = True
            self.is_long = False
        else:
            self.is_short = False
            self.is_long = True
        self.strategy = strategy
        self.ea = ea
        self.sl = sl
        self.tp = tp
        self.tsli = tsl_init
        self.tsla = tsl_again
        self.min_delay = min_delay
        self.current_price = 0
        self.dynamic_ea = dynamic_ea
        self.current_index = 0

    # =============================================================
    def update(self, current_price, current_index):
        self.current_price = current_price
        self.current_index = current_index

    def enter(self):
        if self.is_long:
            return self.strategy.buy()
        else:
            return self.strategy.sell()

    def enter_again(self):
        if self.is_long:
            return self.strategy.buy()
        else:
            return self.strategy.sell()

    def exit(self):
        if self.is_long:
            return self.strategy.close()
        else:
            return self.strategy.close()

    def wait(self, last_trx_index):
        return self.current_index < last_trx_index + self.min_delay

    def level(self, in_price, multiplier):
        if self.is_long:
            return in_price * multiplier
        else:
            return in_price / multiplier

    def should_enter_again(self, in_price, counter=0):
        """Check if price crossed threshold for averaging in"""
        if counter == 0:
            if self.is_short:
                return self.current_price > self.level(in_price, self.ea)
            #     return self.current_price > in_price * (2 - self.ea)
            return self.current_price < in_price * self.ea
        else:
            # 0.9 = 0.95 - 0.05*1
            dyn_ba = self.ea - self.dynamic_ea * counter
            if self.is_short:
                return self.current_price > self.level(in_price, dyn_ba)
            #     return self.current_price > in_price * (2 - self.ea)
            return self.current_price < in_price * dyn_ba

    def should_take_profit(self, in_price):
        """Check if price hit take profit target"""
        if self.is_short:
            # return self.current_price < in_price * (2 - self.tp)
            return self.current_price < self.level(in_price, self.tp)
        return self.current_price > in_price * self.tp

    def should_stop_loss(self, in_price):
        """Check if price hit stop loss"""
        if self.is_short:
            #     return self.current_price > in_price * (2 - self.sl)
            return self.current_price > self.level(in_price, self.sl)
        return self.current_price < in_price * self.sl

    def should_stop_time_loss(self, entry_index, tsl):
        # print(self.current_index, entry_index, tsl)
        return self.current_index > entry_index + tsl

    def print_tpsl(self, in_price):
        if self.is_long:
            _tp = in_price * self.tp
            _sl = in_price * self.sl
            _ea = in_price * self.ea
        else:
            _tp = self.level(self, in_price, self.tp)
            _sl = self.level(self, in_price, self.sl)
            _ea = self.level(self, in_price, self.ea)
            # _tp = in_price * (2 - self.tp)
            # _sl = in_price * (2 - self.sl)
            # _ea = in_price * (2 - self.ea)

        print(f'{self.current_index}| TP:{_tp:.2f} | EA:{_ea:.2f} | SL:{_sl:.2f}')


class BaseLongShort(BaseCryptoTradingStrategy):

    params = (
        ('log', True),
        ("short", False),
        ('tp', 1.005),                # Take profit at 120% of avg price
        ('sl', 0.8),
        ('ea', 0.995),  # again at 70% of avg/last price
        ('max_enter_count', 4),
        ('tsl_init', 480),
        ('tsl_again', 480),
        #
        ("exit_on_no_loss", False),
        ("add_dynamic_ea", 0.05),
        ('ea_from_top', False),
        #
        ('enter_again_avg', 1),  # again when avg/last is less than  of current price
        ('exit_tp_on_avg', 1),  # sell tp on avg/last
        ('exit_sl_on_avg', 1),  # sell tp on avg/last
    )

    def __init__(self):
        super().__init__()

        # Data feeds from super
        self.order_handler = OrderHandler(self, is_short=self.p.short, tp=self.p.tp, sl=self.p.sl, dynamic_ea=self.p.add_dynamic_ea, ea=self.p.ea, tsl_init=self.p.tsl_init, tsl_again=self.p.tsl_again, min_delay=1)
        self.risk_manager = NoneRiskManagement(self)
        self.entry_count = 0
        self.done = False
        self.in_position = False  # Initialize in_position
        self.current_price = 0  # Initialize current_price
        self.portfolio_avg_entry_price = 0
        self.last_trx_index = 0

        self.last_entry_price = 0
        self.last_ie_index = 0
        self.last_ea_index = 0

        self.entry_counter = 0

        self.counters = {
            "tp_count": 0,
            "sl_count": 0,
            "tsl_count": 0,
            "ie_count": 0,
            "ea_count": 0,
            "ea_round_count": 0,
            "main_list": [],
            "counter_list": [],
            "nl_count": 0,
            "bb_count": 0,
        }

    def add_to_list(self, item):
        dt = self.datas[0].datetime.datetime(0)
        self.counters["main_list"].append((item, self.current_price, self.index, dt.isoformat()))

    def _reset_strategy_state(self):
        super()._reset_strategy_state()
        self.entry_count = 0
        if self.entry_counter:
            self.counters["counter_list"].append(self.entry_counter)
        self.entry_counter = 0
        self.last_trx_index = 0
        self.last_ea_index = 0
        self.last_ie_index = 0
        self.add_to_list("r")

    def stop(self):
        """Called once at the end of the strategy"""
        self.add_to_list("e")
        print(f"Strategy End  | Counters: {self.counters} ")

    # =========================================================================
    def enter(self, enter_type="ie"):
        if enter_type == "ie":
            log_text = "Initial"
            self.entry_counter = 1
            self.last_ie_index = self.index
            self.last_ea_index = self.index

        elif enter_type == "ea":
            log_text = "AGAIN"
            self.last_ea_index = self.index
            self.entry_counter += 1
            if self.entry_counter == 2:
                self.counters["ea_round_count"] += 1
        else:
            print("ERROR")

        self.log(f'{log_text} Enter: {self.current_marketcap_str}')
        self.add_to_list(enter_type)
        self.counters[enter_type + "_count"] += 1
        self.order = self.order_handler.enter()
        self.last_trx_index = self.index
        self.last_entry_price = self.current_price
        if self.p.log:
            p = self.portfolio_avg_entry_price if self.p.enter_again_avg else self.last_entry_price
            self.order_handler.print_tpsl(p)

    def exit(self, reason):
        if reason == "tp":
            log_text = "TP"
        elif reason == "nl":
            log_text = "NoLoss"
        elif reason == "bb":
            log_text = "BigBounce"
        elif reason == "sl":
            log_text = "SL"
            self.entry_counter *= -1
        elif reason == "tsl":
            log_text = "TSL"
            self.entry_counter *= -1
        else:
            print("ERROR")

        self.log(f'{log_text} Exit: {self.current_marketcap_str}')
        self.add_to_list(reason)
        self.counters[reason + "_count"] += 1
        self.order = self.order_handler.exit()
        self.last_trx_index = self.index
        self._reset_strategy_state()
    # =========================================================================

    def init_enter_cond(self):
        ib_cond = self.current_price > 0
        return ib_cond

    def tp_cond(self):
        p = self.portfolio_avg_entry_price if self.p.exit_tp_on_avg else self.last_entry_price
        sell_cond_tp = self.order_handler.should_take_profit(in_price=p)
        return sell_cond_tp

    def sl_cond(self):
        _cond_1 = self.entry_counter >= self.p.max_enter_count
        p = self.portfolio_avg_entry_price if self.p.exit_sl_on_avg else self.last_entry_price
        _cond_2 = self.order_handler.should_stop_loss(in_price=p)
        return _cond_1 and _cond_2

    def tsl_cond(self):
        _cond_1 = self.order_handler.should_stop_time_loss(entry_index=self.last_ie_index, tsl=self.p.tsl_init)
        _cond_2 = self.order_handler.should_stop_time_loss(entry_index=self.last_ea_index, tsl=self.p.tsl_again)
        return _cond_1 or _cond_2

    def ea_cond(self):
        p = self.portfolio_avg_entry_price if self.p.enter_again_avg else self.last_entry_price
        b_price_cond = self.order_handler.should_enter_again(in_price=p, counter=self.entry_counter - 1)
        # b_price_cond = self.current_price < p * (self.p.entry_again - (self.p.add_dynamic_ba * self.entry_counter))
        _entry_counter_cond = self.entry_counter < self.p.max_enter_count
        return b_price_cond and _entry_counter_cond

    # =========================================================================
    def _execute_trading_logic(self):
        self.order_handler.update(self.current_price, current_index=self.index)
        self.in_position = self.getposition(self.datas[0]).size != 0

        if self.order_handler.wait(last_trx_index=self.last_trx_index):
            return

        if not self.in_position:
            if self.init_enter_cond():
                self.enter("ie")
                return

        if self.in_position:
            # --- B2: Averaging Down ---
            if self.ea_cond():
                self.enter("ea")
                return

            if self.p.exit_on_no_loss and self.entry_counter != 1 and self.entry_counter != 0:
                if self.current_price > self.portfolio_avg_entry_price:
                    self.exit("nl")

            # --- S1: TP ---
            if self.tp_cond():
                self.exit("tp")
                return

            if self.sl_cond():
                self.exit("sl")
                return

            if self.tsl_cond():
                self.exit("tsl")
                return
