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


class PriceDistanceFromTouch(bt.Indicator):
    """Calculate price distance from last MA touch points"""
    lines = ('pd_touch_norm', 'pd_touch_signal')
    params = (
        ('ma_types', ['ema', 'ema', 'ema', 'ema', 'ema']),  # MA type for each period
        ('ma_periods', [50, 100, 150, 200, 250]),  # Dynamic MA periods
        ('src', 'hlc3'),  # Source: hlc3, close, ohlc4, hl2
        ('smooth', 23),
        ('useZ', False),  # Use directional z-scores
        ('normalize_len', 200),
        ('signal_len', 15),
    )

    def __init__(self):
        # Get source data
        src = self._get_source(self.p.src)

        # Create MAs dynamically based on types and periods
        self.mas = []
        for ma_type, period in zip(self.p.ma_types, self.p.ma_periods):
            ma = self._create_ma(src, ma_type, period)
            self.mas.append(ma)

        # Touch prices storage for each MA
        self.touch_prices = [None] * len(self.mas)

    def _get_source(self, src_type):
        """Get source data based on type"""
        if src_type == 'hlc3':
            return (self.data.high + self.data.low + self.data.close) / 3
        elif src_type == 'close':
            return self.data.close
        elif src_type == 'ohlc4':
            return (self.data.open + self.data.high + self.data.low + self.data.close) / 4
        elif src_type == 'hl2':
            return (self.data.high + self.data.low) / 2
        elif src_type == 'hlcc4':
            return (self.data.high + self.data.low + self.data.close + self.data.close) / 4
        elif src_type == 'open':
            return self.data.open
        elif src_type == 'high':
            return self.data.high
        elif src_type == 'low':
            return self.data.low
        else:
            return self.data.close

    def _create_ma(self, src, ma_type, period):
        """Create MA based on type"""
        ma_type = ma_type.lower()

        if ma_type == 'ema':
            return bt.indicators.EMA(src, period=period)
        elif ma_type == 'sma':
            return bt.indicators.SMA(src, period=period)
        elif ma_type == 'wma':
            return bt.indicators.WMA(src, period=period)
        elif ma_type == 'dema':
            return DEMA(src, period=period)
        elif ma_type == 'tema':
            return TEMA(src, period=period)
        elif ma_type == 'zlema':
            return ZLEMA(src, period=period)
        elif ma_type == 'hma':
            return HullMA(src, period=period)
        elif ma_type == 'smma':
            return SMMA(src, period=period)
        else:
            return bt.indicators.EMA(src, period=period)

    def next(self):
        close = self.data.close[0]

        # Update touch prices on cross for each MA
        if len(self) > 1:
            for i, ma in enumerate(self.mas):
                if (close > ma[0] and self.data.close[-1] <= ma[-1]) or \
                   (close < ma[0] and self.data.close[-1] >= ma[-1]):
                    self.touch_prices[i] = close

        # Calculate price distance from last touch for each MA
        pd_touches = []
        z_values = []

        for i, ma in enumerate(self.mas):
            if self.touch_prices[i] is not None:
                pd_touch = (close - self.touch_prices[i]) / self.touch_prices[i] * 100
                pd_touches.append(pd_touch)

                # Z value (position relative to MA)
                z = -1 if ma[0] > close else 1
                z_values.append(z)
            else:
                pd_touches.append(0)
                z_values.append(1)

        # Average price distance from touch
        if self.p.useZ:
            use_a = sum(pd * z for pd, z in zip(pd_touches, z_values)) / len(pd_touches)
        else:
            use_a = sum(pd_touches) / len(pd_touches)

        # Store for EMA calculation
        if not hasattr(self, 'touch_values'):
            self.touch_values = []
        self.touch_values.append(use_a)

        # Smooth
        ma_pd_touch_smooth = self._calculate_ema(self.touch_values, self.p.smooth)

        # Normalize
        if len(self.touch_values) >= self.p.normalize_len:
            mean = np.mean(self.touch_values[-self.p.normalize_len:])
            std = np.std(self.touch_values[-self.p.normalize_len:])
            self.lines.pd_touch_norm[0] = (ma_pd_touch_smooth - mean) / std if std != 0 else 0
        else:
            self.lines.pd_touch_norm[0] = 0

        # Calculate signal
        if not hasattr(self, 'touch_norm_values'):
            self.touch_norm_values = []
        self.touch_norm_values.append(self.lines.pd_touch_norm[0])
        self.lines.pd_touch_signal[0] = self._calculate_ema(self.touch_norm_values, self.p.signal_len)

    def _calculate_ema(self, values, period):
        if len(values) == 0:
            return 0
        if len(values) < period:
            return np.mean(values)

        multiplier = 2 / (period + 1)
        ema = np.mean(values[:period])
        for val in values[period:]:
            ema = (val * multiplier) + (ema * (1 - multiplier))
        return ema


