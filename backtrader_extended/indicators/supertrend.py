import backtrader as bt
import math


class SuperTrend(bt.Indicator):
    """
    Exact translation of:
    - ATR Period
    - ATR Multiplier
    - changeATR (true = ATR, false = SMA of TR)
    - Supertrend up/down bands
    - Trend direction (1/-1)
    - Buy/Sell signals on trend flip
    """

    lines = ('trend', 'up', 'dn', 'buySignal', 'sellSignal')
    params = (
        ('period', 10),
        ('multiplier', 3.0),
        ('changeATR', True),   # True = ATR(), False = SMA(TR)
    )

    plotlines = dict(
        up=dict(color="green", _plotskip=False),
        dn=dict(color="red", _plotskip=False),
        trend=dict(_plotskip=True),
        buySignal=dict(color="green", marker='^', markersize=6.0),
        sellSignal=dict(color="red", marker='v', markersize=6.0),
    )

    def __init__(self):

        # --- Source is OHLC4 exactly like TradingView ---
        self.src = (self.data.open + self.data.high +
                    self.data.low + self.data.close) / 4

        # --- True Range ---
        tr = bt.indicators.TrueRange()

        # --- ATR logic ---
        if self.p.changeATR:
            self.atr = bt.indicators.ATR(period=self.p.period)
        else:
            self.atr = bt.indicators.SMA(tr, period=self.p.period)

        # memory variables (Pine uses mutation: up := ...)
        self.up1 = 0
        self.dn1 = 0
        self.trend_prev = 1

    def next(self):

        close = self.data.close[0]

        # ------- CALCULATE INITIAL UP & DN -------
        up = self.src[0] - (self.p.multiplier * self.atr[0])
        dn = self.src[0] + (self.p.multiplier * self.atr[0])

        # ------- PREVIOUS VALUES (Pinescript nz(up[1], up)) -------
        up1_prev = self.up1 if not math.isnan(self.up1) else up
        dn1_prev = self.dn1 if not math.isnan(self.dn1) else dn

        # ------- Pinescript logic for rewriting up / dn -------
        if self.data.close[-1] > up1_prev:
            up = max(up, up1_prev)
        if self.data.close[-1] < dn1_prev:
            dn = min(dn, dn1_prev)

        # store memory for next candle
        self.up1 = up
        self.dn1 = dn

        # ------- TREND LOGIC EXACTLY MATCHING PINE -------
        trend = self.trend_prev

        if trend == -1 and close > dn1_prev:
            trend = 1
        elif trend == 1 and close < up1_prev:
            trend = -1

        # write to output lines
        self.lines.up[0] = up
        self.lines.dn[0] = dn
        self.lines.trend[0] = trend

        # ------- BUY/SELL SIGNALS -------
        buySignal = trend == 1 and self.trend_prev == -1
        sellSignal = trend == -1 and self.trend_prev == 1

        self.lines.buySignal[0] = 1 if buySignal else 0
        self.lines.sellSignal[0] = 1 if sellSignal else 0

        # save trend for next step
        self.trend_prev = trend
