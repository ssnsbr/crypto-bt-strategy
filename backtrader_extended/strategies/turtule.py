import backtrader as bt


class TurtleTradingStrategy(bt.Strategy):
    """
    Turtle Trading Strategy
    - Breakout entries (20-day for short-term, 55-day for long-term)
    - ATR-based stop-loss
    - Position sizing based on ATR
    """

    params = dict(
        breakout_short=5,       # Short-term breakout
        breakout_long=10,        # Long-term breakout
        atr_period=20,           # ATR for stop-loss and risk sizing
        risk_per_trade=0.02,     # Fraction of equity risked per trade
        units=4,                 # Max units pyramiding
        log=True,
    )

    def __init__(self):
        super().__init__()

        # === Indicators ===
        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period)
        self.highest_short = bt.indicators.Highest(self.data.high, period=self.p.breakout_short)
        self.lowest_short = bt.indicators.Lowest(self.data.low, period=self.p.breakout_short)
        self.highest_long = bt.indicators.Highest(self.data.high, period=self.p.breakout_long)
        self.lowest_long = bt.indicators.Lowest(self.data.low, period=self.p.breakout_long)

        # State
        self.unit_count = 0
        self.entry_price = 0
        self.stop_price = 0
        self.order = None
        self.risk_manager = NoneRiskManagement(self)

    def _calc_size(self):
        """Calculate position size based on ATR and risk per trade"""
        cash = self.broker.get_cash()
        atr_value = self.atr[0]
        risk_amount = cash * self.p.risk_per_trade
        if atr_value == 0:
            return 0
        size = risk_amount / atr_value

        return size

    def _execute_trading_logic(self):
        price = self.data.close[0]

        # If we have an active order, do nothing
        if self.order:
            return

        pos = self.getposition()

        # === ENTRY RULES ===
        if not pos:
            # Long breakout
            if price > self.highest_short[-1]:  # breakout of prior short-term high
                size = max(1, int(self._calc_size()))  # minimum 1 unit

                if size > 0:
                    self.entry_price = price
                    self.stop_price = price - self.atr[0] * 2
                    self.order = self.buy(size=size)
                    self.unit_count = 1
                    self.log(f"BUY breakout {price:.2f}, stop {self.stop_price:.2f}")

            # Short breakout
            elif price < self.lowest_short[-1]:
                size = max(1, int(self._calc_size()))  # minimum 1 unit
                if size > 0:
                    self.entry_price = price
                    self.stop_price = price + self.atr[0] * 2
                    self.order = self.sell(size=size)
                    self.unit_count = 1
                    self.log(f"SELL breakout {price:.2f}, stop {self.stop_price:.2f}")

        # === POSITION MANAGEMENT / PYRAMIDING ===
        else:
            # Long position
            if pos.size > 0:
                # Add units if breakout occurs
                if (self.unit_count < self.p.units and
                        price > self.entry_price + self.atr[0] * self.unit_count):
                    size = self._calc_size()
                    if size > 0:
                        self.buy(size=size)
                        self.unit_count += 1
                        self.log(f"Add LONG unit {self.unit_count} @ {price:.2f}")

                # Stop-loss
                if price < self.stop_price:
                    self.close()
                    self.unit_count = 0
                    self.log(f"LONG Stop hit @ {price:.2f}")

            # Short position
            elif pos.size < 0:
                # Add units if breakout occurs
                if (self.unit_count < self.p.units and
                        price < self.entry_price - self.atr[0] * self.unit_count):
                    size = self._calc_size()
                    if size > 0:
                        self.sell(size=size)
                        self.unit_count += 1
                        self.log(f"Add SHORT unit {self.unit_count} @ {price:.2f}")

                # Stop-loss
                if price > self.stop_price:
                    self.close()
                    self.unit_count = 0
                    self.log(f"SHORT Stop hit @ {price:.2f}")
