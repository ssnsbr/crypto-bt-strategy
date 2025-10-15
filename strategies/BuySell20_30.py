

from strategies.Base import BaseTradingStrategy
from riskmanagers.NoneRiskManagement import NoneRiskManagement
import backtrader as bt


class MartingaleSizer(bt.Sizer):
    params = (
        ('stake_cash', 5.0),      # Base cash amount for the initial position
        ('multiplier', 2),        # Multiplier for each subsequent buy
        ('max_multiplier', 16),   # Maximum multiplier cap
        ('percentage', 10),        # % of cash for initial buy (0 disables)
        ('log', True)
    )

    def __init__(self):
        self.buy_count = 0
        self.reset_on_next_buy = False
        self.starter_cash = self.p.stake_cash

    def log(self, text):
        if self.p.log:
            print(text)

    def reset(self):
        """Reset the sizer state - called when starting fresh"""
        self.log("[Sizer] RESET SCHEDULED - Will reset on next buy")
        self.reset_on_next_buy = True

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            # Check if we need to reset
            if self.reset_on_next_buy:
                self.log("[Sizer] RESETTING NOW - Back to Buy #1")
                self.buy_count = 0
                self.reset_on_next_buy = False
                self.starter_cash = self.p.stake_cash

            current_multiplier = min(self.p.multiplier ** self.buy_count, self.p.max_multiplier)
            # --- Initial buy uses percentage of cash ---
            if self.buy_count == 0 and self.p.percentage > 0:
                # Calculate cash amount for this buy
                cash_to_use = cash * (self.p.percentage / 100.0)
                self.starter_cash = cash_to_use
                self.log(f"[Sizer] Initial Buy: {self.p.percentage}% of cash = ${cash_to_use:.2f}")

            else:
                # Subsequent buys use martingale logic
                cash_to_use = self.starter_cash * current_multiplier
                self.log(f"[Sizer] Buy #{self.buy_count + 1}: using ${cash_to_use:.2f} (multiplier: {current_multiplier})")

            # Calculate size from cash amount
            price = data.close[0]
            size = cash_to_use / price

            # Check if we have enough cash (including commission)
            total_cost = size * price * (1 + comminfo.p.commission)
            if total_cost > cash:
                size = cash / (price * (1 + comminfo.p.commission))
                actual_cash = size * price
                self.log(f"[Sizer] Insufficient cash, using available ${actual_cash:.2f}")

            self.log(f"[Sizer] Buy #{self.buy_count + 1}: {size:.2f} units for ${cash_to_use:.2f} (multiplier: {current_multiplier})")

            # Increment buy count for next time
            self.buy_count += 1

            return size
        else:
            # Sell everything
            position = self.broker.getposition(data)
            if position.size > 0:
                self.log(f"[Sizer] Selling all {position.size:.2f} units")
            return position.size

from strategies.Base import BaseTradingStrategy
import backtrader as bt
from riskmanagers.NoneRiskManagement import NoneRiskManagement


