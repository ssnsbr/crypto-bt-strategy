
from riskmanagers.BaseRiskManagement import BaseRiskManagement
from strategies.Base import BaseTradingStrategy


class FiboR(BaseTradingStrategy):

    def __init__(self):
        super().__init__()  # Call the base class constructor
        # Instantiate the RiskManagement class
        self.risk_manager = BaseRiskManagement(self)
        self.buying = False
        self.tp = 0
        self.current_fibo = 0
        self.current_fibo_index = -1
        self.fibo_buy = 0.22
        # self.fibo_buy = 0.328
        # self.fibo_buy = 0.5
        # self.fibo_buy = 0.618
        # self.fibo_buy = 0.786
        self.Fibonacci_Buy_MCAP = 0
        self.bought_here = False

    def update_ath(self):
        if super().update_ath():
            self.Fibonacci_Buy_MCAP = self.ath * self.fibo_buy
            self.bought_here = False

    def _execute_trading_logic(self):
        if self.ath <= 0.0:
            return
        if self.order:
            return

        tolerance = 0.02  # 2% buffer
        upper_bound = self.Fibonacci_Buy_MCAP * (1 + tolerance)

        if self.current_price <= upper_bound and not self.bought_here:
            self.log(f'↑ BUY SIGNAL | Price: {self._format_value_for_log_mcap(self.current_price)}, at: {self._format_value_for_log_mcap(self.Fibonacci_Buy_MCAP)}, Fibo Level: {self.fibo_buy}')
            self.order = self.buy()
            self.bought_here = True
        # Check upward touch
