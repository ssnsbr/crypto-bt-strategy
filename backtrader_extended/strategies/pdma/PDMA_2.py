# BaseCryptoTradingStrategy
# super().__init__()
# self.risk_manager = NoneRiskManagement(self)
# def _execute_trading_logic(self):

class PDMAStrategy(BaseTradingStrategy):
    """PDMA / ma_b Strategy: Price from Last Touch"""
    params = (
        ('ma_types', ['ema', 'ema', 'ema', 'ema', 'ema']),  # MA types
        ('ma_periods', [50, 100, 150, 200, 250]),  # MA periods
        ('src', 'hlc3'),  # Source data
        ('smooth', 23),
        ('tp', 0.1),
        ('sl', 0.1),
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
        super().__init__()
        self.risk_manager = NoneRiskManagement(self)

        # Impulse MACD
        # self.impulse = ImpulseMACD(
        #     self.data,
        #     lengthMA=self.p.lengthMA,
        #     lengthSignal=self.p.lengthSignal
        # )

        # Price Distance from Touch
        # self.price_touch = PriceDistanceFromTouch(
        #     self.data,
        #     ma_types=self.p.ma_types,
        #     ma_periods=self.p.ma_periods,
        #     src=self.p.src,
        #     smooth=self.p.smooth,
        #     useZ=self.p.useZtouch,
        #     normalize_len=self.p.normalize_len,
        #     signal_len=self.p.signal_len
        # )

        # Price Distance from MA
        # self.price_dist = PriceDistanceFromMA(
        #     self.data,
        #     ma_types=self.p.ma_types,
        #     ma_periods=self.p.ma_periods,
        #     src=self.p.src,
        #     smooth=self.p.smooth,
        #     useZ=self.p.useZprice,
        #     normalize_len=self.p.normalize_len,
        #     signal_len=self.p.signal_len
        # )

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
        # self.vol_dist = VolumeDistance(
        #     self.data,
        #     ma_types=self.p.ma_types,
        #     ma_periods=self.p.ma_periods,
        #     src=self.p.src,
        #     smooth=self.p.smooth,
        #     useZ=self.p.useZvolume,
        #     normalize_len=self.p.normalize_len,
        #     signal_len=self.p.signal_len
        # )

    def next(self):
        # Get indicator values
        # pd_touch_norm = self.price_touch.pd_touch_norm[0]
        # pd_touch_signal = self.price_touch.pd_touch_signal[0]
        # pd_norm = self.price_dist.pd_norm[0]
        # pd_signal = self.price_dist.pd_signal[0]
        time_norm = self.time_dist.time_norm[0]
        time_signal = self.time_dist.time_signal[0]
        # sh = self.impulse.sh[0]

        # Slope conditions
        # slope_ma_pd_touch_up = pd_touch_norm > pd_touch_signal
        # slope_ma_pd_up = pd_norm > pd_signal
        slope_ma_b_up = time_norm > time_signal

        slope_ma_b_down = time_norm < time_signal
        # slope_ma_pd_down = pd_norm < pd_signal
        # slope_ma_pd_touch_down = pd_touch_norm < pd_touch_signal

        # all_slope_up = slope_ma_pd_touch_up and slope_ma_pd_up and slope_ma_b_up
        # all_slope_down = slope_ma_pd_touch_down and slope_ma_pd_down and slope_ma_pd_touch_down

        # Above/Below zero
        slope_ma_b_above = time_norm > 0
        # slope_ma_pd_above = pd_norm > 0
        # slope_ma_pd_touch_above = pd_touch_norm > 0
        # all_above = slope_ma_b_above and slope_ma_pd_touch_above and slope_ma_pd_above

        slope_ma_b_below = time_norm < 0
        # slope_ma_pd_below = pd_norm < 0
        # slope_ma_pd_touch_below = pd_touch_norm < 0
        # all_below = slope_ma_b_below and slope_ma_pd_touch_below and slope_ma_pd_below

        # Signal comparisons
        # time_more_price = time_signal > pd_touch_signal
        # price_more_time = pd_touch_signal > time_signal

        # Corrections
        # correction_after_up = time_norm > pd_touch_norm and all_slope_up
        # correction_after_down = time_norm < pd_touch_norm and all_slope_down

        # Entry conditions
        # longCond = all_above and all_slope_up and price_more_time and sh > 0
        # shortCond = all_below and all_slope_down and time_more_price and sh < 0
        longCond = slope_ma_b_up
        shortCond = slope_ma_b_down
        longCond = slope_ma_b_down
        shortCond = slope_ma_b_up

        # Exit conditions
        # exitlongCond = correction_after_up
        # exitshortCond = correction_after_down
        if self.current_price > self.portfolio_avg_buy_price * (1 + self.p.tp):
            self.close()
            return
        if self.current_price < self.portfolio_avg_buy_price * (1 - self.p.sl):
            self.close()
            return

        # Execute trades
        if not self.position:
            if longCond:
                self.buy()
                return
        else:
            if self.position.size > 0:
                if shortCond:
                    self.close()
                    return


st = PDMAStrategy


@dataclass
class RunConfig:
    results_folder: str = '/content/drive/MyDrive/charts/results/'
    cash: float = 100
    mcap: bool = True
    after_ath: bool = False
    min_start_minutes_to_wait: int = 20
    randomize_start_margin: bool = True
    df_end_margin: int = -1
    max_start_margin: int = 60
    min_start_margin: int = 10
    cerebro_runonce: bool = False


config = RunConfig()
#  6 400
# 78910 400 900

sp = {
    'dead_coin_market_cap': 9_000, 'migration_market_cap': 100_000
}


sp['data_in_market_cap'] = True
sp['log'] = False

list_of_files_to_run = new_csv_files_1s
list_of_files_to_run = csv_files_1s[:]
is_there_duplicate = False
# is_there_duplicate = if_duplicate(file_to_run=list_of_files_to_run,
#             sizer_class=sizer_class,
#             strategy_class=strategy_class,
#             strategy_params=sp
#             , sizer_params=zp
#             , config=config)

if not is_there_duplicate:

    strategy_class = PDMAStrategy
    config.after_ath = True

    run_and_save(file_to_run=list_of_files_to_run,
                 sizer_class=sizer_class,
                 strategy_class=strategy_class,
                 strategy_params=sp, sizer_params=zp, config=config)
