
class ScalperRiskManagement:
    """
    Manages the take-profit and stop-loss logic for a trading strategy.
    It interacts with the main strategy object to access data, position, and logging.
    """

    def __init__(self, strategy):
        self.strategy = strategy  # Reference to the main strategy instance

    def _calculate_trailing_stop_loss_price(self) -> float:
        """
        Calculates the trailing stop-loss price.
        Currently, this method is present but not actively used for exits in the provided logic.
        It's kept here for completeness and potential future use.
        """
        if self.strategy.portfolio_total_quantity == 0 or self.strategy.portfolio_avg_buy_price == 0:
            return 0.0

        # Example dynamic TSL factor (adjust as per strategy needs)
        dynamic_tsl_factor = 1 - 0.55  # This means stop loss is at 45% of highest price since buy
        return self.strategy.portfolio_highest_price_since_buy * dynamic_tsl_factor

    def _calculate_take_profit_price(self) -> float:
        """
        Calculates the take-profit price based on the average buy price and dynamic factors.
        The TP target slightly increases with deeper Fibo buy levels to recover losses faster.
        """
        if self.strategy.portfolio_total_quantity == 0 or self.strategy.portfolio_avg_buy_price == 0:
            return 0.0

        min_profit_take_percent = 0.01  # Ensure a minimum profit target of 1%

        # Dynamic TP factor: increases slightly with each deeper Fibo buy
        # This incentivizes closing out positions that have accumulated at lower levels
        dynamic_tp_factor = (1 + self.strategy.p.initial_tp_percent) + (self.strategy.current_fibo_buy_level_idx * 0.005)

        # Make sure TP factor is at least the minimum profit
        dynamic_tp_factor = max(dynamic_tp_factor, 1 + min_profit_take_percent)

        return self.strategy.portfolio_avg_buy_price * dynamic_tp_factor

    def check_and_execute_take_profit(self, current_price):
        """
        Checks if the take-profit condition is met and executes a sell order if it is.
        Returns True if a TP order was placed, False otherwise.
        """
        if self.strategy.getposition(self.strategy.datas[0]).size > 0:
            target_profit_price = self._calculate_take_profit_price()

            if current_price >= target_profit_price:
                self.strategy.log(f'TAKE PROFIT! Selling all {self.strategy.getposition(self.strategy.datas[0]).size:.2f} units. '
                                  f'MarketCap: {self.strategy._format_value_for_log_mcap(current_price)}, '
                                  f'TP Target: {self.strategy._format_value_for_log_mcap(target_profit_price)}')
                self.strategy.order = self.strategy.close()  # Sell the entire current position
                return True
        return False

    def check_and_execute_global_stop_loss(self, current_price):
        """
        Checks if the global stop-loss condition is met and executes a sell order if it is.
        This is the highest priority exit rule.
        Returns True if a SL order was placed, False otherwise.
        """
        if self.strategy.getposition(self.strategy.datas[0]).size > 0:  # Only check if we have an open position
            # Calculate global stop loss based on initial parameter
            global_stop_loss_price = self.strategy.portfolio_avg_buy_price * (1 - self.strategy.p.global_sl_percent)
            # global_stop_loss_marketcap_str = self.strategy._format_value_for_log_mcap(global_stop_loss_price) # Not used

            if current_price <= global_stop_loss_price:
                self.strategy.log(f"GLOBAL STOP LOSS TRIGGERED! MarketCap: {self.strategy._format_value_for_log_mcap(current_price)}, "
                                  f"SL Target: {self.strategy._format_value_for_log_mcap(global_stop_loss_price)}. "
                                  f"Selling all {self.strategy.getposition(self.strategy.datas[0]).size:.2f} units.")
                self.strategy.order = self.strategy.close()  # Backtrader's self.close() sells the entire current position
                # Set finish_and_runaway to True as this is a catastrophic exit
                self.strategy.finish_and_runaway = True
                return True
        return False

    def check_and_execute_dead_coin_exit(self, current_price):
        """
        Checks if the dead coin condition is met and executes a sell order if it is.
        Returns True if a dead coin exit order was placed, False otherwise.
        """
        if self.strategy.dead_coin:
            if self.strategy.getposition(self.strategy.datas[0]).size > 0:
                self.strategy.log(f'COIN DEAD! MarketCap {self.strategy._format_value_for_log_mcap(current_price)}, '
                                  f'<= Dead Coin Threshold {self.strategy._format_value_for_log_mcap(self.strategy.dead_coin_market_cap)}. '
                                  f'Selling all {self.strategy.getposition(self.strategy.datas[0]).size:.2f} units.')
                self.strategy.order = self.strategy.close()
            self.strategy.finish_and_runaway = True  # End operations for this coin
            return True
        return False
