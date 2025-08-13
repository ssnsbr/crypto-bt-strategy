import backtrader as bt


class SafeRSI(bt.indicators.RSI):
    def next(self):
        try:
            super().next()
        except ZeroDivisionError:
            self.lines.rsi[0] = 50.0  # Neutral value
