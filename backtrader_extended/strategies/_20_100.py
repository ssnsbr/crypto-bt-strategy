
from backtrader_extended.strategies.Base import BaseTradingStrategy


from riskmanagers.noneRiskManagement import NoneRiskManagement
from riskmanagers.MartingaleRiskManagement import MartingaleRiskManagement

# from utils.utils import format_marketcap, format_price_to_marketcap


class _20_100(BaseTradingStrategy):
    """
    A simple Martingale strategy that buys after migration and places
    subsequent buys after a significant price drop. It exits on a fixed
    take-profit percentage from the average buy price.
    """
    params = (
        ('log', True),
        ('buy_mcap', 12_000),
        ('tp_mcap', 19_000),
        ('sl_mcap', 8_000)
    )

    def __init__(self):
        super().__init__()
        self.risk_manager = NoneRiskManagement(self)
        self.martingale_buy_trigger_price = 0.0
        self.martingale_buy_count = 0
        self.wait_at_least = 5
        self.waiting = 0
        self.done = False
        self.selled = False
        self.bought = False

    def _execute_trading_logic(self):
        """
        This is the core of the strategy, implementing the buy and sell logic.
        """
        if not self.migrated:
            return
        if self.done:
            return
        if self.selled:
            if self.waiting > self.wait_at_least:
                self.done = True
                return
            self.waiting += 1

        # --- Rule 1: Initial Buy ---
        # Conditions :
        # 1 - After Migration
        # 2 - RSI < 40
        # 3 - Not Already In a position
        # 4 - Buy at 20k mcap
        not_in_position = self.getposition(self.datas[0]).size == 0
        cond_rsi = self.rsi < 40
        buy_cond = self.current_price < self.p.buy_mcap
        sell_cond = self.current_price < self.p.sl_mcap or self.current_price > self.p.tp_mcap

        if not not_in_position and sell_cond and self.migrated:
            self.log(f'Stop Loss triggered at {self.current_marketcap_str}')
            self.order = self.close()
            self.selled = True
            return
        if self.bought:
            return
        if not_in_position and cond_rsi and buy_cond and self.migrated:
            self.log(f'Initial BUY: Attempting to buy at {self.current_marketcap_str}')
            # Let the sizer determine the size. It will use the base stake.
            self.order = self.buy()
            self.bought = True
            return


class _20_100_14x(BaseTradingStrategy):
    """
    A simple Martingale strategy that buys after migration and places
    subsequent buys after a significant price drop. It exits on a fixed
    take-profit percentage from the average buy price.
    """
    params = (
        ('log', True),
        ('buy_mcap', 20_000),
        ('sl_mcap', 9_000)
    )

    def __init__(self):
        super().__init__()
        self.risk_manager = NoneRiskManagement(self)
        self.martingale_buy_trigger_price = 0.0
        self.martingale_buy_count = 0
        self.wait_at_least = 5
        self.waiting = 0
        self.done = False
        self.selled = False
        self.bought = False
        self.multiplier = 1.4
        self.current_tp_mcap = self.p.buy_mcap * self.multiplier
        self.wait_new_sell = 0

    def _execute_trading_logic(self):
        """
        This is the core of the strategy, implementing the buy and sell logic.
        """
        if not self.migrated:
            return
        if self.done:
            return
        if self.selled:
            if self.waiting > self.wait_at_least:
                self.done = True
                return
            self.waiting += 1

        if self.wait_new_sell > 0:
            self.wait_new_sell -= 1
            return
        # --- Rule 1: Initial Buy ---
        # Conditions :
        # 1 - After Migration
        # 2 - RSI < 40
        # 3 - Not Already In a position
        # 4 - Buy at 20k mcap
        not_in_position = self.getposition(self.datas[0]).size == 0
        cond_rsi = self.rsi < 40
        buy_cond = self.current_price < self.p.buy_mcap
        sell_cond_sl = self.current_price < self.ath * 0.8
        sell_cond_tp = self.current_price > self.current_tp_mcap

        # TP
        if not not_in_position and self.migrated and sell_cond_tp:
            self.log(f'PARTIAL SELL: Selling half at {self.current_marketcap_str}')
            position_size = self.getposition(self.datas[0]).size
            sell_size = position_size / 5
            self.order = self.sell(size=sell_size)
            self.current_tp_mcap = self.multiplier * self.current_tp_mcap
            self.wait_new_sell = 3
            return

        # SL
        if not not_in_position and sell_cond_sl and self.migrated:
            self.log(f'Stop Loss triggered at {self.current_marketcap_str}')
            self.order = self.close()
            self.selled = True
            return

        if self.bought:
            return
        if not_in_position and cond_rsi and buy_cond and self.migrated:
            self.log(f'Initial BUY: Attempting to buy at {self.current_marketcap_str}')
            # Let the sizer determine the size. It will use the base stake.
            self.order = self.buy()
            self.bought = True
            return


