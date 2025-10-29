

from strategies.Base import BaseTradingStrategy
from riskmanagers.NoneRiskManagement import NoneRiskManagement
from utils.bounce_detector import BounceDetector


# class BaseBuySell20_30_V2(BaseTradingStrategy):

#     params = (
#         ('log', True),
#         ('tp', 1.2),                # Take profit at 120% of avg price
#         ('sl', 0.7),
#         ('buy_again', 0.8),         # Buy again at 70% of avg/last price
#         ('max_buy_count', 4),
#         ('end_mcap', 20_000),
#         ('min_ib_mcap', 20_000),
#         ("sell_on_no_loss", False),
#         ("rsi", 100),
#         ('dead_coin_market_cap', 9_000),
#         ('migration_market_cap', 125_000),
#         ('buy_again_avg', 1),   # Buy again when avg/last is less than buy_again of current price
#         ('sell_tp_on_avg', 1),  # sell tp on avg/last
#         ('sell_sl_on_avg', 1),  # sell tp on avg/last
#     )

#     def __init__(self):
#         super().__init__()
#         self.risk_manager = NoneRiskManagement(self)
#         self.buy_count = 0
#         self.done = False

#         self.just_bought_index = 0
#         self.just_sold_index = 0

#         self.min_wait_before_buy = 2
#         self.min_wait_before_sell = 2

#         self.last_buy_price = 0

#         self.buy_counter = 0
#         self.sl_count = 0
#         self.tp_count = 0
#         self.ib_count = 0
#         self.ba_count = 0
#         self.ba_round_count = 0
#         self.counter_list = []
#         self.main_list = []

#         self.min_after_buy = 0
#         self.max_after_buy = 0

#     def add_to_list(self, item):
#         dt = self.datas[0].datetime.datetime(0)
#         self.main_list.append((item, self.current_price, self.index, dt.isoformat(), self.min_after_buy, self.max_after_buy))

#     def _reset_strategy_state(self):
#         super()._reset_strategy_state()
#         self.buy_count = 0
#         if self.buy_counter:
#             self.counter_list.append(self.buy_counter)
#         self.buy_counter = 0
#         self.just_bought_index = 0
#         self.just_sold_index = 0
#         self.min_after_buy = 0
#         self.max_after_buy = 0
#         self.add_to_list("r")

#     def buy_wait(self):
#         return self.index < self.just_bought_index + self.min_wait_before_buy

#     def sell_wait(self):
#         return self.index < self.just_bought_index + self.min_wait_before_sell

#     def stop(self):
#         """Called once at the end of the strategy"""
#         self.add_to_list("e")
#         print(
#             f"Strategy End  | InitBuy: {self.ib_count} | TP: {self.tp_count} | SL: {self.sl_count} | BuyAgain: {self.ba_round_count}  | BuyAgainAll:{self.ba_count} | self.counter_list: len={len(self.counter_list)} list= {self.counter_list}")

#     def init_buy(self):
#         self.log(f'Initial BUY: Attempting at {self.current_marketcap_str}')
#         self.order = self.buy()
#         self.last_buy_price = self.current_price
#         self.just_bought_index = self.index
#         self.buy_counter = 1
#         self.ib_count += 1
#         self.add_to_list("ib")

#     def again_buy(self):
#         self.log(f'BUY AGAIN: {self.current_marketcap_str}')
#         self.order = self.buy()
#         self.last_buy_price = self.current_price
#         self.just_bought_index = self.index
#         self.buy_counter += 1
#         self.ba_count += 1
#         if self.buy_counter == 2:
#             self.ba_round_count += 1
#         self.add_to_list("ba")

#     def sell_tp(self):
#         self.log(f'TP SELL: {self.current_marketcap_str}')
#         print("max, min when in position:", self.max_after_buy, self.min_after_buy)
#         position_size = self.getposition(self.datas[0]).size
#         self.order = self.sell(size=position_size)
#         self.just_sold_index = self.index
#         self.tp_count += 1
#         self.add_to_list("tp")

#     def sell_sl(self):
#         self.log(f'Defeat SELL: {self.current_marketcap_str}')
#         self.order = self.close()
#         self.just_sold_index = self.index
#         self.sl_count += 1
#         self.add_to_list("sl")
#         self.buy_counter *= -1

#     def _execute_trading_logic(self):
#         if not self.migrated or self.done:
#             return

#         in_position = self.getposition(self.datas[0]).size > 0
#         if in_position:
#             self.min_after_buy = min(self.min_after_buy, self.current_price)
#             self.max_after_buy = max(self.max_after_buy, self.current_price)

#         # --- B1: Initial Buy ---
#         ib_cond = self.current_price > self.p.min_ib_mcap
#         cond_rsi = self.rsi < self.p.rsi
#         if not in_position and cond_rsi and not self.buy_wait() and ib_cond:
#             self.init_buy()
#             return

