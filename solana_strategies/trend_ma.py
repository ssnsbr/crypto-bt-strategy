import backtrader as bt

from strategies.Base_Crypto import BaseCryptoTradingStrategy

# === 1️⃣ ONE-MA STRATEGY ===


class SOL_Trend_1MA(BaseCryptoTradingStrategy):
    """
    Solana 1-MA Trend Strategy
    - Trades in direction of EMA(Period)
    - Buys when price crosses above EMA
    - Shorts when price crosses below EMA
    """

    params = (
        ('ema_period', 100),
        ('tp_percent', 0.02),
        ('sl_percent', 0.02),
        ('log', True),
    )

    def __init__(self):
        super().__init__()
        self.ema = bt.indicators.EMA(self.datas[0].close, period=self.p.ema_period)
        self.order = None

    def _execute_trading_logic(self):
        if self.order:
            return
        pos = self.getposition(self.datas[0])
        price = self.dataclose[0]
        ema = self.ema[0]

        # Entry
        if not pos:
            if price > ema and self.dataclose[-1] <= self.ema[-1]:
                self.order = self.buy()
                if self.p.log:
                    self.log(f"BUY above EMA @ {price:.2f}")
            elif price < ema and self.dataclose[-1] >= self.ema[-1]:
                self.order = self.sell()
                if self.p.log:
                    self.log(f"SELL below EMA @ {price:.2f}")

        # Exit
        elif pos.size > 0 and price < ema:
            self.close()
            if self.p.log:
                self.log(f"Close LONG @ {price:.2f}")
        elif pos.size < 0 and price > ema:
            self.close()
            if self.p.log:
                self.log(f"Close SHORT @ {price:.2f}")


# === 2️⃣ TWO-MA CROSSOVER ===
class SOL_Trend_2MA(BaseCryptoTradingStrategy):
    """
    Solana 2-MA Crossover Strategy
    - Classic fast/slow EMA crossover
    - Trend-following entries, simple exits
    """

    params = (
        ('fast_period', 20),
        ('slow_period', 100),
        ('tp_percent', 0.02),
        ('sl_percent', 0.02),
        ('log', True),
    )

    def __init__(self):
        super().__init__()
        self.fast = bt.indicators.EMA(self.datas[0], period=self.p.fast_period)
        self.slow = bt.indicators.EMA(self.datas[0], period=self.p.slow_period)
        self.crossover = bt.indicators.CrossOver(self.fast, self.slow)
        self.order = None

    def _execute_trading_logic(self):
        if self.order:
            return
        pos = self.getposition(self.datas[0])
        price = self.dataclose[0]

        # Entry
        if not pos:
            if self.crossover > 0:
                self.order = self.buy()
                if self.p.log:
                    self.log(f"BUY crossover up @ {price:.2f}")
            elif self.crossover < 0:
                self.order = self.sell()
                if self.p.log:
                    self.log(f"SELL crossover down @ {price:.2f}")

        # Exit
        elif pos.size > 0 and self.crossover < 0:
            self.close()
            if self.p.log:
                self.log(f"Close LONG on crossdown @ {price:.2f}")
        elif pos.size < 0 and self.crossover > 0:
            self.close()
            if self.p.log:
                self.log(f"Close SHORT on crossup @ {price:.2f}")


# === 3️⃣ THREE-MA ALIGNMENT ===
class SOL_Trend_3MA(BaseCryptoTradingStrategy):
    """
    Solana 3-MA Alignment Strategy
    - Enters only when all three EMAs align (short > mid > long or vice versa)
    - Exits when alignment breaks
    """

    params = (
        ('short_period', 10),
        ('mid_period', 50),
        ('long_period', 200),
        ('log', True),
    )

    def __init__(self):
        super().__init__()
        self.short = bt.indicators.EMA(self.datas[0], period=self.p.short_period)
        self.mid = bt.indicators.EMA(self.datas[0], period=self.p.mid_period)
        self.long = bt.indicators.EMA(self.datas[0], period=self.p.long_period)
        self.order = None

    def _execute_trading_logic(self):
        if self.order:
            return
        pos = self.getposition(self.datas[0])
        price = self.dataclose[0]

        uptrend = self.short[0] > self.mid[0] > self.long[0]
        downtrend = self.short[0] < self.mid[0] < self.long[0]

        # Entry
        if not pos:
            if uptrend:
                self.order = self.buy()
                if self.p.log:
                    self.log(f"BUY 3-MA alignment @ {price:.2f}")
            elif downtrend:
                self.order = self.sell()
                if self.p.log:
                    self.log(f"SELL 3-MA alignment @ {price:.2f}")

        # Exit
        elif pos.size > 0 and not uptrend:
            self.close()
            if self.p.log:
                self.log(f"Close LONG (alignment lost) @ {price:.2f}")
        elif pos.size < 0 and not downtrend:
            self.close()
            if self.p.log:
                self.log(f"Close SHORT (alignment lost) @ {price:.2f}")
