import backtrader as bt


class TimeDistanceFromMASingle(bt.Indicator):
    """Calculate time distance from a single MA cross"""
    lines = ('time_raw',)
    params = (
        ('ma', None),
        ('period', None),
        ('useZ', False),
    )

    def __init__(self):
        self.ma = self.p.ma
        self.bars_since = 0

        # Detect crosses for optimization
        self.cross_up = bt.indicators.CrossUp(self.data.close, self.ma)
        self.cross_down = bt.indicators.CrossDown(self.data.close, self.ma)

    def next(self):
        close = self.data.close[0]

        # Increment bars since last cross
        self.bars_since += 1

        # Reset on cross
        if self.cross_up[0] or self.cross_down[0]:
            self.bars_since = 0

        # Normalize by MA period
        bars_norm = self.bars_since / self.p.period

        # Apply directional z-score if enabled
        if self.p.useZ:
            z = -1 if self.ma[0] > close else 1
            self.lines.time_raw[0] = bars_norm * z
        else:
            self.lines.time_raw[0] = bars_norm


class TimeDistance(bt.Indicator):
    """Calculate time distance from MA crosses"""
    lines = ('time_norm', 'time_signal')
    params = (
        ('mas', None),  # List of (ma, period) tuples
        ('smooth', 23),
        ('useZ', True),
        ('normalize_len', 200),
        ('signal_len', 15),
    )

    def __init__(self):
        self.mas = self.p.mas

        # Create a TimeDistanceFromMASingle indicator for each MA
        self.time_indicators = []
        for ma, period in self.mas:
            time_ind = TimeDistanceFromMASingle(
                self.data,
                ma=ma,
                period=period,
                useZ=self.p.useZ
            )
            self.time_indicators.append(time_ind)

        # Average all the time distance indicators
        time_sum = self.time_indicators[0].lines.time_raw
        for time_ind in self.time_indicators[1:]:
            time_sum = time_sum + time_ind.lines.time_raw
        time_avg = time_sum / len(self.time_indicators)

        # Smooth with EMA
        time_smooth = bt.indicators.EMA(time_avg, period=self.p.smooth)

        # Normalize using z-score over normalize_len period
        time_mean = bt.indicators.SMA(time_smooth, period=self.p.normalize_len)
        time_std = bt.indicators.StdDev(time_smooth, period=self.p.normalize_len)
        self.lines.time_norm = (time_smooth - time_mean) / time_std

        # Signal line is EMA of normalized values
        self.lines.time_signal = bt.indicators.EMA(self.lines.time_norm, period=self.p.signal_len)
