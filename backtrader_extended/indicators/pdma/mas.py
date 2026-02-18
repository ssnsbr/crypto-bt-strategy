import backtrader as bt
import numpy as np


class SMMA(bt.Indicator):
    """Smoothed Moving Average"""
    lines = ('smma',)
    params = (('period', 30),)

    def __init__(self):
        self.addminperiod(self.p.period)

    def next(self):
        if len(self) == self.p.period:
            self.lines.smma[0] = sum(self.data.get(size=self.p.period)) / self.p.period
        else:
            self.lines.smma[0] = (self.lines.smma[-1] * (self.p.period - 1) + self.data[0]) / self.p.period


class ZLEMA(bt.Indicator):
    """Zero Lag EMA"""
    lines = ('zlema',)
    params = (('period', 30),)

    def __init__(self):
        ema1 = bt.indicators.EMA(self.data, period=self.p.period)
        ema2 = bt.indicators.EMA(ema1, period=self.p.period)
        self.lines.zlema = ema1 + (ema1 - ema2)


class DEMA(bt.Indicator):
    """Double Exponential Moving Average"""
    lines = ('dema',)
    params = (('period', 30),)

    def __init__(self):
        ema1 = bt.indicators.EMA(self.data, period=self.p.period)
        ema2 = bt.indicators.EMA(ema1, period=self.p.period)
        self.lines.dema = 2 * ema1 - ema2


class TEMA(bt.Indicator):
    """Triple Exponential Moving Average"""
    lines = ('tema',)
    params = (('period', 30),)

    def __init__(self):
        ema1 = bt.indicators.EMA(self.data, period=self.p.period)
        ema2 = bt.indicators.EMA(ema1, period=self.p.period)
        ema3 = bt.indicators.EMA(ema2, period=self.p.period)
        self.lines.tema = 3 * ema1 - 3 * ema2 + ema3


class HullMA(bt.Indicator):
    """Hull Moving Average"""
    lines = ('hma',)
    params = (('period', 30),)

    def __init__(self):
        wma_half = bt.indicators.WMA(self.data, period=int(self.p.period / 2))
        wma_full = bt.indicators.WMA(self.data, period=self.p.period)
        diff = 2 * wma_half - wma_full
        self.lines.hma = bt.indicators.WMA(diff, period=int(np.sqrt(self.p.period)))
