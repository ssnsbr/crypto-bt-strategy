import backtrader as bt

from solana_backtrader_extended.strategies.pdma.impulse_macd import ImpulseMACD

from solana_backtrader_extended.strategies.pdma.price_distance import PriceDistanceFromMA
from solana_backtrader_extended.strategies.pdma.price_touch_distance import PriceDistanceFromTouch
from solana_backtrader_extended.strategies.pdma.time_distance import TimeDistance
from solana_backtrader_extended.strategies.pdma.volume_distance import VolumeDistance


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


class PDMAStrategy(bt.Strategy):
    """PDMA / ma_b Strategy: Price from Last Touch"""
    params = (
        ('ma_types', ['ema', 'ema', 'ema', 'ema', 'ema']),  # MA types
        ('ma_periods', [50, 100, 150, 200, 250]),  # MA periods
        ('src', 'hlc3'),  # Source data
        ('smooth', 23),
        ('tpPerc', 1.0),
        ('slPerc', 1.0),
        ('useZvolume', True),
        ('useZtime', True),
        ('useZprice', False),
        ('useZtouch', False),
        ('lengthMA', 34),
        ('lengthSignal', 9),
        ('normalize_len', 200),
        ('signal_len', 15),
    )

    def __init__(self):
        # Impulse MACD
        self.impulse = ImpulseMACD(
            self.data,
            lengthMA=self.p.lengthMA,
            lengthSignal=self.p.lengthSignal
        )

        # Price Distance from Touch
        self.price_touch = PriceDistanceFromTouch(
            self.data,
            ma_types=self.p.ma_types,
            ma_periods=self.p.ma_periods,
            src=self.p.src,
            smooth=self.p.smooth,
            useZ=self.p.useZtouch,
            normalize_len=self.p.normalize_len,
            signal_len=self.p.signal_len
        )

        # Price Distance from MA
        self.price_dist = PriceDistanceFromMA(
            self.data,
            ma_types=self.p.ma_types,
            ma_periods=self.p.ma_periods,
            src=self.p.src,
            smooth=self.p.smooth,
            useZ=self.p.useZprice,
            normalize_len=self.p.normalize_len,
            signal_len=self.p.signal_len
        )

        # Time Distance
        self.time_dist = TimeDistance(
            self.data,
            ma_types=self.p.ma_types,
            ma_periods=self.p.ma_periods,
            src=self.p.src,
            smooth=self.p.smooth,
            useZ=self.p.useZtime,
            normalize_len=self.p.normalize_len,
            signal_len=self.p.signal_len
        )

        # Volume Distance
        self.vol_dist = VolumeDistance(
            self.data,
            ma_types=self.p.ma_types,
            ma_periods=self.p.ma_periods,
            src=self.p.src,
            smooth=self.p.smooth,
            useZ=self.p.useZvolume,
            normalize_len=self.p.normalize_len,
            signal_len=self.p.signal_len
        )

    def next(self):
        # Get indicator values
        pd_touch_norm = self.price_touch.pd_touch_norm[0]
        pd_touch_signal = self.price_touch.pd_touch_signal[0]
        pd_norm = self.price_dist.pd_norm[0]
        pd_signal = self.price_dist.pd_signal[0]
        time_norm = self.time_dist.time_norm[0]
        time_signal = self.time_dist.time_signal[0]
        sh = self.impulse.sh[0]

        # Slope conditions
        slope_ma_pd_touch_up = pd_touch_norm > pd_touch_signal
        slope_ma_pd_up = pd_norm > pd_signal
        slope_ma_b_up = time_norm > time_signal

        # slope_ma_b_down = time_norm < time_signal
        slope_ma_pd_down = pd_norm < pd_signal
        slope_ma_pd_touch_down = pd_touch_norm < pd_touch_signal

        all_slope_up = slope_ma_pd_touch_up and slope_ma_pd_up and slope_ma_b_up
        all_slope_down = slope_ma_pd_touch_down and slope_ma_pd_down and slope_ma_pd_touch_down

        # Above/Below zero
        slope_ma_b_above = time_norm > 0
        slope_ma_pd_above = pd_norm > 0
        slope_ma_pd_touch_above = pd_touch_norm > 0
        all_above = slope_ma_b_above and slope_ma_pd_touch_above and slope_ma_pd_above

        slope_ma_b_below = time_norm < 0
        slope_ma_pd_below = pd_norm < 0
        slope_ma_pd_touch_below = pd_touch_norm < 0
        all_below = slope_ma_b_below and slope_ma_pd_touch_below and slope_ma_pd_below

        # Signal comparisons
        time_more_price = time_signal > pd_touch_signal
        price_more_time = pd_touch_signal > time_signal

        # Corrections
        correction_after_up = time_norm > pd_touch_norm and all_slope_up
        correction_after_down = time_norm < pd_touch_norm and all_slope_down

        # Entry conditions
        longCond = all_above and all_slope_up and price_more_time and sh > 0
        shortCond = all_below and all_slope_down and time_more_price and sh < 0

        # Exit conditions
        exitlongCond = correction_after_up
        exitshortCond = correction_after_down

        # Execute trades
        if not self.position:
            if longCond:
                self.buy()
            elif shortCond:
                self.sell()
        else:
            if self.position.size > 0:
                if exitlongCond or shortCond:
                    self.close()
                    if shortCond:
                        self.sell()
            elif self.position.size < 0:
                if exitshortCond or longCond:
                    self.close()
                    if longCond:
                        self.buy()


# Example usage
if __name__ == '__main__':
    cerebro = bt.Cerebro()

    # Example 1: Strategy with 3 MAs
    cerebro.addstrategy(PDMAStrategy, ma_periods=[50, 100, 150])

    # Example 2: Strategy with 5 MAs (default)
    # cerebro.addstrategy(PDMAStrategy, ma_periods=[50, 100, 150, 200, 250])

    # Example 3: Custom MA periods
    # cerebro.addstrategy(PDMAStrategy, ma_periods=[20, 50, 100, 200])

    # Add data feed (replace with your data)
    # data = bt.feeds.GenericCSVData(
    #     dataname='your_data.csv',
    #     dtformat='%Y-%m-%d',
    #     datetime=0,
    #     open=1,
    #     high=2,
    #     low=3,
    #     close=4,
    #     volume=5,
    #     openinterest=-1
    # )
    # cerebro.adddata(data)

    # Set initial capital
    cerebro.broker.setcash(1000.0)

    # Set commission
    cerebro.broker.setcommission(commission=0.001)

    # Print starting conditions
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')

    # Run strategy
    cerebro.run()

    # Print final result
    print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')

    # Plot results
    cerebro.plot()
