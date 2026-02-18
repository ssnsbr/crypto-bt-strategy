
from riskmanagers.NoneRiskManagement import NoneRiskManagement
from backtrader_extended.strategies.Base_Crypto import BaseCryptoTradingStrategy
import backtrader as bt


class SOL_TrendAware_MeanReversion(BaseCryptoTradingStrategy):
    """
    Solana Mean Reversion with Trend Filter
    - Trades pullbacks to mean_ma in the direction of trend
    - Trend defined by MA_fast / MA_slow crossover
    - Mean defined by mean_ma
    """

    params = dict(
        ma_fast=50,        # short-term trend
        ma_slow=200,       # long-term trend
        mean_ma=20,        # mean level for reversion
        sl_percent=0.02,
        tp_percent=0.02,
        log=True
    )

    def __init__(self):
        super().__init__()
        self.ma_fast = bt.indicators.EMA(self.datas[0].close, period=self.p.ma_fast)
        self.ma_slow = bt.indicators.EMA(self.datas[0].close, period=self.p.ma_slow)
        self.mean_ma = bt.indicators.SMA(self.datas[0].close, period=self.p.mean_ma)

        self.order = None
        self.entry_index = 0
        self.risk_manager = NoneRiskManagement(self)

    def _execute_trading_logic(self):
        if self.order:
            return

        pos = self.getposition(self.datas[0])
        in_position = pos.size != 0
        price = self.dataclose[0]

        fast = self.ma_fast[0]
        slow = self.ma_slow[0]
        mean = self.mean_ma[0]

        # === Determine Trend ===
        uptrend = fast > slow
        downtrend = fast < slow

        # === Entry Logic ===
        if not in_position:
            if uptrend and price < mean:
                self.order = self.buy()
                if self.p.log:
                    self.log(f"BUY pullback in uptrend @ {price:.2f} (fast>{slow})")

            elif downtrend and price > mean:
                self.order = self.sell()
                if self.p.log:
                    self.log(f"SELL pullback in downtrend @ {price:.2f} (fast<{slow})")

        # === Exit Logic ===
        else:
            if pos.size > 0:  # Long
                if price >= mean or price <= pos.price * (1 - self.p.sl_percent):
                    self.close()
                    if self.p.log:
                        self.log(f"Close LONG @ {price:.2f}")
                elif price >= pos.price * (1 + self.p.tp_percent):
                    self.close()
                    if self.p.log:
                        self.log(f"Take Profit LONG @ {price:.2f}")

            elif pos.size < 0:  # Short
                if price <= mean or price >= pos.price * (1 + self.p.sl_percent):
                    self.close()
                    if self.p.log:
                        self.log(f"Close SHORT @ {price:.2f}")
                elif price <= pos.price * (1 - self.p.tp_percent):
                    self.close()
                    if self.p.log:
                        self.log(f"Take Profit SHORT @ {price:.2f}")

    def stop(self):
        pos = self.getposition(self.datas[0])
        if pos.size != 0:
            self.log(f"END OF BACKTEST: Closing {pos.size} @ {self.dataclose[0]:.2f}")
            self.close()
        super().stop()


class MeanReversionInTrend(BaseCryptoTradingStrategy):
    """
    Mean Reversion with Trend Confirmation (1m TF)
    - Trades reversion setups only in direction of trend
    - Trend = ADX(5m & 15m) strong + RSI(higher TF)
    - Entry = price stretch beyond Bollinger Bands
    - SL = 4xATR of entry candle
    - TP = close above upper/lower BB (opposite side)
    """

    params = dict(
        bb_period=20,
        bb_mult=2.0,
        atr_period=14,
        ema_period=200,
        adx_period_5=14,
        adx_period_15=14,
        adx_trend=25,          # Minimum ADX to consider trend valid
        rsi_period=14,
        z_thrsh=2.5,
        log=True
    )

    def __init__(self):
        super().__init__()

        # === Base timeframe (1m) indicators ===
        self.bb = bt.indicators.BollingerBands(
            self.data.close,
            period=self.p.bb_period,
            devfactor=self.p.bb_mult
        )
        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period)
        self.ema = bt.indicators.EMA(self.data, period=self.p.ema_period)
        self.rsi = bt.indicators.RSI(self.data, period=self.p.rsi_period * 15)

        # === Higher TFs ===
        # data1 = 5m, data2 = 15m (added in Cerebro)
        self.adx_5m = bt.indicators.ADX(self.datas[1], period=self.p.adx_period_5)
        self.adx_15m = bt.indicators.ADX(self.datas[2], period=self.p.adx_period_15)
        self.rsi_htf = bt.indicators.RSI(self.datas[0], period=self.p.rsi_period * 15)
        # self.rsi_htf = bt.indicators.RSI(self.datas[0], period=self.p.rsi_period * 15)

        self.risk_manager = NoneRiskManagement(self)

        # State vars
        self.order = None
        self.sl_price = None
        self.tp_flag = False

    def _is_trend_up(self):
        """Confirm uptrend using ADX & RSI (5m + 15m + higher TF RSI)."""
        return (
            self.adx_5m[0] > self.p.adx_trend
            and self.adx_15m[0] > self.p.adx_trend
            and self.rsi_htf[0] > 50
        )

    def _is_trend_down(self):
        """Confirm downtrend using ADX & RSI (5m + 15m + higher TF RSI)."""
        return (
            self.adx_5m[0] > self.p.adx_trend
            and self.adx_15m[0] > self.p.adx_trend
            and self.rsi_htf[0] < 50
        )

    def _long_condition(self):
        """Mean reversion buy setup in uptrend."""
        return (
            self._is_trend_up()
            and self.data.close[0] < self.bb.lines.bot[0]  # below lower BB
            # and self.data.close[0] > self.ema[0] * 0.9     # not fighting trend
            # and self.rsi[0] < 30
        )

    def _short_condition(self):
        """Mean reversion short setup in downtrend."""
        return (
            self._is_trend_down()
            and self.data.close[0] > self.bb.lines.top[0]  # above upper BB
            # and self.data.close[0] < self.ema[0] * 1.1     # not fighting trend
            # and self.rsi[0] > 70
        )

    def _execute_trading_logic(self):
        # print(self.rsi[0],self.rsi_htf[0])
        pos = self.getposition()
        price = self.data.close[0]
        # === ENTRY ===
        if not pos:
            if self._long_condition():
                self.sl_price = price - 4 * self.atr[0]
                self.order = self.buy()
                if self.p.log:
                    self.log(f"BUY mean reversion @ {price:.2f} | SL={self.sl_price:.2f}")

            elif self._short_condition():
                self.sl_price = price + 4 * self.atr[0]
                self.order = self.sell()
                if self.p.log:
                    self.log(f"SELL mean reversion @ {price:.2f} | SL={self.sl_price:.2f}")

        # === EXIT ===
        else:
            # Long position management
            if pos.size > 0:
                if price <= self.sl_price:
                    self.close()
                    if self.p.log:
                        self.log(f"STOP LOSS hit @ {price:.2f}")
                elif price > self.bb.lines.top[0]:
                    self.close()
                    if self.p.log:
                        self.log(f"TP hit (BB cross) @ {price:.2f}")

            # Short position management
            elif pos.size < 0:
                if price >= self.sl_price:
                    self.close()
                    if self.p.log:
                        self.log(f"STOP LOSS hit @ {price:.2f}")
                elif price < self.bb.lines.bot[0]:
                    self.close()
                    if self.p.log:
                        self.log(f"TP hit (BB cross) @ {price:.2f}")
