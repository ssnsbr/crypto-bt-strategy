
from backtrader_extended.strategies.Base_Crypto import BaseCryptoTradingStrategy
import backtrader as bt


class SOL_TrendAware_MeanReversion_RSI(BaseCryptoTradingStrategy):
    """
    Solana Mean Reversion with Trend Filter + RSI Confirmation
    - Trades pullbacks to mean_ma only in direction of trend
    - Uses RSI(3) to confirm oversold/overbought pullbacks
    - Exits when price returns to mean, TP/SL hits, or after N candles
    """

    params = dict(
        ma_fast=90,        # short-term trend
        ma_slow=240,       # long-term trend
        mean_ma=60,        # mean level for reversion
        rsi_period=3,      # fast RSI
        rsi_buy=30,        # oversold
        rsi_sell=70,       # overbought
        max_hold=5,        # exit after N candles
        sl_percent=0.02,
        tp_percent=0.02,
        log=True
    )

    def __init__(self):
        super().__init__()

        # === Indicators ===
        self.ma_fast = bt.indicators.EMA(self.datas[0].close, period=self.p.ma_fast)
        self.ma_slow = bt.indicators.EMA(self.datas[0].close, period=self.p.ma_slow)
        self.mean_ma = bt.indicators.EMA(self.datas[0].close, period=self.p.mean_ma)
        self.rsi = bt.indicators.RSI(self.datas[0].close, period=self.p.rsi_period)

        # === State ===
        self.order = None
        self.entry_index = 0

    def _execute_trading_logic(self):
        if self.order:
            return

        pos = self.getposition(self.datas[0])
        in_position = pos.size != 0
        price = self.dataclose[0]

        fast = self.ma_fast[0]
        slow = self.ma_slow[0]
        mean = self.mean_ma[0]
        rsi = self.rsi[0]

        # === Trend direction ===
        uptrend = fast > slow
        downtrend = fast < slow

        # === Entries ===
        if not in_position:
            # BUY pullback: uptrend + price below mean + RSI oversold
            if uptrend and price < mean and rsi < self.p.rsi_buy:
                self.order = self.buy()
                self.entry_index = len(self)
                if self.p.log:
                    self.log(f"BUY mean-reversion pullback @ {price:.2f}, RSI={rsi:.1f}")

            # SELL pullback: downtrend + price above mean + RSI overbought
            elif downtrend and price > mean and rsi > self.p.rsi_sell:
                self.order = self.sell()
                self.entry_index = len(self)
                if self.p.log:
                    self.log(f"SELL mean-reversion pullback @ {price:.2f}, RSI={rsi:.1f}")

        # === Exits ===
        else:
            # Common exit rules
            max_candles = (len(self) - self.entry_index) >= self.p.max_hold

            if pos.size > 0:  # Long
                if price >= mean or max_candles or price <= pos.price * (1 - self.p.sl_percent):
                    self.close()
                    if self.p.log:
                        self.log(f"Exit LONG @ {price:.2f} after {len(self)-self.entry_index} candles")

                elif price >= pos.price * (1 + self.p.tp_percent):
                    self.close()
                    if self.p.log:
                        self.log(f"TP LONG @ {price:.2f}")

            elif pos.size < 0:  # Short
                if price <= mean or max_candles or price >= pos.price * (1 + self.p.sl_percent):
                    self.close()
                    if self.p.log:
                        self.log(f"Exit SHORT @ {price:.2f} after {len(self)-self.entry_index} candles")

                elif price <= pos.price * (1 - self.p.tp_percent):
                    self.close()
                    if self.p.log:
                        self.log(f"TP SHORT @ {price:.2f}")

    def stop(self):
        pos = self.getposition(self.datas[0])
        if pos.size != 0:
            self.log(f"END: Closing {pos.size} @ {self.dataclose[0]:.2f}")
            self.close()
        super().stop()
