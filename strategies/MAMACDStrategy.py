import backtrader as bt
from strategies.Base import BaseTradingStrategy
from riskmanagers.BaseRiskManagement import BaseRiskManagement


class MAMACDStrategy(BaseTradingStrategy):
    params = (
        ('ma_period', 50),       # Moving Average period
        ('macd1', 12),           # MACD Fast EMA
        ('macd2', 26),           # MACD Slow EMA
        ('macdsig', 9),          # MACD Signal line
        ('log', True),
    )

    def __init__(self):
        super().__init__()  # Initialize BaseTradingStrategy

        # --- Indicators ---
        self.ma = bt.indicators.SimpleMovingAverage(self.dataclose, period=self.p.ma_period)
        self.macd = bt.indicators.MACD(self.dataclose,
                                       period_me1=self.p.macd1,
                                       period_me2=self.p.macd2,
                                       period_signal=self.p.macdsig)
        self.macd_cross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)
        self.risk_manager = BaseRiskManagement(self)

    def _execute_trading_logic(self):
        # --- Buy Logic ---
        if not self.position:
            if self.dataclose[0] > self.ma[0] and self.macd_cross[0] > 0:
                self.log(f'↑ BUY SIGNAL | Price: {self._format_value_for_log_mcap(self.dataclose[0])}, MA: {self._format_value_for_log_mcap(self.ma[0])}, MACD Cross: {self.macd_cross[0]}')
                self.order = self.buy()

        # --- Sell Logic ---
        else:
            if self.dataclose[0] < self.ma[0] or self.macd_cross[0] < 0:
                self.log(f'↓ SELL SIGNAL | Price: {self._format_value_for_log_mcap(self.dataclose[0])}, MA: {self._format_value_for_log_mcap(self.ma[0])}, MACD Cross: {self.macd_cross[0]}')
                self.order = self.sell()
