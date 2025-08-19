from riskmanagers import NoneRiskManagement
from strategies.Base import BaseTradingStrategy


class _20_100(BaseTradingStrategy):
    """
    A simple Martingale strategy that buys after migration and places
    subsequent buys after a significant price drop. It exits on a fixed
    take-profit percentage from the average buy price.
    """
    params = (
        ('log', True),
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
        buy_cond = self.current_price < 20_000
        sell_cond = self.current_price < 9_000 or self.current_price > 80_000

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
