

from backtrader_extended.strategies.Base import BaseTradingStrategy
from riskmanagers.noneRiskManagement import NoneRiskManagement


class BaseMBSUTILS(BaseTradingStrategy):
    def __init__(self):
        super().__init__()

        # Data feeds from super
        # self.dataclose = self.datas[0].close
        # self.dataopen = self.datas[0].open
        # self.datahigh = self.datas[0].high
        # self.datalow = self.datas[0].low
        # self.datavolume = self.datas[0].volume
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
            "cs_count": 0,
        }

        self.buy_counter = 0
        self.min_after_buy = 0
        self.max_after_buy = 0
        self.bounce_state = None

        self.targets = {
            "sl": 0,
            "tp": 0,
            "ba": 0,
        }

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

    def update_targets(self):
        if self.p.sell_tp_on_avg:
            self.targets["tp"] = self.portfolio_avg_buy_price * self.p.tp
        else:
            self.targets["tp"] = self.last_buy_price * self.p.tp
        if self.p.sell_sl_on_avg:
            self.targets["sl"] = self.portfolio_avg_buy_price * self.p.sl
        else:
            self.targets["sl"] = self.last_buy_price * self.p.sl
        if self.p.buy_again_avg == 1:
            self.targets["ba"] = self.portfolio_avg_buy_price * (self.p.buy_again - (self.p.add_dynamic_ba * self.buy_counter))
        else:
            self.targets["ba"] = self.last_buy_price * (self.p.buy_again - (self.p.add_dynamic_ba * self.buy_counter))

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
        self.update_targets()

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
        self.update_targets()

    def sell_tp(self):
        self.log(f'TP SELL: {self.current_marketcap_str}')
        print("max, min when in position:", self.max_after_buy, self.min_after_buy)
        position_size = self.getposition(self.datas[0]).size
        self.order = self.sell(size=position_size)
        self.just_sold_index = self.index
        self.counters["tp_count"] += 1
        self.add_to_list("tp")
        self.update_targets()

    def sell_no_loss(self):
        self.log(f'NL SELL: {self.current_marketcap_str}')
        position_size = self.getposition(self.datas[0]).size
        self.order = self.sell(size=position_size)
        self.just_sold_index = self.index
        self.counters["nl_count"] += 1
        self.add_to_list("nl")
        self.update_targets()

    def sell_custom(self):
        self.log(f'Custom Exit SELL: {self.current_marketcap_str}')
        print("max, min when in position:", self.max_after_buy, self.min_after_buy)
        position_size = self.getposition(self.datas[0]).size
        self.order = self.sell(size=position_size)
        self.just_sold_index = self.index
        self.counters["cs_count"] += 1
        self.add_to_list("cs")
        self.update_targets()

    def sell_sl(self):
        self.log(f'Defeat SELL: {self.current_marketcap_str}')
        self.order = self.close()
        self.just_sold_index = self.index
        self.counters["sl_count"] += 1
        self.add_to_list("sl")
        self.buy_counter *= -1
        self.update_targets()
