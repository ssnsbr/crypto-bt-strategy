import backtrader as bt
from backtrader_extended.strategies.Base import BaseTradingStrategy
from riskmanagers.noneRiskManagement import NoneRiskManagement


class SOL_EMA_MACD_Strategy(BaseTradingStrategy):
    """
    Solana Long/Short Strategy using EMA trend + MACD signal.
    - Long only if price > EMA and MACD crosses above signal (hist < 0)
    - Short only if price < EMA and MACD crosses below signal (hist > 0)
    """

    params = (
        ('ema_period', 50),          # EMA period to define trend
        ('macd_me1', 12),            # MACD fast EMA
        ('macd_me2', 26),            # MACD slow EMA
        ('macd_signal', 9),          # MACD signal line
        ('tp_percent', 0.05),        # Take profit (5%)
        ('sl_percent', 0.02),        # Stop loss (2%)
        ('log', True),
    )

    def __init__(self):
        super().__init__()

        # Indicators
        self.ema = bt.indicators.EMA(self.datas[0].close, period=self.p.ema_period)
        self.macd = bt.indicators.MACD(
            self.datas[0].close,
            period_me1=self.p.macd_me1,
            period_me2=self.p.macd_me2,
            period_signal=self.p.macd_signal
        )
        self.macd_cross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

        # Risk management
        self.risk_manager = NoneRiskManagement(self)
        self.order = None

    def _execute_trading_logic(self):
        in_position = self.getposition(self.datas[0]).size != 0

        # Skip if an order is pending
        if self.order:
            return

        # Trend check
        price = self.dataclose[0]
        ema = self.ema[0]
        macd_hist = self.macd.macdhist[0]

        # --- LONG ---
        if price > ema and self.macd_cross[0] == 1 and macd_hist < 0:
            if in_position and self.getposition().size < 0:
                # Close short before going long
                self.close()
            if not in_position or self.getposition().size <= 0:
                self.order = self.buy()
                self.log(f"LONG ENTRY at {price:.2f}")

        # --- SHORT ENTRY ---
        elif price < ema and self.macd_cross[0] == -1 and macd_hist > 0:
            if in_position and self.getposition().size > 0:
                # Close long before going short
                self.close()
            if not in_position or self.getposition().size >= 0:
                self.order = self.sell()
                self.log(f"SHORT ENTRY at {price:.2f}")

        # --- Optional TP / SL handled by risk manager ---
        self._execute_risk_management()

    def stop(self):
        """Close all positions at end of backtest."""
        in_position = self.getposition(self.datas[0]).size
        if in_position != 0:
            self.log(f"END OF BACKTEST: Closing position of size {in_position} at price {self.dataclose[0]:.2f}")
            self.close()
        super().stop()
