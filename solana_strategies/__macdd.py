import math
import backtrader as bt

from riskmanagers.noneRiskManagement import NoneRiskManagement
from backtrader_extended.strategies.Base_Crypto import BaseCryptoTradingStrategy

class ZigZagTrend(bt.Indicator):
    """
    Lightweight ZigZag-based trend indicator.
    Detects if recent swing direction is up or down.
    """
    lines = ('trend',)
    params = dict(pct=1.5)  # min % change to define a swing

    def __init__(self):
        self.addminperiod(3)
        self.last_pivot = None
        self.last_dir = 0

    def next(self):
        high = self.data.high[0]
        low = self.data.low[0]

        if self.last_pivot is None:
            self.last_pivot = self.data.close[0]
            self.lines.trend[0] = 0
            return

        change_up = (high - self.last_pivot) / self.last_pivot * 100
        change_down = (self.last_pivot - low) / self.last_pivot * 100

        if self.last_dir <= 0 and change_up > self.p.pct:
            self.last_pivot = high
            self.last_dir = 1
        elif self.last_dir >= 0 and change_down > self.p.pct:
            self.last_pivot = low
            self.last_dir = -1

        self.lines.trend[0] = self.last_dir


class SOL_EMA_MACD_LongShort_1m(BaseCryptoTradingStrategy):

    params = dict(
        ema_long=200,  # simulates 1h trend
        ema_mid=50,    # simulates 15m trend
        ema_short=20,  # short-term trend
        macd_me1=12,
        macd_me2=26,
        macd_signal=9,
        atr_period=14,
        atr_tp_mult=2.0,
        atr_sl_mult=1.0,
        rsi_period=14,
        rsi_overbought=70,
        rsi_oversold=30,
        vol_window=20,
        zigzag_pct=1.5,
        adx_period=14,
        adx_threshold=20,
        log=True,
    )

    def __init__(self):
        super().__init__()

        # --- EMAs on same 1m feed ---
        self.ema_long = bt.ind.EMA(self.datas[0].close, period=self.p.ema_long)
        self.ema_mid = bt.ind.EMA(self.datas[0].close, period=self.p.ema_mid)
        self.ema_short = bt.ind.EMA(self.datas[0].close, period=self.p.ema_short)

        # --- MACD ---
        self.macd = bt.ind.MACD(self.datas[0].close,
                                period_me1=self.p.macd_me1,
                                period_me2=self.p.macd_me2,
                                period_signal=self.p.macd_signal)
        self.macd_cross = bt.ind.CrossOver(self.macd.macd, self.macd.signal)

        # --- Additional indicators ---
        self.atr = bt.ind.ATR(self.datas[0], period=self.p.atr_period)
        self.rsi = bt.ind.RSI(self.datas[0], period=self.p.rsi_period)
        self.adx = bt.ind.ADX(self.datas[0], period=self.p.adx_period)
        self.zigzag = ZigZagTrend(self.datas[0], pct=self.p.zigzag_pct)
        self.risk_manager =

    def _execute_trading_logic(self):
        if self.order:
            return

        pos = self.getposition(self.datas[0])
        price = self.dataclose[0]

        # --- Trend conditions ---
        long_trend_up = self.datas[0].close[0] > self.ema_long[0]
        mid_trend_up = self.datas[0].close[0] > self.ema_mid[0]
        short_up = self.datas[0].close[0] > self.ema_short[0]
        zigzag_up = self.zigzag.lines.trend[0] > 0

        bias_long = long_trend_up and mid_trend_up
        bias_short = not long_trend_up and not mid_trend_up

        # --- Filters ---
        if self.adx[0] < self.p.adx_threshold:
            return
        avg_vol = sum(self.datas[0].volume.get(size=self.p.vol_window)) / self.p.vol_window
        if self.datas[0].volume[0] < avg_vol * 0.5:
            return
        if self.rsi[0] > self.p.rsi_overbought and bias_long:
            return
        if self.rsi[0] < self.p.rsi_oversold and bias_short:
            return

        atr = self.atr[0]
        tp_dist = atr * self.p.atr_tp_mult
        sl_dist = atr * self.p.atr_sl_mult

        # --- LONG ---
        if bias_long and short_up and zigzag_up and self.macd_cross[0] == 1:
            if pos.size <= 0:
                self.close()
                self.order = self.buy_bracket(
                    size=1,
                    limitprice=price + tp_dist,
                    stopprice=price - sl_dist
                )

        # --- SHORT ---
        elif bias_short and not short_up and not zigzag_up and self.macd_cross[0] == -1:
            if pos.size >= 0:
                self.close()
                self.order = self.sell_bracket(
                    size=1,
                    limitprice=price - tp_dist,
                    stopprice=price + sl_dist
                )


run_me(SOL_EMA_MACD_LongShort_1m, 10_000)
