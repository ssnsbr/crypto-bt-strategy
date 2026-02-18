import backtrader as bt


class PriceDistanceFromTouchSingle(bt.Indicator):
    """Calculate price distance from last MA touch point"""
    lines = ('pd_touch_raw',)
    params = (
        ('ma', None),
        ('useZ', False),
    )

    def __init__(self):
        self.ma = self.p.ma
        self.touch_price = None

        # Detect crosses for optimization
        self.cross_up = bt.indicators.CrossUp(self.data.close, self.ma)
        self.cross_down = bt.indicators.CrossDown(self.data.close, self.ma)

    def next(self):
        close = self.data.close[0]

        # Update touch price on cross
        if self.cross_up[0] or self.cross_down[0]:
            self.touch_price = close

        # Calculate price distance from last touch
        if self.touch_price is not None:
            pd_touch = (close - self.touch_price) / self.touch_price * 100

            # Apply directional z-score if enabled
            if self.p.useZ:
                z = -1 if self.ma[0] > close else 1
                self.lines.pd_touch_raw[0] = pd_touch * z
            else:
                self.lines.pd_touch_raw[0] = pd_touch
        else:
            # No touch yet
            self.lines.pd_touch_raw[0] = 0


class PriceDistanceFromTouch(bt.Indicator):
    """Calculate price distance from last MA touch points"""
    lines = ('pd_touch_norm', 'pd_touch_signal')
    params = (
        ('mas', None),
        ('smooth', 23),
        ('useZ', False),
        ('normalize_len', 200),
        ('signal_len', 15),
    )

    def __init__(self):
        self.mas = self.p.mas

        # Create a PriceDistanceFromTouchSingle indicator for each MA
        self.touch_indicators = []
        for ma in self.mas:
            touch_ind = PriceDistanceFromTouchSingle(
                self.data,
                ma=ma,
                useZ=self.p.useZ
            )
            self.touch_indicators.append(touch_ind)

        # Average all the touch distance indicators
        touch_sum = self.touch_indicators[0].lines.pd_touch_raw
        for touch_ind in self.touch_indicators[1:]:
            touch_sum = touch_sum + touch_ind.lines.pd_touch_raw
        touch_avg = touch_sum / len(self.touch_indicators)

        # Smooth with EMA
        touch_smooth = bt.indicators.EMA(touch_avg, period=self.p.smooth)

        # Normalize using z-score over normalize_len period
        touch_mean = bt.indicators.SMA(touch_smooth, period=self.p.normalize_len)
        touch_std = bt.indicators.StdDev(touch_smooth, period=self.p.normalize_len)
        self.lines.pd_touch_norm = (touch_smooth - touch_mean) / touch_std

        # Signal line is EMA of normalized values
        self.lines.pd_touch_signal = bt.indicators.EMA(self.lines.pd_touch_norm, period=self.p.signal_len)
