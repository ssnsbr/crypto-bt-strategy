

from riskmanagers.BaseRiskManagement import BaseRiskManagement


class FiboRiskManagement(BaseRiskManagement):
    """
    Manages the take-profit and stop-loss logic specifically for the FiboMartingaleStrategy.
    Overrides _calculate_take_profit_price for Fibo-specific dynamic TP factor.
    """

    def __init__(self, strategy):
        super().__init__(strategy)  # Call the constructor of the base class

    def _calculate_take_profit_price(self) -> float:
        """
        Calculates the fixed take-profit price based on the average buy price and dynamic factors.
        The TP target slightly increases with deeper Fibo buy levels to recover losses faster.
        Overrides BaseRiskManagement's implementation.
        """
        if self.strategy.portfolio_total_quantity == 0 or self.strategy.portfolio_avg_buy_price == 0:
            return 0.0

        min_profit_take_percent = 0.01  # Ensure a minimum profit target of 1%

        # Dynamic TP factor: increases slightly with each deeper Fibo buy
        # This incentivizes closing out positions that have accumulated at lower levels
        # Accessing strategy.p.tp_percent and strategy.current_fibo_buy_level_idx
        dynamic_tp_factor = (1 + self.strategy.p.tp_percent) + (self.strategy.current_fibo_buy_level_idx * 0.005)

        # Make sure TP factor is at least the minimum profit
        dynamic_tp_factor = max(dynamic_tp_factor, 1 + min_profit_take_percent)

        return self.strategy.portfolio_avg_buy_price * dynamic_tp_factor
