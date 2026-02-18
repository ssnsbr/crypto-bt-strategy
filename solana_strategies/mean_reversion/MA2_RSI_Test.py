

class MA2_RSI_Test(BaseCryptoTradingStrategy):
    params = (
        ('ma_fast', 26),
        ('ma_slow', 90),
        #
        ('swing_period', 5),
        ("main_tf", 0),
        #
        ("tp", 0.1),
        ("sl", 0.1),
        ("trend_thresh", 0.007),
        #
        ("bb_period", 15),
        ("bb_dev", 2.75),
    )

    def __init__(self):
        super().__init__()
        print("self.p.main_tf:", self.p.main_tf)
        for i, d in enumerate(self.datas):
            print(f"Data {i}: timeframe={d.params.timeframe}, compression={d.params.compression}")
        main_data = self.datas[self.p.main_tf]

        # --- MA ---
        self.ma_slow = bt.indicators.EMA(main_data.close, period=self.p.ma_slow)
        self.ma_fast = bt.indicators.EMA(main_data.close, period=self.p.ma_fast)
        #
        self.highest_in_3 = bt.indicators.Highest(main_data.high, period=self.p.swing_period)
        self.lowest_in_3 = bt.indicators.Lowest(main_data.low, period=self.p.swing_period)
        # --- BB ---
        self.bb = bt.indicators.BollingerBands(main_data.close, period=self.p.bb_period, devfactor=self.p.bb_dev)
        self.bb_mid = self.bb.lines.mid
        self.bb_top = self.bb.lines.top
        self.bb_bot = self.bb.lines.bot
        # --- RSI ---
        self.rsi3 = bt.indicators.RSI(main_data.close, period=4)
        self.rsi14 = bt.indicators.RSI(main_data.close, period=14)
        self.risk_manager = NoneRiskManagement(self)
        self._sl = 0
        self._tp = 0
        self.price = 0

    def _find_trend(self):
        if self.ma_fast[0] > self.ma_slow[0]:
            return 1
        if self.ma_fast[0] < self.ma_slow[0]:
            return -1

    # ------------- ENTRY

    def _long_conditions(self):
        trend = self._find_trend()
        _trend_cond = trend == 1 and self.price < self.ma_fast[0]
        _bb_cond = self.price < self.bb_top[0]
        _rs_cond = self.rsi3[0] < 30
        return (_bb_cond or _rs_cond) and _trend_cond

    def _short_conditions(self):
        trend = self._find_trend()
        _trend_cond = trend == -1 and self.price > self.ma_fast[0]
        _bb_cond = self.price > self.bb_bot[0]
        _rs_cond = self.rsi3[0] > 70
        return (_bb_cond or _rs_cond) and _trend_cond

    # ------------- EXIT
    def _close_long_conditions(self):
        _sl_cond = self.price < self._sl
        _tp_cond = self.price > self._tp
        _rsi14_cond = self.rsi14 > 60
        _bb_cond = self.price > self.bb_top[0]
        _candle_trend_cond = self.datas[0].close < self.datas[1].close

        # return _rsi14_cond  or (_tp_cond and _sl_cond)
        # return _sl_cond  or (_tp_cond and _rsi14_cond)
        return _candle_trend_cond

    def _close_short_conditions(self):
        _sl_cond = self.price > self._sl
        _tp_cond = self.price < self._tp
        _rsi14_cond = self.rsi14 < 40
        # return _sl_cond or (_tp_cond and _rsi14_cond)
        _bb_cond = self.price < self.bb_top[0]
        _candle_trend_cond = self.datas[0].close > self.datas[1].close
        return _candle_trend_cond

    def _execute_trading_logic(self):
        main_data = self.datas[self.p.main_tf]
        self.price = main_data.close[0]
        pos = self.getposition(main_data)

        if not pos.size:
            if self._long_conditions():
                self.order = self.buy()
                self._tp = self.price * (1 + self.p.tp)
                self._sl = self.lowest_in_3[0] - self.lowest_in_3[0] * self.p.trend_thresh
            elif self._short_conditions():
                self.order = self.sell()
                self._tp = self.price * (1 - self.p.tp)
                self._sl = self.highest_in_3[0] + self.highest_in_3[0] * self.p.trend_thresh
        else:
            # LONG management
            if pos.size > 0:
                if self._close_long_conditions():
                    self.close()

            # SHORT management
            elif pos.size < 0:
                if self._close_short_conditions():
                    self.close()

    def stop(self):
        pos = self.getposition(self.datas[self.p.main_tf])
        if pos.size != 0:
            self.close()
        super().stop()


all_results_df, all_cerebros_objects, all_portfolio_histories = run_me(MA2_RSI_Test, df_len=1_000, multi_tf=["1m", "5m"])
