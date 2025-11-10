import backtrader as bt


class TEMA(bt.Indicator):
    lines = ('tema',)
    params = (('period', 20),)

    def __init__(self):
        ema1 = bt.indicators.EMA(self.data, period=self.p.period)
        ema2 = bt.indicators.EMA(ema1, period=self.p.period)
        ema3 = bt.indicators.EMA(ema2, period=self.p.period)
        self.lines.tema = 3 * (ema1 - ema2) + ema3
