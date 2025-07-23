import abc


class AbstractRiskManagement(abc.ABC):
    """
    Abstract Base Class for all trading strategy risk management components.
    Defines the common interface for checking and executing stop loss and take profit.
    """

    def __init__(self, strategy):
        # A reference to the main strategy instance, allowing access to its data, position, and logging.
        self.strategy = strategy

    # ---- TP ----
    @abc.abstractmethod
    def check_and_execute_take_profit(self, current_price: float) -> bool:
        """
        Checks if the take-profit condition is met and executes a sell order if it is.
        Returns True if a TP order was placed, False otherwise.
        """
        pass

    @abc.abstractmethod
    def check_and_execute_trailing_take_profit(self, current_price: float) -> bool:
        """
        Checks if the trailing take-profit condition is met and executes a sell order if it is.
        Returns True if a TTP order was placed, False otherwise.
        """
        pass

    @abc.abstractmethod
    def check_and_execute_dynamic_take_profit(self, current_price: float) -> bool:
        """
        Checks if the dynamic take-profit condition is met and executes a sell order if it is.
        Returns True if a DTP order was placed, False otherwise.
        """
        pass

    # ---- SL ----
    @abc.abstractmethod
    def check_and_execute_stop_loss(self, current_price: float) -> bool:
        """
        Checks if the stop-loss condition is met and executes a sell order if it is.
        This is typically the highest priority exit rule.
        Returns True if a SL order was placed, False otherwise.
        """
        pass

    @abc.abstractmethod
    def check_and_execute_emergency_exit(self, current_price: float) -> bool:
        """
        Checks if the 'emergency' condition is met and executes a sell order if it is.
        This is for exiting positions in assets that have fallen below a critical threshold.
        Returns True if a emergency exit order was placed, False otherwise.
        """
        pass

    @abc.abstractmethod
    def check_and_execute_trailing_stop_loss(self, current_price: float) -> bool:
        """
        Checks if the trailing stop-loss condition is met and executes a sell order if it is.
        Returns True if a TSL order was placed, False otherwise.
        """
        pass
