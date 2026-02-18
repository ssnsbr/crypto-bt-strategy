from riskmanagers.NoneRiskManagement import NoneRiskManagement
import backtrader as bt

from backtrader_extended.strategies.Base_Crypto import BaseCryptoTradingStrategy


class SOL_EMA_MACD_LongShort(BaseCryptoTradingStrategy):
    """
    Solana Long/Short Strategy using EMA trend + MACD signal.
    - Long only if price > EMA and MACD crosses above signal (hist < 0)
    - Short only if price < EMA and MACD crosses below signal (hist > 0)
    """

    params = (
        ('ema_period', 200 * 5),
        ('macd_me1', 12 * 5),
        ('macd_me2', 26 * 5),
        ('macd_signal', 9 * 5),

        ('long_ema_period', 1000),
        ('long_macd_me1', 12 * 5),
        ('long_macd_me2', 26 * 5),
        ('long_macd_signal', 9 * 5),

        ('tp_percent', 0.02),
        ('sl_percent', 0.02),
        ('log', True),
    )

    def __init__(self):
        super().__init__()

        # Indicators
        self.ema = bt.indicators.EMA(self.datas[0].close, period=self.p.ema_period)
        self.long_ema = bt.indicators.EMA(self.datas[0].close, period=self.p.long_ema_period)

        self.macd = bt.indicators.MACD(
            self.datas[0].close,
            period_me1=self.p.macd_me1,
            period_me2=self.p.macd_me2,
            period_signal=self.p.macd_signal
        )
        # Compute MACD histogram manually
        self.macd_hist = self.macd.macd - self.macd.signal
        # Crossover detector
        self.macd_cross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

        self.long_macd = bt.indicators.MACD(
            self.datas[0].close,
            period_me1=self.p.long_macd_me1,
            period_me2=self.p.long_macd_me2,
            period_signal=self.p.long_macd_signal
        )
        # Compute MACD histogram manually
        self.long_macd_hist = self.long_macd.macd - self.long_macd.signal
        # Crossover detector
        self.long_macd_cross = bt.indicators.CrossOver(self.long_macd.macd, self.long_macd.signal)

        # Risk manager
        self.risk_manager = NoneRiskManagement(self)
        self.order = None

    def get_trend(self, price, short_ema, long_ema=None):
        short_trend = 0
        long_trend = 0
        # --- Detect Trend ---
        if price > short_ema:
            short_trend = 1
            if long_ema is not None and price > long_ema and short_ema > long_ema:
                long_trend = 1
        elif price < short_ema:
            short_trend = -1
            if long_ema is not None and price < long_ema and short_ema < long_ema:
                long_trend = -1
        if long_ema is not None:
            return long_trend
        else:
            return short_trend

    def _execute_trading_logic(self):
        if self.order:
            return  # Skip if there’s a pending order

        pos = self.getposition(self.datas[0])
        in_position = pos.size != 0

        price = self.dataclose[0]
        long_ema = self.long_ema[0]
        hist = self.macd_hist[0]

        short_ema = self.ema[0]

        long_trend = self.get_trend(price, short_ema, long_ema)
        short_trend = self.get_trend(price, short_ema)
        long_trend = short_trend

        # --- No trend ---
        # if long_trend == 0 or short_trend == 0 or short_trend != long_trend:
        #     return

        if in_position and pos.size > 0:
            # print("Owning",pos.size)
            if self.current_price < self.portfolio_avg_buy_price * (1 - self.p.sl_percent):
                self.close()
                return
            elif self.current_price > self.portfolio_avg_buy_price * (1 + self.p.tp_percent):
                self.close()
                return

        if in_position and pos.size < 0:
            # print("Owning",pos.size)
            if self.current_price > self.portfolio_avg_buy_price * (1 + self.p.sl_percent):
                self.close()
                self.log(f"SL at {price:.2f}")

                return
            elif self.current_price < self.portfolio_avg_buy_price * (1 - self.p.tp_percent):
                self.close()
                self.log(f"TP at {price:.2f}")

                return

        # --- Up Trend
        if long_trend == 1 and short_trend == 1 and self.macd_hist[0] < 0:
            # print("Up Trend.",self.macd_hist[0])
            # --- LONG ENTRY ---
            if self.macd_cross[0] == 1:
                if in_position and pos.size < 0:
                    self.close()
                    self.log(f"Close at {price:.2f}")

                if not in_position or pos.size <= 0:
                    self.order = self.buy()
                    self.log(f"LONG ENTRY at {price:.2f}")

        # --- Down Trend
        if long_trend == -1 and short_trend == -1 and self.macd_hist[0] > 0:
            # print("Down Trend.",self.macd_hist[0])
            # --- SHORT ENTRY ---
            if self.macd_cross[0] == -1:
                if in_position and pos.size > 0:
                    self.close()
                    self.log(f"Close at {price:.2f}")

                if not in_position or pos.size >= 0:
                    self.order = self.sell()
                    self.log(f"SHORT ENTRY at {price:.2f}")

    def stop(self):
        pos = self.getposition(self.datas[0])
        if pos.size != 0:
            self.log(f"END OF BACKTEST: Closing position of size {pos.size} at {self.dataclose[0]:.2f}")
            self.close()
        super().stop()
