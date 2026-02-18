import backtrader as bt

from solana_backtrader_extended.strategies.pdma.mas import ZLEMA, SMMA


class ImpulseMACD(bt.Indicator):
    """Impulse MACD Indicator"""
    lines = ('md', 'sb', 'sh')
    params = (
        ('lengthMA', 34),
        ('lengthSignal', 9),
    )

    def __init__(self):
        hlc3 = (self.data.high + self.data.low + self.data.close) / 3

        hi = SMMA(self.data.high, period=self.p.lengthMA)
        lo = SMMA(self.data.low, period=self.p.lengthMA)
        mi = ZLEMA(hlc3, period=self.p.lengthMA)

        # Calculate md based on conditions
        md = bt.If(mi > hi, mi - hi,
                   bt.If(mi < lo, mi - lo, 0))

        self.lines.md = md
        self.lines.sb = bt.indicators.SMA(md, period=self.p.lengthSignal)
        self.lines.sh = md - self.lines.sb
