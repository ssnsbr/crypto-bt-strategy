
from backtrader_extended.strategies.Base_Crypto import BaseCryptoTradingStrategy
from riskmanagers.NoneRiskManagement import NoneRiskManagement
import backtrader as bt


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
