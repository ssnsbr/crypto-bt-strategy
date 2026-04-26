

from riskmanagers.ABCRiskManagement import AbstractRiskManagement


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
