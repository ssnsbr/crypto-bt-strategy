
import backtrader as bt
from riskmanagers import NoneRiskManagement
from strategies.Base import BaseTradingStrategy


class MartingaleSizer(bt.Sizer):
    params = (
        ('stake_cash', 5.0),      # Base cash amount for the initial position
        ('multiplier', 2),        # Multiplier for each subsequent buy
        ('max_multiplier', 16),   # Maximum multiplier cap
    )

    def __init__(self):
        self.buy_count = 0
        self.reset_on_next_buy = False

    def reset(self):
        """Reset the sizer state - called when starting fresh"""
        print(f"[Sizer] RESET SCHEDULED - Will reset on next buy")
        self.reset_on_next_buy = True

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            # Check if we need to reset
            if self.reset_on_next_buy:
                print(f"[Sizer] RESETTING NOW - Back to Buy #1")
                self.buy_count = 0
                self.reset_on_next_buy = False

            # Calculate multiplier for this buy
            current_multiplier = min(self.p.multiplier ** self.buy_count, self.p.max_multiplier)

            # Calculate cash amount for this buy
            cash_to_use = self.p.stake_cash * current_multiplier

            # Calculate size from cash amount
            price = data.close[0]
            size = cash_to_use / price

            # Check if we have enough cash (including commission)
            total_cost = size * price * (1 + comminfo.p.commission)
            if total_cost > cash:
                size = cash / (price * (1 + comminfo.p.commission))
                actual_cash = size * price
                print(f"[Sizer] Insufficient cash, using available ${actual_cash:.2f}")

            print(f"[Sizer] Buy #{self.buy_count + 1}: {size:.2f} units for ${cash_to_use:.2f} (multiplier: {current_multiplier})")

            # Increment buy count for next time
            self.buy_count += 1

            return size
        else:
            # Sell everything
            position = self.broker.getposition(data)
            if position.size > 0:
                print(f"[Sizer] Selling all {position.size:.2f} units")
            return position.size


class SimplyBuy(BaseTradingStrategy):
    """
    A simple Martingale strategy that buys after migration and places
    subsequent buys after a significant price drop. It exits on a fixed
    take-profit percentage from the average buy price.
    """
    params = (
        ('log', True),
        ('buy_again', 0.7),         # Buy again at 70% of avg price
        ('tp', 1.2),                # Take profit at 120% of avg price
        ('sl', 0.3),
        ('max_buy_count', 6),
        ('end_mcap', 9_000),
    )

    def __init__(self):
        super().__init__()
        self.risk_manager = NoneRiskManagement(self)
        self.buy_count = 0
        self.done = False

        self.just_bought_index = 0
        self.just_sold_index = 0

        self.min_wait_before_buy = 5
        self.min_wait_before_sell = 1
        self.buy_counter = 0

        self.sl_count = 0
        self.tp_count = 0
        self.ib_count = 0
        self.ba_count = 0

    def _reset_strategy_state(self):
        super()._reset_strategy_state()
        self.buy_count = 0
        self.buy_counter = 0
        self.just_bought_index = 0
        self.just_sold_index = 0

    def buy_wait(self):
        return self.index < self.just_bought_index + self.min_wait_before_buy

    def sell_wait(self):
        return self.index < self.just_bought_index + self.min_wait_before_sell

    def notify_trade(self, trade):
        super().notify_trade(trade)
        # self.sizer.notify_trade(trade)

    def stop(self):
        """Called once at the end of the strategy"""
        print(
            f"Strategy End | TP: {self.tp_count} | SL: {self.sl_count} | BuyAgain: {self.ba_count}  | InitBuy: {self.ib_count}")

    def _execute_trading_logic(self):
        if not self.migrated or self.done:
            return

        in_position = self.getposition(self.datas[0]).size > 0

        # --- B1: Initial Buy ---
        cond_rsi = self.rsi < 40
        if not in_position and cond_rsi and not self.buy_wait():
            self.log(f'Initial BUY: Attempting at {self.current_marketcap_str}')
            self.order = self.buy()
            self.just_bought_index = self.index
            self.buy_counter = 1
            self.ib_count += 1

            return

        # --- S1: TP ---
        if in_position and not self.sell_wait():
            sell_cond_tp = self.current_price > self.portfolio_avg_buy_price * self.p.tp
            if sell_cond_tp:
                self.log(f'TP SELL: {self.current_marketcap_str}')
                position_size = self.getposition(self.datas[0]).size
                self.order = self.sell(size=position_size)
                self.just_sold_index = self.index
                self.tp_count += 1
                self.reset
                return

        # --- B2: Averaging Down ---
        buy_cond = self.current_price < self.portfolio_avg_buy_price * self.p.buy_again
        if in_position and buy_cond and self.buy_counter < self.p.max_buy_count:
            self.log(f'BUY AGAIN: {self.current_marketcap_str}')
            self.order = self.buy()
            self.just_bought_index = self.index
            self.buy_counter += 1
            self.ba_count += 1

            return

        # --- S2: Defeat Stop ---
        defeat_con_1 = self.buy_counter >= self.p.max_buy_count
        defeat_con_2 = self.current_price < self.portfolio_avg_buy_price * self.p.sl
        if in_position and defeat_con_1 and defeat_con_2:
            self.log(f'Defeat SELL: {self.current_marketcap_str}')
            self.order = self.close()
            self.just_sold_index = self.index
            self.sl_count += 1

            return

        # --- Z: END ---
        if in_position and self.current_price < self.p.end_mcap:
            self.log(f'Dead Coin SELL: {self.current_marketcap_str}')
            self.order = self.close()
            self.done = True
            return


