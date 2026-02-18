import backtrader as bt


class TwoMALongOnly(BaseTradingStrategy):
    params = (
        ('ma1_type','ema'),      # 'sma', 'ema', 'dema', 'tema'),
        ('ma2_type','sma'),
        ('ma1_period',20),
        ('ma2_period',50),
        ('min_price',50_000),       # trade only if price >= min_price),
        ('max_price',100_000),       # trade only if price <= max_price),
    )
    def __init__(self):
        super().__init__()
        self.ma1 = self._create_ma(self.p.ma1_type, self.p.ma1_period)
        self.ma2 = self._create_ma(self.p.ma2_type, self.p.ma2_period)
        self.ma1_slope_ema = bt.ind.EMA(self.ma1, period=5)  # slope signal
        self.ma2_slope_ema = bt.ind.EMA(self.ma2, period=5)
        self.macd = bt.ind.MACD(self.data.close, period_me1=60, period_me2=130, period_signal=15)
        self.macd_hist = self.macd.macd - self.macd.signal  # histogram

        self.risk_manager = NoneRiskManagement(self)
    def _create_ma(self, ma_type, period):
        ma_type = ma_type.lower()

        if ma_type == 'sma':
            return bt.ind.SMA(self.data.close, period=period)
        elif ma_type == 'ema':
            return bt.ind.EMA(self.data.close, period=period)
        elif ma_type == 'dema':
            return bt.ind.DEMA(self.data.close, period=period)
        elif ma_type == 'tema':
            return bt.ind.TEMA(self.data.close, period=period)
        else:
            raise ValueError(f"Unknown MA type: {ma_type}")

    def _execute_trading_logic(self):
        price = self.data.close[0]

        # Price filter
        if not (self.p.min_price <= price <= self.p.max_price):
            return

        above_both = price > self.ma1[0] and price > self.ma2[0]
        below_both = price < self.ma1[0] and price < self.ma2[0]
        below_one = price < self.ma1[0] or price < self.ma2[0]

        ma1_up = self.ma1_slope_ema[0] > self.ma1_slope_ema[-1]  # EMA of MA increasing
        ma2_up = self.ma2_slope_ema[0] > self.ma2_slope_ema[-1]

        # Check both slopes up
        if ma1_up and ma2_up:
            slope_signal = True
        else:
            slope_signal = False
        macd_positive = self.macd_hist[0] > 0  # histogram above zero

        # Then you can combine it with price above MA
        if not self.position and slope_signal and price > self.ma1[0] and price > self.ma2[0] and macd_positive:
            self.buy()

        # ENTRY (long only)
        # if not self.position and above_both:
            # self.buy()

        # EXIT
        elif self.position and below_one:
            self.sell()


class After_TwoMALongOnly(TwoMALongOnly):
  pass
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

sp={"ma1_type":'tema'
    ,"ma2_type":'dema'
    ,'ma1_period':90
    ,'ma2_period':60
    ,'min_price':50_000
    ,'max_price':500_000
    , 'dead_coin_market_cap': 9_000
    , 'migration_market_cap': 200_000
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


    # strategy_class = TwoMALongOnly
    # config.after_ath= True if strategy_class == After_TwoMALongOnly else False
    # run_and_save(file_to_run=list_of_files_to_run ,
    #             sizer_class=sizer_class,
    #             strategy_class=strategy_class,
    #             strategy_params=sp
    #             , sizer_params=zp
                # , config=config )


    strategy_class = After_TwoMALongOnly
    config.after_ath= True if strategy_class == After_TwoMALongOnly else False

    run_and_save(file_to_run=list_of_files_to_run,
                sizer_class=sizer_class,
                strategy_class=strategy_class,
                strategy_params=sp
                , sizer_params=zp
                , config=config)