#         # --- B2: Averaging Down ---
#         if self.p.buy_again_avg == 1:
#             buy_cond = self.current_price < self.portfolio_avg_buy_price * self.p.buy_again
#         else:
#             buy_cond = self.current_price < self.last_buy_price * self.p.buy_again
#         if in_position and buy_cond and self.buy_counter < self.p.max_buy_count:
#             self.order = self.again_buy()
#             return

#         # --- S1: TP ---
#         if in_position and not self.sell_wait():
#             if self.p.sell_tp_on_avg:
#                 sell_cond_tp = self.current_price > self.portfolio_avg_buy_price * self.p.tp
#             elif self.p.sell_on_no_loss and self.buy_counter != 1 and self.buy_counter != 0:
#                 sell_cond_tp = self.current_price > self.portfolio_avg_buy_price
#             else:
#                 sell_cond_tp = self.current_price > self.last_buy_price * self.p.tp
#             if sell_cond_tp:
#                 self.sell_tp()
#                 return

#         # --- S2: Defeat Stop ---
#         defeat_con_1 = self.buy_counter >= self.p.max_buy_count
#         if self.p.sell_sl_on_avg:
#             defeat_con_2 = self.current_price < self.portfolio_avg_buy_price * self.p.sl
#         else:
#             defeat_con_2 = self.current_price < self.last_buy_price * self.p.sl

#         if in_position and defeat_con_1 and defeat_con_2 and not self.sell_wait():
#             self.sell_sl()
#             return

#         # --- Z: END ---
#         if in_position and self.current_price < self.p.end_mcap:
#             self.log(f'Dead Coin SELL: {self.current_marketcap_str}')
#             self.order = self.close()
#             self.buy_counter *= -1
#             self.add_to_list("d")
#             self.done = True
#             return


class BaseBuySell20_30_V3(BaseTradingStrategy):

    params = (
        ('log', True),
        ('tp', 1.2),                # Take profit at 120% of avg price
        ('sl', 0.7),
        ('buy_again', 0.8),         # Buy again at 70% of avg/last price
        ('max_buy_count', 4),
        ('end_mcap', 20_000),
        ('min_ib_mcap', 20_000),
        #
        ('uncatch_bounce_tp', 1.2),
        ("sell_on_current_bounce_from_min", 1.35),
        ("sell_on_no_loss", False),
        ("up_bounce_threshold", 1.1),
        ("down_bounce_threshold", 0.9),
        #
        ("rsi", 100),
        ('dead_coin_market_cap', 9_000),
        ('migration_market_cap', 125_000),
        ('buy_again_avg', 1),   # Buy again when avg/last is less than buy_again of current price
        ('sell_tp_on_avg', 1),  # sell tp on avg/last
        ('sell_sl_on_avg', 1),  # sell tp on avg/last
    )

    def __init__(self):
        super().__init__()
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

    def current_bounce_from_min(self):
        return (self.current_price / self.min_after_buy)

    def analyze_bounces(self, bounce_list):
        pass

    def buy_again_decider(self):
        return False

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
            self.counter["counter_list"].append(self.buy_counter)
        self.buy_counter = 0
        self.just_bought_index = 0
        self.just_sold_index = 0
        self.min_after_buy = 0.1  # for /0 error
        self.max_after_buy = 0.1
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

    def _execute_trading_logic(self):
        if not self.migrated or self.done:
            return

        in_position = self.getposition(self.datas[0]).size > 0
        if in_position:
            self.min_after_buy = min(self.min_after_buy, self.current_price)
            self.max_after_buy = max(self.max_after_buy, self.current_price)
            bounce_state = self.bounceDetector.detect_bounce(self.current_price, up_bounce_threshold=self.p.up_bounce_threshold, down_bounce_threshold=self.p.down_bounce_threshold)
            self.analyze_bounces(bounce_state["bounce_list"])

        # --- B1: Initial Buy ---
        ib_cond = self.current_price > self.p.min_ib_mcap
        cond_rsi = self.rsi < self.p.rsi
        if not in_position and cond_rsi and not self.buy_wait() and ib_cond:
            self.init_buy()
            return

        # --- B2: Averaging Down ---
        if self.p.buy_again_avg == 1:
            buy_cond = self.current_price < self.portfolio_avg_buy_price * self.p.buy_again
        else:
            buy_cond = self.current_price < self.last_buy_price * self.p.buy_again
        if in_position and buy_cond and self.buy_counter < self.p.max_buy_count:
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
        if in_position and not self.sell_wait():
            if self.p.sell_tp_on_avg:
                sell_cond_tp = self.current_price > self.portfolio_avg_buy_price * self.p.tp
            else:
                sell_cond_tp = self.current_price > self.last_buy_price * self.p.tp
            if sell_cond_tp:
                self.sell_tp()
                return

        # --- S2: Defeat Stop ---
        defeat_con_1 = self.buy_counter >= self.p.max_buy_count
        if self.p.sell_sl_on_avg:
            defeat_con_2 = self.current_price < self.portfolio_avg_buy_price * self.p.sl
        else:
            defeat_con_2 = self.current_price < self.last_buy_price * self.p.sl

        if in_position and defeat_con_1 and defeat_con_2 and not self.sell_wait():
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
