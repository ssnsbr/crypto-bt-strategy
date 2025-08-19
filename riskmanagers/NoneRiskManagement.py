

from riskmanagers.ABCRiskManagement import AbstractRiskManagement


class NoneRiskManagement(AbstractRiskManagement):

    def __init__(self, strategy):
        super().__init__(strategy)

    def _calculate_trailing_stop_loss_price(self) -> float:
        return False

    def _calculate_take_profit_price(self) -> float:
        return False

    def _calculate_stop_loss_price(self) -> float:
        return False

    def check_and_execute_take_profit(self, current_price: float) -> bool:
        return False

    def check_and_execute_stop_loss(self, current_price: float) -> bool:
        return False

    def check_and_execute_emergency_exit(self, current_price: float) -> bool:
        return False

    def check_and_execute_dynamic_take_profit(self, current_price: float) -> bool:
        return False

    def check_and_execute_trailing_stop_loss(self, current_price: float) -> bool:
        return False

    def check_and_execute_trailing_take_profit(self, current_price: float) -> bool:
        return False
