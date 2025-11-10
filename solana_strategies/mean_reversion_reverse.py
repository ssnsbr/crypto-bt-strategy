import backtrader as bt

from riskmanagers.NoneRiskManagement import NoneRiskManagement
from strategies.Base_Crypto import BaseCryptoTradingStrategy


class SOL_MeanReversion_BBands_Zscore(BaseCryptoTradingStrategy):
    """
    Solana Mean Reversion Strategy
    - Fades overextensions beyond ±2σ using Bollinger Bands and Z-score
    - Uses EMA(200) to avoid fighting major trend
    - Closes when price returns to mean or stop/take-profit triggers
    """

    params = (
        ('ema_period', 200),
        ('bb_period', 50),
        ('bb_mult', 2.0),
        ('z_period', 50),
        ('rsi_period', 3),
        ('z_thrsh', 3),
        ('end_after', 3),
        ('tp_percent', 0.02),   # small, fast profits
        ('sl_percent', 0.02),
        ('at_mv', True),
        ('log', True),
    )

    def __init__(self):
        super().__init__()

        # === Indicators ===
        self.ema = bt.indicators.EMA(self.datas[0].close, period=self.p.ema_period)

        self.bb = bt.indicators.BollingerBands(
            self.datas[0].close,
            period=self.p.bb_period,
            devfactor=self.p.bb_mult
        )
        self.rsi = bt.indicators.RSI(self.datas[0].close, period=self.p.rsi_period)

        # Compute Z-score
        mean = bt.indicators.SMA(self.datas[0].close, period=self.p.z_period)
        std = bt.indicators.StandardDeviation(self.datas[0].close, period=self.p.z_period)
        self.zscore = (self.datas[0].close - mean) / (std + 1e-9)

        # Risk manager
        self.order = None
        self.entry_index = 0
        self.risk_manager = NoneRiskManagement(self)

    def _execute_trading_logic(self):
        if self.order:
            return

        pos = self.getposition(self.datas[0])
        in_position = pos.size != 0
        price = self.dataclose[0]

        upper = self.bb.lines.top[0]
        mid = self.bb.lines.mid[0]
        lower = self.bb.lines.bot[0]
        ema = self.ema[0]
        z = self.zscore[0]
        rsi = self.rsi[0]

        # # === Trend-Following Pullback Entries === profitable
        # if not in_position:
        #     # BUY pullback in uptrend: price near EMA or lower BB
        #     if price > ema and price <= mid and rsi < 30:
        #         self.order = self.buy()
        #         if self.p.log: self.log(f"BUY trend-continuation @ {price:.2f}")

        #     # SHORT pullback in downtrend: price near EMA or upper BB
        #     elif price < ema and price >= mid and rsi > 70:
        #         self.order = self.sell()
        #         if self.p.log: self.log(f"SHORT trend-continuation @ {price:.2f}")

        # === Mean Reversion Entries ===
        if not in_position:
            # BUY signal: oversold + below lower band + low RSI
            if price < lower and z < -self.p.z_thrsh and rsi < 30:  # and price > ema * 0.9:
                self.order = self.buy()
                if self.p.log:
                    self.log(f"BUY mean reversion @ {price:.2f}, z={z:.2f}, RSI={rsi:.1f}")
                self.entry_index = self.index

            # SHORT signal: overbought + above upper band + high RSI
            elif price > upper and z > self.p.z_thrsh and rsi > 70:  # and price < ema * 1.1:
                self.order = self.sell()
                if self.p.log:
                    self.log(f"SHORT mean reversion @ {price:.2f}, z={z:.2f}, RSI={rsi:.1f}")
                self.entry_index = self.index

        # === Exits ===
        else:
            # Long exits
            if pos.size > 0:
                if price >= mid or price <= pos.price * (1 - self.p.sl_percent):
                    self.close()
                    if self.p.log:
                        self.log(f"Close LONG @ {price:.2f}")
                elif price >= pos.price * (1 + self.p.tp_percent):
                    self.close()
                    if self.p.log:
                        self.log(f"Take Profit LONG @ {price:.2f}")

            # Short exits
            elif pos.size < 0:
                if price <= mid or price >= pos.price * (1 + self.p.sl_percent):
                    self.close()
                    if self.p.log:
                        self.log(f"Close SHORT @ {price:.2f}")
                elif price <= pos.price * (1 - self.p.tp_percent):
                    self.close()
                    if self.p.log:
                        self.log(f"Take Profit SHORT @ {price:.2f}")

            # Short exits
            if pos.size != 0:
                if self.entry_index + self.p.end_after <= self.index:
                    self.close()
                    if self.p.log:
                        self.log(f"Close 10 Candles @ {price:.2f}")

    def stop(self):
        pos = self.getposition(self.datas[0])
        if pos.size != 0:
            self.log(f"END OF BACKTEST: Closing position {pos.size} @ {self.dataclose[0]:.2f}")
            self.close()
        super().stop()


