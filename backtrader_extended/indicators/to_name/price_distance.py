import backtrader as bt


class PriceDistanceFromMASingle(bt.Indicator):
    """Calculate current price distance from a single MA"""
    lines = ('pd_raw',)
    params = (
        ('ma', None),
        ('useZ', False),
    )

    def __init__(self):
        self.ma = self.p.ma

        # Calculate price distance as percentage
        pd = (self.data.close - self.ma) / self.ma * 100

        if self.p.useZ:
            # Z value (position relative to MA): -1 if MA > close, else 1
            z = bt.If(self.ma > self.data.close, -1, 1)
            self.lines.pd_raw = pd * z
        else:
            self.lines.pd_raw = pd


class PriceDistanceFromMA(bt.Indicator):
    """Calculate current price distance from multiple MAs"""
    lines = ('pd_norm', 'pd_signal')
    params = (
        ('mas', None),
        ('smooth', 23),
        ('useZ', False),
        ('normalize_len', 200),
        ('signal_len', 15),
    )

    def __init__(self):
        self.mas = self.p.mas

        # Create a PriceDistanceFromMASingle indicator for each MA
        self.pd_indicators = []
        for ma in self.mas:
            pd_ind = PriceDistanceFromMASingle(
                self.data,
                ma=ma,
                useZ=self.p.useZ
            )
            self.pd_indicators.append(pd_ind)

        # Average all the price distance indicators
        # Sum all pd_raw lines and divide by count
        pd_sum = self.pd_indicators[0].lines.pd_raw
        for pd_ind in self.pd_indicators[1:]:
            pd_sum = pd_sum + pd_ind.lines.pd_raw
        pd_avg = pd_sum / len(self.pd_indicators)

        # Smooth with EMA
        pd_smooth = bt.indicators.EMA(pd_avg, period=self.p.smooth)

        # Normalize using z-score over normalize_len period
        pd_mean = bt.indicators.SMA(pd_smooth, period=self.p.normalize_len)
        pd_std = bt.indicators.StdDev(pd_smooth, period=self.p.normalize_len)
        self.lines.pd_norm = (pd_smooth - pd_mean) / pd_std

        # Signal line is EMA of normalized values
        self.lines.pd_signal = bt.indicators.EMA(self.lines.pd_norm, period=self.p.signal_len)
