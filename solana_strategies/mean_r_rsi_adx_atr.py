
from riskmanagers.NoneRiskManagement import NoneRiskManagement
from strategies.Base_Crypto import BaseCryptoTradingStrategy
import backtrader as bt


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
