
from riskmanagers.BaseRiskManagement import BaseRiskManagement
from strategies.Base import BaseTradingStrategy


class SimpleTest(BaseTradingStrategy):

    def __init__(self):
        super().__init__()  # Call the base class constructor
        # Instantiate the RiskManagement class
        self.risk_manager = BaseRiskManagement(self)
        self.buying = False

    def _execute_trading_logic(self):
        """ 
        A simple strategy that 
        1- buys when the RSI is below a certain threshold and sells when the RSI is above a certain threshold.
        2- Use Moving Average Crossovers to determine when to buy and sell
        """
        if self.order:  # This checks if self.order is not None
            return  # Exit if an order is already active/pending

        if self.buying:
            self.buying = False
            return

        open_position = self.getposition(self.datas[0]).size == 0
        rsi_condition = self.rsi < 40
        mv_crossover = self.dataclose < self.sma30
        green_candle_condition = self.green_candle_streak > 1
        if open_position and rsi_condition and mv_crossover and green_candle_condition:
            self.order = self.buy()
            self.buying = True