class TimeDistance(bt.Indicator):
    """Calculate time distance from MA crosses"""
    lines = ('time_norm', 'time_signal')
    params = (
        ('ma_types', ['ema', 'ema', 'ema', 'ema', 'ema']),  # MA type for each period
        ('ma_periods', [50, 100, 150, 200, 250]),  # Dynamic MA periods
        ('src', 'hlc3'),  # Source: hlc3, close, ohlc4, hl2
        ('smooth', 23),
        ('useZ', True),  # Use directional z-scores
        ('normalize_len', 200),
        ('signal_len', 15),
    )

    def __init__(self):
        # Get source data
        src = self._get_source(self.p.src)

        # Create MAs dynamically based on types and periods
        self.mas = []
        for ma_type, period in zip(self.p.ma_types, self.p.ma_periods):
            ma = self._create_ma(src, ma_type, period)
            self.mas.append((ma, period))

        # Bars since last cross for each MA
        self.bars_since = [0] * len(self.mas)

    def _get_source(self, src_type):
        """Get source data based on type"""
        if src_type == 'hlc3':
            return (self.data.high + self.data.low + self.data.close) / 3
        elif src_type == 'close':
            return self.data.close
        elif src_type == 'ohlc4':
            return (self.data.open + self.data.high + self.data.low + self.data.close) / 4
        elif src_type == 'hl2':
            return (self.data.high + self.data.low) / 2
        elif src_type == 'hlcc4':
            return (self.data.high + self.data.low + self.data.close + self.data.close) / 4
        elif src_type == 'open':
            return self.data.open
        elif src_type == 'high':
            return self.data.high
        elif src_type == 'low':
            return self.data.low
        else:
            return self.data.close

    def _create_ma(self, src, ma_type, period):
        """Create MA based on type"""
        ma_type = ma_type.lower()

        if ma_type == 'ema':
            return bt.indicators.EMA(src, period=period)
        elif ma_type == 'sma':
            return bt.indicators.SMA(src, period=period)
        elif ma_type == 'wma':
            return bt.indicators.WMA(src, period=period)
        elif ma_type == 'dema':
            return DEMA(src, period=period)
        elif ma_type == 'tema':
            return TEMA(src, period=period)
        elif ma_type == 'zlema':
            return ZLEMA(src, period=period)
        elif ma_type == 'hma':
            return HullMA(src, period=period)
        elif ma_type == 'smma':
            return SMMA(src, period=period)
        else:
            return bt.indicators.EMA(src, period=period)

    def next(self):
        close = self.data.close[0]

        # Increment and reset bars for each MA
        for i, (ma, period) in enumerate(self.mas):
            self.bars_since[i] += 1

            # Reset on cross
            if len(self) > 1:
                if (close > ma[0] and self.data.close[-1] <= ma[-1]) or \
                   (close < ma[0] and self.data.close[-1] >= ma[-1]):
                    self.bars_since[i] = 0

        # Normalize by MA length and calculate average
        bars_normalized = []
        z_values = []

        for i, (ma, period) in enumerate(self.mas):
            bars_norm = self.bars_since[i] / period
            bars_normalized.append(bars_norm)

            # Z value
            z = -1 if ma[0] > close else 1
            z_values.append(z)

        # Average time distance
        if self.p.useZ:
            use_b = sum(b * z for b, z in zip(bars_normalized, z_values)) / len(bars_normalized)
        else:
            use_b = sum(bars_normalized) / len(bars_normalized)

        # Store for EMA calculation
        if not hasattr(self, 'time_values'):
            self.time_values = []
        self.time_values.append(use_b)

        # Smooth
        ma_b_smooth = self._calculate_ema(self.time_values, self.p.smooth)

        # Normalize
        if len(self.time_values) >= self.p.normalize_len:
            mean = np.mean(self.time_values[-self.p.normalize_len:])
            std = np.std(self.time_values[-self.p.normalize_len:])
            self.lines.time_norm[0] = (ma_b_smooth - mean) / std if std != 0 else 0
        else:
            self.lines.time_norm[0] = 0

        # Calculate signal
        if not hasattr(self, 'time_norm_values'):
            self.time_norm_values = []
        self.time_norm_values.append(self.lines.time_norm[0])
        self.lines.time_signal[0] = self._calculate_ema(self.time_norm_values, self.p.signal_len)

    def _calculate_ema(self, values, period):
        if len(values) == 0:
            return 0
        if len(values) < period:
            return np.mean(values)

        multiplier = 2 / (period + 1)
        ema = np.mean(values[:period])
        for val in values[period:]:
            ema = (val * multiplier) + (ema * (1 - multiplier))
        return ema