class BaseBuySell20_30(BaseTradingStrategy):

    params = (
        ('log', True),
        ('tp', 1.2),                # Take profit at 120% of avg price
        ('sl', 0.6),
        ('buy_again', 0.7),         # Buy again at 70% of avg/last price
        ('max_buy_count', 6),
        ('end_mcap', 20_000),
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

        self.buy_counter = 0
        self.sl_count = 0
        self.tp_count = 0
        self.ib_count = 0
        self.ba_count = 0
        self.ba_round_count = 0
        self.counter_list = []

    def _reset_strategy_state(self):
        super()._reset_strategy_state()
        self.buy_count = 0
        if self.buy_counter:
            self.counter_list.append(self.buy_counter)
        self.buy_counter = 0
        self.just_bought_index = 0
        self.just_sold_index = 0

    def buy_wait(self):
        return self.index < self.just_bought_index + self.min_wait_before_buy

    def sell_wait(self):
        return self.index < self.just_bought_index + self.min_wait_before_sell

    def stop(self):
        """Called once at the end of the strategy"""
        print(
            f"Strategy End  | InitBuy: {self.ib_count} | TP: {self.tp_count} | SL: {self.sl_count} | BuyAgain: {self.ba_round_count}  | BuyAgainAll:{self.ba_count} | self.counter_list: len={len(self.counter_list)} list= {self.counter_list}")

    def init_buy(self):
        self.log(f'Initial BUY: Attempting at {self.current_marketcap_str}')
        self.order = self.buy()
        self.last_buy_price = self.current_price
        self.just_bought_index = self.index
        self.buy_counter = 1
        self.ib_count += 1

    def again_buy(self):
        self.log(f'BUY AGAIN: {self.current_marketcap_str}')
        self.order = self.buy()
        self.last_buy_price = self.current_price
        self.just_bought_index = self.index
        self.buy_counter += 1
        self.ba_count += 1
        if self.buy_counter == 2:
            self.ba_round_count += 1

    def sell_tp(self):
        self.log(f'TP SELL: {self.current_marketcap_str}')
        position_size = self.getposition(self.datas[0]).size
        self.order = self.sell(size=position_size)
        self.just_sold_index = self.index
        self.tp_count += 1

    def sell_sl(self):
        self.log(f'Defeat SELL: {self.current_marketcap_str}')
        self.order = self.close()
        self.just_sold_index = self.index
        self.sl_count += 1

    def _execute_trading_logic(self):
        if not self.migrated or self.done:
            return

        in_position = self.getposition(self.datas[0]).size > 0

        # --- B1: Initial Buy ---
        cond_rsi = self.rsi < self.p.rsi
        if not in_position and cond_rsi and not self.buy_wait():
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
            self.done = True
            return


# ***
####


# class BuySell20Sell30(BaseTradingStrategy):

#     params = (
#         ('log', True),
#         ('tp', 1.2),                # Take profit at 120% of avg price
#         ('sl', 0.7),
#         ('end_mcap', 20_000),
#         ("rsi", 100),
#         ('dead_coin_market_cap', 9_000),
#         ('migration_market_cap', 125_000),
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
#         self.buy_counter = 0

#         self.sl_count = 0
#         self.tp_count = 0
#         self.ib_count = 0
#         self.ba_count = 0

#     def _reset_strategy_state(self):
#         super()._reset_strategy_state()
#         self.buy_count = 0
#         self.buy_counter = 0
#         self.just_bought_index = 0
#         self.just_sold_index = 0

#     def buy_wait(self):
#         return self.index < self.just_bought_index + self.min_wait_before_buy

#     def sell_wait(self):
#         return self.index < self.just_bought_index + self.min_wait_before_sell

#     def notify_trade(self, trade):
#         super().notify_trade(trade)
#         # self.sizer.notify_trade(trade)

#     def stop(self):
#         """Called once at the end of the strategy"""
#         print(
#             f"Strategy End | TP: {self.tp_count} | SL: {self.sl_count} | BuyAgain: {self.ba_count}  | InitBuy: {self.ib_count}")

#     def _execute_trading_logic(self):
#         if not self.migrated or self.done:
#             return

#         in_position = self.getposition(self.datas[0]).size > 0

#         # --- B1: Initial Buy ---
#         cond_rsi = self.rsi < self.p.rsi
#         if not in_position and cond_rsi and not self.buy_wait():
#             self.log(f'Initial BUY: Attempting at {self.current_marketcap_str}')
#             self.order = self.buy()
#             self.just_bought_index = self.index
#             self.buy_counter = 1
#             self.ib_count += 1
#             return

#         # --- S1: TP ---
#         if in_position and not self.sell_wait():
#             sell_cond_tp = self.current_price > self.portfolio_avg_buy_price * self.p.tp
#             sell_cond_sl = self.current_price < self.portfolio_avg_buy_price * self.p.sl

#             if sell_cond_tp:
#                 self.log(f'TP SELL: {self.current_marketcap_str}')
#                 position_size = self.getposition(self.datas[0]).size
#                 self.order = self.sell(size=position_size)
#                 self.just_sold_index = self.index
#                 self.tp_count += 1
#                 self.reset
#                 return

#             elif sell_cond_sl:
#                 self.log(f'TP SELL: {self.current_marketcap_str}')
#                 position_size = self.getposition(self.datas[0]).size
#                 self.order = self.sell(size=position_size)
#                 self.just_sold_index = self.index
#                 self.sl_count += 1
#                 self.reset
#                 return

#         # --- Z: END ---
#         if in_position and self.current_price < self.p.end_mcap:
#             self.log(f'Dead Coin SELL: {self.current_marketcap_str}')
#             self.order = self.close()
#             self.done = True
#             return


# class BuySell20MartingleLastBuy30(BaseTradingStrategy):

#     params = (
#         ('log', True),
#         ('tp', 1.2),                # Take profit at 120% of avg price
#         ('sl', 0.7),
#         ('end_mcap', 20_000),
#         ('buy_again', 0.7),         # Buy again at 70% of avg price
#         ("rsi", 100),
#         ('max_buy_count', 6),

#         ('dead_coin_market_cap', 9_000),
#         ('migration_market_cap', 125_000),
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
#         self.buy_counter = 0

#         self.sl_count = 0
#         self.tp_count = 0
#         self.ib_count = 0
#         self.ba_count = 0
#         self.ba_round_count = 0
#         self.counter_list = []
#         self.last_bought_price = 0
#         self.accept_sl = 0

#     def _reset_strategy_state(self):
#         super()._reset_strategy_state()
#         self.buy_count = 0
#         if self.buy_counter:
#             self.counter_list.append(self.buy_counter)
#         self.buy_counter = 0
#         self.just_bought_index = 0
#         self.just_sold_index = 0

#     def buy_wait(self):
#         return self.index < self.just_bought_index + self.min_wait_before_buy

#     def sell_wait(self):
#         return self.index < self.just_bought_index + self.min_wait_before_sell

#     def notify_trade(self, trade):
#         super().notify_trade(trade)
#         # self.sizer.notify_trade(trade)

#     def stop(self):
#         """Called once at the end of the strategy"""
#         print(
#             f"Strategy End | TP: {self.tp_count} | SL: {self.sl_count} | BuyAgain: {self.ba_count}  | InitBuy: {self.ib_count}")

#     def _execute_trading_logic(self):
#         if not self.migrated or self.done:
#             return

#         in_position = self.getposition(self.datas[0]).size > 0

#         # --- B1: Initial Buy ---
#         cond_rsi = self.rsi < self.p.rsi
#         if not in_position and cond_rsi and not self.buy_wait():
#             self.log(f'Initial BUY: Attempting at {self.current_marketcap_str}')
#             self.order = self.buy()
#             self.just_bought_index = self.index
#             self.buy_counter = 1
#             self.ib_count += 1
#             self.last_bought_price = self.current_price
#             return

#         # --- S1: TP ---
#         if in_position and not self.sell_wait():
#             sell_cond_tp = self.current_price > self.portfolio_avg_buy_price * self.p.tp
#             if sell_cond_tp:
#                 self.log(f'TP SELL: {self.current_marketcap_str}')
#                 position_size = self.getposition(self.datas[0]).size
#                 self.order = self.sell(size=position_size)
#                 self.just_sold_index = self.index
#                 self.tp_count += 1
#                 self.reset
#                 return

#         # --- B2: Averaging Down ---
#         buy_cond = self.current_price < self.last_bought_price * self.p.buy_again
#         if in_position and buy_cond and self.buy_counter < self.p.max_buy_count:
#             self.log(f'BUY AGAIN: {self.current_marketcap_str}')
#             self.order = self.buy()
#             self.just_bought_index = self.index
#             self.buy_counter += 1
#             self.ba_count += 1
#             if self.buy_counter == 1:
#                 self.ba_round_count += 1
#             return

#         # --- S2: Defeat Stop ---
#         defeat_con_1 = self.buy_counter >= self.p.max_buy_count
#         defeat_con_2 = self.current_price < self.portfolio_avg_buy_price * self.p.sl
#         if in_position and defeat_con_1 and defeat_con_2:
#             self.log(f'Defeat SELL: {self.current_marketcap_str}')
#             self.order = self.close()
#             self.just_sold_index = self.index
#             self.sl_count += 1
#             self.accept_sl += 1
#             return

#         # --- Z: END ---
#         if in_position and self.current_price < self.p.end_mcap:
#             self.log(f'Dead Coin SELL: {self.current_marketcap_str}')
#             self.order = self.close()
#             self.done = True
#             return


# class BuySell20MartingleAVGBuy30(BaseTradingStrategy):

#     params = (
#         ('log', True),
#         ('tp', 1.2),                # Take profit at 120% of avg price
#         ('sl', 0.7),
#         ('end_mcap', 20_000),
#         ('buy_again', 0.7),         # Buy again at 70% of avg price
#         ("rsi", 100),
#         ('max_buy_count', 6),
#         ('dead_coin_market_cap', 9_000),
#         ('migration_market_cap', 125_000),
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
#         self.buy_counter = 0

#         self.sl_count = 0
#         self.tp_count = 0
#         self.ib_count = 0
#         self.ba_count = 0
#         self.ba_round_count = 0
#         self.counter_list = []

#     def _reset_strategy_state(self):
#         super()._reset_strategy_state()
#         self.buy_count = 0
#         if self.buy_counter:
#             self.counter_list.append(self.buy_counter)
#         self.buy_counter = 0
#         self.just_bought_index = 0
#         self.just_sold_index = 0

#     def buy_wait(self):
#         return self.index < self.just_bought_index + self.min_wait_before_buy

#     def sell_wait(self):
#         return self.index < self.just_bought_index + self.min_wait_before_sell

#     def notify_trade(self, trade):
#         super().notify_trade(trade)
#         # self.sizer.notify_trade(trade)

#     def stop(self):
#         """Called once at the end of the strategy"""
#         print(
#             f"Strategy End | TP: {self.tp_count} | SL: {self.sl_count} | BuyAgain: {self.ba_count}  | InitBuy: {self.ib_count}")

#     def _execute_trading_logic(self):
#         if not self.migrated or self.done:
#             return

#         in_position = self.getposition(self.datas[0]).size > 0

#         # --- B1: Initial Buy ---
#         cond_rsi = self.rsi < self.p.rsi
#         if not in_position and cond_rsi and not self.buy_wait():
#             self.log(f'Initial BUY: Attempting at {self.current_marketcap_str}')
#             self.order = self.buy()
#             self.just_bought_index = self.index
#             self.buy_counter = 1
#             self.ib_count += 1

#             return

#         # --- S1: TP ---
#         if in_position and not self.sell_wait():
#             sell_cond_tp = self.current_price > self.portfolio_avg_buy_price * self.p.tp
#             if sell_cond_tp:
#                 self.log(f'TP SELL: {self.current_marketcap_str}')
#                 position_size = self.getposition(self.datas[0]).size
#                 self.order = self.sell(size=position_size)
#                 self.just_sold_index = self.index
#                 self.tp_count += 1
#                 self.reset
#                 return

#         # --- B2: Averaging Down ---
#         buy_cond = self.current_price < self.portfolio_avg_buy_price * self.p.buy_again
#         if in_position and buy_cond and self.buy_counter < self.p.max_buy_count:
#             self.log(f'BUY AGAIN: {self.current_marketcap_str}')
#             self.order = self.buy()
#             self.just_bought_index = self.index
#             self.buy_counter += 1
#             self.ba_count += 1
#             if self.buy_counter == 1:
#                 self.ba_round_count += 1
#             return

#         # --- S2: Defeat Stop ---
#         defeat_con_1 = self.buy_counter >= self.p.max_buy_count
#         defeat_con_2 = self.current_price < self.portfolio_avg_buy_price * self.p.sl
#         if in_position and defeat_con_1 and defeat_con_2:
#             self.log(f'Defeat SELL: {self.current_marketcap_str}')
#             self.order = self.close()
#             self.just_sold_index = self.index
#             self.sl_count += 1

#             return

#         # --- Z: END ---
#         if in_position and self.current_price < self.p.end_mcap:
#             self.log(f'Dead Coin SELL: {self.current_marketcap_str}')
#             self.order = self.close()
#             self.done = True
#             return
