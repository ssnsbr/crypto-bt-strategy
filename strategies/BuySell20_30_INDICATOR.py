

from strategies.Base import BaseTradingStrategy
from riskmanagers.NoneRiskManagement import NoneRiskManagement
from utils.bounce_detector import BounceDetector
from utils.liveliness_tracker import LivelinessTracker
import backtrader as bt


class BaseBuySell20_30_INDICATORS(BaseTradingStrategy):

    params = (
        ('log', True),
        ('tp', 1.2),                # Take profit at 120% of avg price
        ('sl', 0.7),
        ('buy_again', 0.8),         # Buy again at 70% of avg/last price
        ('buy_again_from_top', False),
        ('max_buy_count', 4),
        ('end_mcap', 20_000),
        ('min_ib_mcap', 20_000),
        #
        ('use_macd_buy_sell', [True, False]),
        ('use_ema_buy_sell', [True, False]),
        ('use_rsi_buy_sell', [True, False]),
        ('use_liveliness_buy_sell', [False, False]),
        ('use_stoch_buy_sell', [False, False]),
        ('use_bouce_buy_sell', [False, False]),
        ('MACD_p', [30, 65, 23]),
        ('EMA_p', 60),
        ('RSI_p', 60),
        ('STOCH_p', [60, 15, 15]),
        ("liveliness_w", 120),
        #
        ("rsi_thr", 50),
        ("EMA_tolerance", 0.1),
        #
        ('uncatch_bounce_tp', 1.2),
        ("sell_on_current_bounce_from_min", 1.35),
        ("sell_on_no_loss", False),
        ("up_bounce_threshold", 1.1),
        ("down_bounce_threshold", 0.9),
        ("no_buy_on_down_fall", False),
        ("min_liveliness_for_ba", 0.4),
        ("add_dynamic_ba", 0.05),
        #
        ('dead_coin_market_cap', 9_000),
        ('migration_market_cap', 125_000),
        ('buy_again_avg', 1),   # Buy again when avg/last is less than buy_again of current price
        ('sell_tp_on_avg', 1),  # sell tp on avg/last
        ('sell_sl_on_avg', 1),  # sell tp on avg/last
    )

    def __init__(self):
        super().__init__()

        # Data feeds from super
        # self.dataclose = self.datas[0].close
        # self.dataopen = self.datas[0].open
        # self.datahigh = self.datas[0].high
        # self.datalow = self.datas[0].low
        # self.datavolume = self.datas[0].volume

        self.rsi = bt.indicators.RSI_Safe(self.datas[0].close, period=self.p.RSI_p)
        self.ema = bt.indicators.EMA(self.datas[0].close, period=self.p.EMA_p)
        self.macd = bt.indicators.MACD(self.datas[0].close, period_me1=self.p.MACD_p[0], period_me2=self.p.MACD_p[1], period_signal=self.p.MACD_p[2])
        self.stoch = bt.indicators.StochasticFull(self.datas[0], period=self.p.STOCH_p[0], period_dfast=self.p.STOCH_p[1], period_dslow=self.p.STOCH_p[2])
        self.liveliness_tracker = LivelinessTracker(window=self.p.liveliness_w)

        self.risk_manager = NoneRiskManagement(self)
        self.buy_count = 0
        self.done = False

        self.just_bought_index = 0
        self.just_sold_index = 0

        self.min_wait_before_buy = 2
        self.min_wait_before_sell = 2

        self.last_buy_price = 0

        self.counters = {
            "tp_count": 0,
            "sl_count": 0,
            "ib_count": 0,
            "ba_count": 0,
            "ba_round_count": 0,
            "main_list": [],
            "counter_list": [],
            "nl_count": 0,
            "bfm_count": 0,
        }

        self.buy_counter = 0
        self.min_after_buy = 0
        self.max_after_buy = 0
        self.bounceDetector = BounceDetector()
        self.bounce_state = None

    def current_bounce_from_min(self):
        if self.min_after_buy != 0:
            return (self.current_price / self.min_after_buy)
        else:
            return 1

    def analyze_bounces(self, bounce_list):
        pass

    def is_on_down_fall(self):
        state = self.bounceDetector.get_state()
        if state is None:
            return True
        if len(state["bounce_list"]) > self.buy_counter - 1:
            return False
        else:
            return True

    # Detect if a local bounce of at least X% happened since first buy
    def detect_bounce(self, current_price, up_bounce_threshold=1.1, down_bounce_threshold=0.9):
        # TODO for not buying again
        pass

    def were_there_uncatched_bounce(self):
        # 100ib-80ba-64ba-(50ba,76tp)-55-66
        # here it gave a bounce which we did not catch
        # Should I exit?
        if (self.current_price / self.min_after_buy) > self.p.uncatch_bounce_tp:
            print("uncatched BOUNCE UP!")
            return True

    def add_to_list(self, item):
        dt = self.datas[0].datetime.datetime(0)
        self.counters["main_list"].append((item, self.current_price, self.index, dt.isoformat(), self.min_after_buy, self.max_after_buy))

    def _reset_strategy_state(self):
        super()._reset_strategy_state()
        self.buy_count = 0
        if self.buy_counter:
            self.counters["counter_list"].append(self.buy_counter)
        self.buy_counter = 0
        self.just_bought_index = 0
        self.just_sold_index = 0
        self.min_after_buy = 0  # for /0 error
        self.max_after_buy = 0
        self.add_to_list("r")
        self.bounceDetector.reset()

    def buy_wait(self):
        return self.index < self.just_bought_index + self.min_wait_before_buy

    def sell_wait(self):
        return self.index < self.just_bought_index + self.min_wait_before_sell

    def stop(self):
        """Called once at the end of the strategy"""
        self.add_to_list("e")
        print(
            f"Strategy End  | Counters: {self.counters} ")

    def init_buy(self):
        self.log(f'Initial BUY: Attempting at {self.current_marketcap_str}')
        self.order = self.buy()
        self.last_buy_price = self.current_price
        self.just_bought_index = self.index
        self.buy_counter = 1
        self.counters["ib_count"] += 1
        self.add_to_list("ib")

    def again_buy(self):
        self.log(f'BUY AGAIN: {self.current_marketcap_str}')
        self.order = self.buy()
        self.last_buy_price = self.current_price
        self.just_bought_index = self.index
        self.buy_counter += 1
        self.counters["ba_count"] += 1
        if self.buy_counter == 2:
            self.counters["ba_round_count"] += 1
        self.add_to_list("ba")

    def sell_tp(self):
        self.log(f'TP SELL: {self.current_marketcap_str}')
        print("max, min when in position:", self.max_after_buy, self.min_after_buy)
        position_size = self.getposition(self.datas[0]).size
        self.order = self.sell(size=position_size)
        self.just_sold_index = self.index
        self.counters["tp_count"] += 1
        self.add_to_list("tp")

    def sell_no_loss(self):
        self.log(f'NL SELL: {self.current_marketcap_str}')
        position_size = self.getposition(self.datas[0]).size
        self.order = self.sell(size=position_size)
        self.just_sold_index = self.index
        self.counters["nl_count"] += 1
        self.add_to_list("nl")

    def sell_bfm(self):
        self.log(f'FromMinBoubce SELL: {self.current_marketcap_str}')
        print("max, min when in position:", self.max_after_buy, self.min_after_buy)
        position_size = self.getposition(self.datas[0]).size
        self.order = self.sell(size=position_size)
        self.just_sold_index = self.index
        self.counters["bfm_count"] += 1
        self.add_to_list("bfm")

    def sell_sl(self):
        self.log(f'Defeat SELL: {self.current_marketcap_str}')
        self.order = self.close()
        self.just_sold_index = self.index
        self.counters["sl_count"] += 1
        self.add_to_list("sl")
        self.buy_counter *= -1

    def init_buy_cond(self):
        in_position = self.getposition(self.datas[0]).size > 0
        cond_rsi = self.rsi < self.p.rsi_thr
        ib_cond = self.current_price > self.p.min_ib_mcap
        return not in_position and cond_rsi and not self.buy_wait() and ib_cond

    def tp_cond(self):
        sell_cond_tp = False
        if self.in_position and not self.sell_wait():
            if self.p.sell_tp_on_avg:
                sell_cond_tp = self.current_price > self.portfolio_avg_buy_price * self.p.tp
            else:
                sell_cond_tp = self.current_price > self.last_buy_price * self.p.tp
        return sell_cond_tp

    def sl_cond(self):
        # --- S2: Defeat Stop ---
        defeat_con_1 = self.buy_counter >= self.p.max_buy_count
        if self.p.sell_sl_on_avg:
            defeat_con_2 = self.current_price < self.portfolio_avg_buy_price * self.p.sl
        else:
            defeat_con_2 = self.current_price < self.last_buy_price * self.p.sl

        return self.in_position and defeat_con_1 and defeat_con_2 and not self.sell_wait()

    def ba_cond(self):
        __cond = False
        # --- B2: Averaging Down ---
        if self.p.buy_again_avg == 1:
            buy_price_cond = self.current_price < self.portfolio_avg_buy_price * (self.p.buy_again - (self.p.add_dynamic_ba * self.buy_counter))
        else:
            buy_price_cond = self.current_price < self.last_buy_price * (self.p.buy_again - (self.p.add_dynamic_ba * self.buy_counter))
        # -------------
        _buy_counter_cond = self.buy_counter < self.p.max_buy_count
        # ----------------------------------------------------------------------------------
        # ------------ On down fall
        # no_buy_on_down_fall = False -> down_fall_cond=False -> not down_fall_cond= True
        # no_buy_on_down_fall = True -> self.is_on_down_fall=False -> not down_fall_cond= True
        # no_buy_on_down_fall = True -> self.is_on_down_fall=True -> not down_fall_cond= False
        _d1 = self.p.no_buy_on_down_fall and self.is_on_down_fall()
        down_fall_cond = not _d1
        # ----------- On liveliness, -1 = liveliness is off.
        if self.p.use_liveliness_buy_sell[0]:
            liveliness_cond = self.liveliness > self.p.min_liveliness_for_ba
        else:
            liveliness_cond = True
        if self.p.use_bouce_buy_sell[0]:
            pass
        # === Indicator conditions ===
        rsi_cond = True
        macd_cond = True
        ema_cond = True
        stoch_cond = True

        # --- RSI ---
        if self.p.use_rsi_buy_sell[0]:
            # Typical: oversold region
            rsi_cond = self.rsi < self.p.rsi_thr  # e.g. 30

        # --- MACD ---
        if self.p.use_macd_buy_sell[0]:
            macd_line = self.macd.macd[0]
            signal_line = self.macd.signal[0]
            macd_cond = (macd_line > 0) and (signal_line > 0) and (macd_line > signal_line)

        # --- EMA ---
        if self.p.use_ema_buy_sell[0]:
            ema_cond = self.current_price > self.ema * (1 - self.p.EMA_tolerance)
            # use 0.01 tolerance for 1% under EMA allowed

        # --- Stochastic ---
        if self.p.use_stoch_buy_sell[0]:
            stoch_k = self.stoch.percK
            stoch_d = self.stoch.percD
            stoch_cond = (stoch_k < self.p.STOCH_buy_threshold) and (stoch_k > stoch_d)
            # e.g. below 20 but %K crossing up %D

        # === Combine all conditions ===
        __cond = (
            self.in_position
            and buy_price_cond
            and _buy_counter_cond
            and liveliness_cond
            and down_fall_cond
            and rsi_cond
            and macd_cond
            and ema_cond
            and stoch_cond
        )

        if self.in_position and buy_price_cond and _buy_counter_cond:
            if not liveliness_cond or not down_fall_cond:
                print("***** NOT BUYING AGAIN: down_fall_cond:", down_fall_cond, ", liveliness_cond:", liveliness_cond, "liveliness:", self.liveliness)
        return __cond

    def _execute_trading_logic(self):
        if not self.migrated or self.done:
            return

        self.liveliness_tracker.update(self.current_price)
        self.liveliness = self.liveliness_tracker.get_liveliness()

        in_position = self.getposition(self.datas[0]).size > 0
        self.in_position = in_position
        if in_position:
            if self.min_after_buy == 0:
                self.min_after_buy = self.current_price
            else:
                self.min_after_buy = min(self.min_after_buy, self.current_price)
            self.max_after_buy = max(self.max_after_buy, self.current_price)
            self.bounce_state = self.bounceDetector.detect_bounce(self.current_price, up_bounce_threshold=self.p.up_bounce_threshold, down_bounce_threshold=self.p.down_bounce_threshold)
            self.analyze_bounces(self.bounce_state["bounce_list"])

        # --- B1: Initial Buy ---
        if self.init_buy_cond():
            self.init_buy()
            return

        # --- B2: Averaging Down ---
        if self.ba_cond():
            self.order = self.again_buy()
            return

        # --- NEWSell BFM: Sell on Bounce from Min
        if self.current_bounce_from_min() > self.p.sell_on_current_bounce_from_min:
            self.sell_bfm()
            return

        # --- NEWSell SnL: sell_on_no_loss
        if in_position and not self.sell_wait():
            if self.p.sell_on_no_loss and self.buy_counter != 1 and self.buy_counter != 0:
                if self.current_price > self.portfolio_avg_buy_price:
                    self.sell_no_loss()

        # --- S1: TP ---
        if self.tp_cond():
            self.sell_tp()
            return

        # --- S2: Defeat Stop ---
        if self.sl_cond():
            self.sell_sl()
            return

        # --- Z: END ---
        if in_position and self.current_price < self.p.end_mcap:
            self.log(f'Dead Coin SELL: {self.current_marketcap_str}')
            self.order = self.close()
            self.buy_counter *= -1
            self.add_to_list("d")
            self.done = True
            return