class VolumeDistance(bt.Indicator):
    """Calculate volume distance"""
    lines = ('vol_norm', 'vol_signal')
    params = (
        ('ma_types', ['ema', 'ema', 'ema', 'ema', 'ema']),  # MA type for each period
        ('ma_periods', [50, 100, 150, 200, 250]),  # Dynamic MA periods
        ('src', 'hlc3'),  # Source for price MAs: hlc3, close, ohlc4, hl2
        ('smooth', 23),
        ('useZ', True),  # Use directional z-scores
        ('normalize_len', 200),
        ('signal_len', 15),
    )

    def __init__(self):
        # Get source data for price MAs
        src = self._get_source(self.p.src)

        # Create price MAs for z calculation
        self.price_mas = []
        for ma_type, period in zip(self.p.ma_types, self.p.ma_periods):
            ma = self._create_ma(src, ma_type, period)
            self.price_mas.append(ma)

        # Create volume MAs (always use EMA for volume)
        self.vol_mas = []
        for period in self.p.ma_periods:
            vol_ma = bt.indicators.EMA(self.data.volume, period=period)
            self.vol_mas.append(vol_ma)

    def _get_source(self, src_type):
        """Get source data based on type"""
        if src_type == 'hlc3':
            return (self.data.high + self.data.low + self.data.close) / 3
        elif src_type == 'close':
            return self.data.close
        elif src_type == 'ohlc4':
            return (self.data.open + self.data.high + self.data.low + self.data.close) / 4
        elif src_type == 'hl2':
            return (self.data.high + self.data.low) / 2
        elif src_type == 'hlcc4':
            return (self.data.high + self.data.low + self.data.close + self.data.close) / 4
        elif src_type == 'open':
            return self.data.open
        elif src_type == 'high':
            return self.data.high
        elif src_type == 'low':
            return self.data.low
        else:
            return self.data.close

    def _create_ma(self, src, ma_type, period):
        """Create MA based on type"""
        ma_type = ma_type.lower()

        if ma_type == 'ema':
            return bt.indicators.EMA(src, period=period)
        elif ma_type == 'sma':
            return bt.indicators.SMA(src, period=period)
        elif ma_type == 'wma':
            return bt.indicators.WMA(src, period=period)
        elif ma_type == 'dema':
            return DEMA(src, period=period)
        elif ma_type == 'tema':
            return TEMA(src, period=period)
        elif ma_type == 'zlema':
            return ZLEMA(src, period=period)
        elif ma_type == 'hma':
            return HullMA(src, period=period)
        elif ma_type == 'smma':
            return SMMA(src, period=period)
        else:
            return bt.indicators.EMA(src, period=period)

    def next(self):
        close = self.data.close[0]

        # Calculate z values from price position
        z_values = []
        for price_ma in self.price_mas:
            z = -1 if price_ma[0] > close else 1
            z_values.append(z)

        # Average volume
        if self.p.useZ:
            use_v = sum(vol[0] * z for vol, z in zip(self.vol_mas, z_values)) / len(self.vol_mas)
        else:
            use_v = sum(vol[0] for vol in self.vol_mas) / len(self.vol_mas)

        # Store for EMA calculation
        if not hasattr(self, 'vol_values'):
            self.vol_values = []
        self.vol_values.append(use_v)

        # Smooth
        vol_sum_smooth = self._calculate_ema(self.vol_values, self.p.smooth)

        # Normalize
        if len(self.vol_values) >= self.p.normalize_len:
            mean = np.mean(self.vol_values[-self.p.normalize_len:])
            std = np.std(self.vol_values[-self.p.normalize_len:])
            self.lines.vol_norm[0] = (vol_sum_smooth - mean) / std if std != 0 else 0
        else:
            self.lines.vol_norm[0] = 0

        # Calculate signal
        if not hasattr(self, 'vol_norm_values'):
            self.vol_norm_values = []
        self.vol_norm_values.append(self.lines.vol_norm[0])
        self.lines.vol_signal[0] = self._calculate_ema(self.vol_norm_values, self.p.signal_len)

    def _calculate_ema(self, values, period):
        if len(values) == 0:
            return 0
        if len(values) < period:
            return np.mean(values)

        multiplier = 2 / (period + 1)
        ema = np.mean(values[:period])
        for val in values[period:]:
            ema = (val * multiplier) + (ema * (1 - multiplier))
        return ema