class SimplyBuy2(BaseTradingStrategy):
    """
    A simple Martingale strategy that buys after migration and places
    subsequent buys after a significant price drop. It exits on a fixed
    take-profit percentage from the average buy price.
    """
    params = (
        ('log', True),
        ('buy_again', 0.7),         # Buy again at 70% of avg price
        ('tp', 1.2),                # Take profit at 120% of avg price
        ('sl', 0.3),
        ('max_buy_count', 6),
        ('end_mcap', 9_000),
    )

    def __init__(self):
        super().__init__()
        self.risk_manager = NoneRiskManagement(self)
        self.buy_count = 0
        self.done = False

        self.just_bought_index = 0
        self.just_sold_index = 0

        self.min_wait_before_buy = 5
        self.min_wait_before_sell = 1
        self.buy_counter = 0

        self.sl_count = 0
        self.tp_count = 0
        self.ib_count = 0
        self.ba_count = 0

    def _reset_strategy_state(self):
        super()._reset_strategy_state()
        self.buy_count = 0
        self.buy_counter = 0
        self.just_bought_index = 0
        self.just_sold_index = 0

    def buy_wait(self):
        return self.index < self.just_bought_index + self.min_wait_before_buy

    def sell_wait(self):
        return self.index < self.just_bought_index + self.min_wait_before_sell

    def notify_trade(self, trade):
        super().notify_trade(trade)
        # self.sizer.notify_trade(trade)

    def stop(self):
        """Called once at the end of the strategy"""
        print(
            f"Strategy End | TP: {self.tp_count} | SL: {self.sl_count} | BuyAgain: {self.ba_count}  | InitBuy: {self.ib_count}")

    def _execute_trading_logic(self):
        if not self.migrated or self.done:
            return

        in_position = self.getposition(self.datas[0]).size > 0

        # --- B1: Initial Buy ---
        cond_rsi = self.rsi < 40
        if not in_position and cond_rsi and not self.buy_wait():
            self.log(f'Initial BUY: Attempting at {self.current_marketcap_str}')
            self.order = self.buy()
            self.just_bought_index = self.index
            self.buy_counter = 1
            self.ib_count += 1

            return

        # --- S1: TP ---
        if in_position and not self.sell_wait():
            sell_cond_tp = self.current_price > self.portfolio_avg_buy_price * self.p.tp
            if sell_cond_tp:
                self.log(f'TP SELL: {self.current_marketcap_str}')
                position_size = self.getposition(self.datas[0]).size
                self.order = self.sell(size=position_size)
                self.just_sold_index = self.index
                self.tp_count += 1
                self.reset
                return

        # --- B2: Averaging Down ---
        buy_cond = self.current_price < self.portfolio_avg_buy_price * self.p.buy_again
        if in_position and buy_cond and self.buy_counter < self.p.max_buy_count:
            self.log(f'BUY AGAIN: {self.current_marketcap_str}')
            self.order = self.close()
            # self.order =
            self.just_bought_index = self.index
            self.buy_counter += 1
            self.ba_count += 1

            return

        # --- S2: Defeat Stop ---
        # defeat_con_1 = self.buy_counter >= self.p.max_buy_count
        # defeat_con_2 = self.current_price < self.portfolio_avg_buy_price * self.p.sl
        # if in_position and defeat_con_1 and defeat_con_2:
        #     self.log(f'Defeat SELL: {self.current_marketcap_str}')
        #     self.order = self.close()
        #     self.just_sold_index = self.index
        #     self.sl_count += 1

            return

        # --- Z: END ---
        if in_position and self.current_price < self.p.end_mcap:
            self.log(f'Dead Coin SELL: {self.current_marketcap_str}')
            self.order = self.close()
            self.done = True
            return