class SOL_TrendAware_MeanReversion_BBands_RSI(bt.Strategy):
    """
    Solana 1-Minute Mean Reversion Strategy with Trend Filter
    ----------------------------------------------------------
    Trend filter:
        - EMA(50) > EMA(200): only LONGs
        - EMA(50) < EMA(200): only SHORTs

    Entry:
        - RSI(3) < 25 and price < lower Bollinger Band (20, 2)
          → enter LONG (only if uptrend)
        - RSI(3) > 75 and price > upper Bollinger Band
          → enter SHORT (only if downtrend)

    Exit:
        - Take profit at Bollinger mid-band (mean)
        - Stop loss at recent swing low/high (3–5 bars lookback)
    """

    params = dict(
        ema_fast=50,
        ema_slow=200,
        bb_period=20,
        bb_dev=2.0,
        rsi_period=3,
        rsi_buy=25,
        rsi_sell=75,
        swing_lookback=5,
        log=True
    )

    def __init__(self):
        # === Trend Filter ===
        self.ema_fast = bt.indicators.EMA(self.data.close, period=self.p.ema_fast)
        self.ema_slow = bt.indicators.EMA(self.data.close, period=self.p.ema_slow)

        # === Bollinger Bands ===
        self.bb = bt.indicators.BollingerBands(self.data.close, period=self.p.bb_period, devfactor=self.p.bb_dev)
        self.bb_mid = self.bb.lines.mid
        self.bb_top = self.bb.lines.top
        self.bb_bot = self.bb.lines.bot

        # === RSI ===
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)

        self.order = None
        self.entry_price = None
        self.entry_index = None

    # Simple logger
    def log(self, msg):
        if self.p.log:
            dt = self.datas[0].datetime.datetime(0)
            print(f"{dt} | {msg}")

    def _recent_swing_low(self, lookback):
        return min(self.data.low.get(size=lookback))

    def _recent_swing_high(self, lookback):
        return max(self.data.high.get(size=lookback))

    def next(self):
        if self.order:
            return

        price = self.data.close[0]
        uptrend = self.ema_fast[0] > self.ema_slow[0]
        downtrend = self.ema_fast[0] < self.ema_slow[0]
        rsi = self.rsi[0]

        pos = self.getposition()

        # === Entry ===
        if not pos:
            # LONG setup
            if uptrend and rsi < self.p.rsi_buy and price < self.bb_bot[0]:
                sl = self._recent_swing_low(self.p.swing_lookback)
                self.order = self.buy()
                self.sl_level = sl
                self.entry_price = price
                self.log(f"BUY @ {price:.4f} | RSI={rsi:.1f} | SL={sl:.4f}")

            # SHORT setup
            elif downtrend and rsi > self.p.rsi_sell and price > self.bb_top[0]:
                sh = self._recent_swing_high(self.p.swing_lookback)
                self.order = self.sell()
                self.sl_level = sh
                self.entry_price = price
                self.log(f"SELL @ {price:.4f} | RSI={rsi:.1f} | SL={sh:.4f}")

        # === Exit ===
        else:
            if pos.size > 0:  # LONG position
                # Stop loss
                if price < self.sl_level:
                    self.close()
                    self.log(f"Exit LONG (SL) @ {price:.4f}")
                # Take profit at mid-band
                elif price >= self.bb_mid[0]:
                    self.close()
                    self.log(f"Exit LONG (Mean Reversion) @ {price:.4f}")

            elif pos.size < 0:  # SHORT position
                if price > self.sl_level:
                    self.close()
                    self.log(f"Exit SHORT (SL) @ {price:.4f}")
                elif price <= self.bb_mid[0]:
                    self.close()
                    self.log(f"Exit SHORT (Mean Reversion) @ {price:.4f}")