class SimpleMartingaleStrategy(BaseTradingStrategy):
    """
    A simple Martingale strategy that buys after migration and places
    subsequent buys after a significant price drop. It exits on a fixed
    take-profit percentage from the average buy price.
    """
    params = (
        ('tp_percent', 0.25),  # Take Profit is 35% from the average buy price
        ('sl_percent', 0.90),  # Stop Loss at a 50% drop from the average buy price
        ('martingale_buy_drop', -0.50),  # Buy after a 50% drop from the previous average price
        ('martingale_multiplier', 2.0),  # Multiplier for position size after a loss
        ('max_martingales', 4),  # Maximum number of Martingale buys to prevent excessive risk
        # ('rsi_period', 15),
        ('log', True),
    )

    def __init__(self):
        super().__init__()
        self.risk_manager = MartingaleRiskManagement(self)
        self.martingale_buy_trigger_price = 0.0
        self.martingale_buy_count = 0
        self.wait_at_least = 2
        self.waiting = 0

    def _reset_strategy_state(self):
        super()._reset_strategy_state()
        self.martingale_buy_trigger_price = 0.0
        self.martingale_buy_count = 0

    def notify_order(self, order):
        """
        Overrides the base class method to update the Martingale trigger price
        after a buy order is completed.
        """
        super().notify_order(order)
        if order.status == order.Completed and order.isbuy():
            # After a successful buy, set the trigger for the next Martingale buy
            self.martingale_buy_trigger_price = self.portfolio_avg_buy_price * (1 + self.p.martingale_buy_drop)
            self.log(f"Next Martingale buy trigger price set to "
                     f"{self._format_value_for_log_mcap(self.martingale_buy_trigger_price)}")

    def _execute_trading_logic(self):
        """
        This is the core of the strategy, implementing the buy and sell logic.
        """
        if not self.migrated:
            return
        if self.waiting < self.wait_at_least:
            self.waiting += 1
            return
        # --- Rule 1: Initial Buy ---
        # Conditions :
        # 1 - After Migration
        # 2 - RSI < 40
        # 3 - Not Already In a position
        not_in_position = self.getposition(self.datas[0]).size == 0
        cond_rsi = self.rsi < 40

        if not_in_position and cond_rsi and self.migrated:
            self.log(f'Initial BUY: Attempting to buy at {self.current_marketcap_str}')
            # Let the sizer determine the size. It will use the base stake.
            self.order = self.buy()
            self.martingale_buy_count += 1
            self.waiting = 0
            return

        # --- Rule 2: Martingale Buy ---
        # If price drops and we are in a position, buy more.
        # This will be triggered only after a buy has been completed.
        if self.getposition(self.datas[0]).size > 0 and self.martingale_buy_count < self.p.max_martingales:
            if self.current_price <= self.martingale_buy_trigger_price:
                self.log(f'MARTINGALE BUY #{self.martingale_buy_count + 1}: '
                         f'Price dropped, buying more at {self.current_marketcap_str}')
                self.order = self.buy()
                self.martingale_buy_count += 1
                self.waiting = 0
                return
