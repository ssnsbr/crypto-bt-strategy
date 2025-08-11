
from strategies.Base import BaseTradingStrategy


from riskmanagers.ABCRiskManagement import AbstractRiskManagement

import backtrader as bt


class MartingaleSizer(bt.Sizer):
    """
    A position sizer that doubles the stake (position size) after each loss.
    This is a classic Martingale strategy, increasing risk after losses.
    """
    params = (
        ('stake_cash', 1000),  # Base cash amount for the initial position
        ('multiplier', 2),
        ('max_multiplier', 16),
    )

    def __init__(self):
        self.loss_streak = 0
        self.cash_to_buy = self.p.stake_cash

    def notify_trade(self, trade):
        """
        Updates the loss streak and cash to buy based on the outcome of a closed trade.
        """
        if trade.isclosed:
            if trade.pnl > 0:
                self.loss_streak = 0
                self.cash_to_buy = self.p.stake_cash
            else:
                self.loss_streak += 1
                multiplier = min(self.p.multiplier ** self.loss_streak, self.p.max_multiplier)
                self.cash_to_buy = self.p.stake_cash * multiplier

    def _getsizing(self, comminfo, cash, data, isbuy):
        """
        Calculates the position size (in units) for the next trade based on the
        cash amount to be spent and the current price.
        """
        if isbuy:
            size = self.cash_to_buy / data.close[0]
            # Ensure we don't try to buy more than available cash
            if self.cash_to_buy > cash:
                size = cash / data.close[0]
            return size
        else:  # Sell order
            return self.getsizing(data)  # Close the entire position


class MartingaleRiskManagement(AbstractRiskManagement):
    """
    Concrete base class for risk management, implementing common TP/SL/Emergency logic.
    """

    def __init__(self, strategy):
        super().__init__(strategy)
        self.dynamic_tp_peak_price = 0.0

    def _calculate_trailing_stop_loss_price(self) -> float:
        if self.strategy.portfolio_total_quantity == 0 or self.strategy.portfolio_highest_price_since_buy == 0:
            return 0.0
        return self.strategy.portfolio_highest_price_since_buy * (1 - self.strategy.p.trailing_sl_percent)

    def _calculate_take_profit_price(self) -> float:
        if self.strategy.portfolio_total_quantity == 0 or self.strategy.portfolio_avg_buy_price == 0:
            return 0.0
        return self.strategy.portfolio_avg_buy_price * (1 + self.strategy.p.tp_percent)

    def _calculate_stop_loss_price(self) -> float:
        if self.strategy.portfolio_total_quantity == 0 or self.strategy.portfolio_avg_buy_price == 0:
            return 0.0
        return self.strategy.portfolio_avg_buy_price * (1 - self.strategy.p.sl_percent)

    def check_and_execute_take_profit(self, current_price: float) -> bool:
        if self.strategy.getposition(self.strategy.datas[0]).size > 0:
            target_profit_price = self._calculate_take_profit_price()
            if current_price >= target_profit_price:
                self.strategy.log(f'FIXED TAKE PROFIT! Selling all {self.strategy.getposition(self.strategy.datas[0]).size:.2f} units. '
                                  f'Price: {self.strategy._format_value_for_log_mcap(current_price)}, '
                                  f'TP Target: {self.strategy._format_value_for_log_mcap(target_profit_price)}')
                self.strategy.order = self.strategy.close()
                return True
        return False

    def check_and_execute_stop_loss(self, current_price: float) -> bool:
        if self.strategy.getposition(self.strategy.datas[0]).size > 0:
            stop_loss_price = self._calculate_stop_loss_price()
            if current_price <= stop_loss_price:
                self.strategy.log(f"STOP LOSS TRIGGERED! Price: {self.strategy._format_value_for_log_mcap(current_price)}, "
                                  f"SL Target: {self.strategy._format_value_for_log_mcap(stop_loss_price)}. "
                                  f"Selling all {self.strategy.getposition(self.strategy.datas[0]).size:.2f} units.")
                self.strategy.order = self.strategy.close()
                return True
        return False

    def check_and_execute_emergency_exit(self, current_price: float) -> bool:
        if self.strategy.emergency_exit_triggered:
            if self.strategy.getposition(self.strategy.datas[0]).size > 0:
                self.strategy.log(f'EMERGENCY EXIT! Price {self.strategy._format_value_for_log_mcap(current_price)}, '
                                  f'Selling all {self.strategy.getposition(self.strategy.datas[0]).size:.2f} units.')
                self.strategy.order = self.strategy.close()
            return True
        return False

    def check_and_execute_dynamic_take_profit(self, current_price: float) -> bool:
        return False

    def check_and_execute_trailing_stop_loss(self, current_price: float) -> bool:
        return False

    def check_and_execute_trailing_take_profit(self, current_price: float) -> bool:
        return False


class SimpleMartingaleStrategy(BaseTradingStrategy):
    """
    A simple Martingale strategy that buys after migration and places
    subsequent buys after a significant price drop. It exits on a fixed
    take-profit percentage from the average buy price.
    """
    params = (
        ('tp_percent', 0.35),  # Take Profit is 35% from the average buy price
        ('sl_percent', 0.50),  # Stop Loss at a 50% drop from the average buy price
        ('martingale_buy_drop', -0.50),  # Buy after a 50% drop from the previous average price
        ('martingale_multiplier', 2.0),  # Multiplier for position size after a loss
        ('max_martingales', 4),  # Maximum number of Martingale buys to prevent excessive risk
        ('rsi_period', 15),
        ('log', True),
    )

    def __init__(self):
        super().__init__()
        self.risk_manager = MartingaleRiskManagement(self)
        self.martingale_buy_trigger_price = 0.0
        self.martingale_buy_count = 0

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
                return
