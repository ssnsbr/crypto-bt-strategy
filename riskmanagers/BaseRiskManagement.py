
from riskmanagers.ABCRiskManagement import AbstractRiskManagement


class BaseRiskManagement(AbstractRiskManagement):
    """
    Concrete base class for risk management, implementing common TP/SL/Emergency logic.
    Derived risk management classes can inherit from this and override specific methods.
    """

    def __init__(self, strategy):
        super().__init__(strategy)
        # Internal state for Dynamic Take Profit
        self.dynamic_tp_peak_price = 0.0

    def _calculate_trailing_stop_loss_price(self) -> float:
        """
        Calculates the trailing stop-loss price based on the highest price reached
        since the last buy and the strategy's trailing_sl_percent.
        """
        if self.strategy.portfolio_total_quantity == 0 or self.strategy.portfolio_highest_price_since_buy == 0:
            return 0.0
        return self.strategy.portfolio_highest_price_since_buy * (1 - self.strategy.p.trailing_sl_percent)

    def _calculate_trailing_take_profit_price(self) -> float:
        """
        Calculates the trailing take-profit price based on the highest price reached
        since the last buy and the strategy's trailing_tp_percent.
        """
        if self.strategy.portfolio_total_quantity == 0 or self.strategy.portfolio_highest_price_since_buy == 0:
            return 0.0
        return self.strategy.portfolio_highest_price_since_buy * (1 - self.strategy.p.trailing_tp_percent)

    def _calculate_take_profit_price(self) -> float:
        """
        Calculates the fixed take-profit price based on the average buy price.
        This is a default implementation; specific strategies might override it.
        """
        if self.strategy.portfolio_total_quantity == 0 or self.strategy.portfolio_avg_buy_price == 0:
            return 0.0
        return self.strategy.portfolio_avg_buy_price * (1 + self.strategy.p.tp_percent)

    def _calculate_stop_loss_price(self) -> float:
        """
        Calculates the stop-loss price based on the average buy price.
        This is a default implementation; specific strategies might override it.
        """
        if self.strategy.portfolio_total_quantity == 0 or self.strategy.portfolio_avg_buy_price == 0:
            return 0.0
        return self.strategy.portfolio_avg_buy_price * (1 - self.strategy.p.sl_percent)

    def check_and_execute_take_profit(self, current_price: float) -> bool:
        """
        Checks if the fixed take-profit condition is met and executes a sell order if it is.
        """
        if self.strategy.getposition(self.strategy.datas[0]).size > 0:
            target_profit_price = self._calculate_take_profit_price()
            if current_price >= target_profit_price:
                self.strategy.log(f'FIXED TAKE PROFIT! Selling all {self.strategy.getposition(self.strategy.datas[0]).size:.2f} units. '
                                  f'MarketCap: {self.strategy._format_value_for_log_mcap(current_price)}, '
                                  f'TP Target: {self.strategy._format_value_for_log_mcap(target_profit_price)}')
                self.strategy.order = self.strategy.close()
                return True
        return False

    def check_and_execute_stop_loss(self, current_price: float) -> bool:
        """
        Checks if the stop-loss condition is met and executes a sell order if it is.
        """
        if self.strategy.getposition(self.strategy.datas[0]).size > 0:
            stop_loss_price = self._calculate_stop_loss_price()
            if current_price <= stop_loss_price:
                self.strategy.log(f"STOP LOSS TRIGGERED! MarketCap: {self.strategy._format_value_for_log_mcap(current_price)}, "
                                  f"SL Target: {self.strategy._format_value_for_log_mcap(stop_loss_price)}. "
                                  f"Selling all {self.strategy.getposition(self.strategy.datas[0]).size:.2f} units.")
                self.strategy.order = self.strategy.close()
                return True
        return False

    def check_and_execute_emergency_exit(self, current_price: float) -> bool:
        """
        Checks if the emergency condition (e.g., dead coin) is met and executes a sell order if it is.
        """
        if self.strategy.emergency_exit_triggered:
            if self.strategy.getposition(self.strategy.datas[0]).size > 0:
                self.strategy.log(f'EMERGENCY EXIT! MarketCap {self.strategy._format_value_for_log_mcap(current_price)}, '
                                  f'Selling all {self.strategy.getposition(self.strategy.datas[0]).size:.2f} units.')
                self.strategy.order = self.strategy.close()
            return True
        return False

    def check_and_execute_trailing_stop_loss(self, current_price: float) -> bool:
        """
        Checks if the trailing stop-loss condition is met and executes a sell order if it is.
        """
        if self.strategy.getposition(self.strategy.datas[0]).size > 0:
            pnl_percent = (current_price / self.strategy.portfolio_avg_buy_price) - 1.0
            if pnl_percent >= self.strategy.p.trailing_sl_activation_profit_percent:
                trailing_sl_price = self._calculate_trailing_stop_loss_price()
                if current_price <= trailing_sl_price:
                    self.strategy.log(f"TRAILING STOP LOSS TRIGGERED! MarketCap: {self.strategy._format_value_for_log_mcap(current_price)}, "
                                      f"TSL Target: {self.strategy._format_value_for_log_mcap(trailing_sl_price)}. "
                                      f"Selling all {self.strategy.getposition(self.strategy.datas[0]).size:.2f} units.")
                    self.strategy.order = self.strategy.close()
                    return True
        return False

    def check_and_execute_trailing_take_profit(self, current_price: float) -> bool:
        """
        Checks if the trailing take-profit condition is met and executes a sell order if it is.
        """
        if self.strategy.getposition(self.strategy.datas[0]).size > 0:
            pnl_percent = (current_price / self.strategy.portfolio_avg_buy_price) - 1.0
            if pnl_percent >= self.strategy.p.trailing_tp_activation_profit_percent:
                trailing_tp_price = self._calculate_trailing_take_profit_price()
                if current_price <= trailing_tp_price:
                    self.strategy.log(f"TRAILING TAKE PROFIT TRIGGERED! MarketCap: {self.strategy._format_value_for_log_mcap(current_price)}, "
                                      f"TTP Target: {self.strategy._format_value_for_log_mcap(trailing_tp_price)}. "
                                      f"Selling all {self.strategy.getposition(self.strategy.datas[0]).size:.2f} units.")
                    self.strategy.order = self.strategy.close()
                    return True
        return False

    def check_and_execute_dynamic_take_profit(self, current_price: float) -> bool:
        """
        Checks if the dynamic take-profit condition is met and executes a sell order if it is.
        """
        if not self.strategy.getposition(self.strategy.datas[0]).size > 0:
            return False

        pnl_percent = (current_price / self.strategy.portfolio_avg_buy_price) - 1.0

        if pnl_percent >= self.strategy.p.dynamic_tp_activation_profit_percent:
            self.dynamic_tp_peak_price = max(self.dynamic_tp_peak_price, current_price)
            dynamic_tp_trigger_price = self.dynamic_tp_peak_price * (1 - self.strategy.p.dynamic_tp_pullback_percent)

            if current_price <= dynamic_tp_trigger_price:
                self.strategy.log(f"DYNAMIC TAKE PROFIT TRIGGERED! MarketCap: {self.strategy._format_value_for_log_mcap(current_price)}, "
                                  f"Peak Price: {self.strategy._format_value_for_log_mcap(self.dynamic_tp_peak_price)}, "
                                  f"DTP Target: {self.strategy._format_value_for_log_mcap(dynamic_tp_trigger_price)}. "
                                  f"Selling all {self.strategy.getposition(self.strategy.datas[0]).size:.2f} units.")
                self.strategy.order = self.strategy.close()
                self.dynamic_tp_peak_price = 0.0
                return True
        else:
            self.dynamic_tp_peak_price = 0.0
        return False
