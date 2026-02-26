import backtrader as bt

from backtrader_extended.indicators.moving_averages import DEMA, SMMA, ZLEMA, TEMA, HullMA


class VolumeDistanceSingle(bt.Indicator):
    """Calculate volume distance for a single MA period"""
    lines = ('vol_weighted',)
    params = (
        ('price_ma', None),
        ('vol_ma', None),
        ('useZ', True),
    )

    def __init__(self):
        self.price_ma = self.p.price_ma
        self.vol_ma = self.p.vol_ma

        if self.p.useZ:
            # Z value (position relative to MA): -1 if MA > close, else 1
            # z = bt.If(self.price_ma > self.data.close, -1, 1)
            z = 1 if self.price_ma > self.data.close else -1
            self.lines.vol_weighted = self.vol_ma * z
        else:
            self.lines.vol_weighted = self.vol_ma


class VolumeDistance(bt.Indicator):
    """Calculate volume distance across multiple MA periods"""
    lines = ('vol_norm', 'vol_signal')
    params = (
        ('ma_types', ['ema', 'ema', 'ema', 'ema', 'ema']),
        ('ma_periods', [50, 100, 150, 200, 250]),
        ('src', 'hlc3'),
        ('smooth', 23),
        ('useZ', True),
        ('normalize_len', 200),
        ('signal_len', 15),
    )

    def __init__(self):
        # Determine source price
        src = self._get_source()

        # Create price MAs and volume MAs, then volume distance indicators
        self.vol_indicators = []
        for ma_type, period in zip(self.p.ma_types, self.p.ma_periods):
            # Create price MA for z calculation
            price_ma = self._create_ma(src, ma_type, period)

            # Create volume MA (always use EMA for volume)
            vol_ma = bt.indicators.EMA(self.data.volume, period=period)

            # Create volume distance indicator
            vol_ind = VolumeDistanceSingle(
                self.data,
                price_ma=price_ma,
                vol_ma=vol_ma,
                useZ=self.p.useZ
            )
            self.vol_indicators.append(vol_ind)

        # Average all volume indicators
        vol_sum = self.vol_indicators[0].lines.vol_weighted
        for vol_ind in self.vol_indicators[1:]:
            vol_sum = vol_sum + vol_ind.lines.vol_weighted
        vol_avg = vol_sum / len(self.vol_indicators)

        # Smooth with EMA
        vol_smooth = bt.indicators.EMA(vol_avg, period=self.p.smooth)

        # Normalize using z-score over normalize_len period
        vol_mean = bt.indicators.SMA(vol_smooth, period=self.p.normalize_len)
        vol_std = bt.indicators.StdDev(vol_smooth, period=self.p.normalize_len)
        self.lines.vol_norm = (vol_smooth - vol_mean) / vol_std

        # Signal line is EMA of normalized values
        self.lines.vol_signal = bt.indicators.EMA(self.lines.vol_norm, period=self.p.signal_len)

    def _get_source(self):
        """Get the price source based on parameter"""
        if self.p.src == 'hlc3':
            return (self.data.high + self.data.low + self.data.close) / 3
        elif self.p.src == 'ohlc4':
            return (self.data.open + self.data.high + self.data.low + self.data.close) / 4
        elif self.p.src == 'hl2':
            return (self.data.high + self.data.low) / 2
        else:  # 'close' or default
            return self.data.close

    def _create_ma(self, src, ma_type, period):
        """Create a moving average of the specified type"""
        ma_type = ma_type.lower()

        if ma_type == 'sma':
            return bt.indicators.SMA(src, period=period)
        elif ma_type == 'ema':
            return bt.indicators.EMA(src, period=period)
        elif ma_type == 'wma':
            return bt.indicators.WMA(src, period=period)
        elif ma_type == 'dema':
            return DEMA(src, period=period) 
        elif ma_type == 'tema':
            return TEMA(src, period=period)
        elif ma_type == 'hull':
            return HullMA(src, period=period)
        elif ma_type == 'zlema':
            return ZLEMA(src, period=period)
        elif ma_type == 'smma':
            return SMMA(src, period=period)
        else:
            return bt.indicators.EMA(src, period=period)
