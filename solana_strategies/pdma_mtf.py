from types import SimpleNamespace

from backtrader_extended.strategies.Base_Crypto import BaseCryptoTradingStrategy
from tradeengine_indicators import DEMA, TimeDistance
import backtrader as bt


def _pdma_conditions(time_distance_indicators, reverse: bool) -> tuple[bool, bool]:
    """
    Derive long/short conditions from a time_distance indicator dict.
    Mirrors Pine Script:
        longCond  = slope_up   and signal < 0   (or reversed)
        shortCond = slope_down and signal > 0   (or reversed)
    """
    signal = time_distance_indicators["signal"]
    slope_up = time_distance_indicators["slope_up"]
    slope_down = time_distance_indicators["slope_down"]

    if not reverse:
        long = slope_up and signal < 0
        short = slope_down and signal > 0
    else:
        long = slope_down and signal > 0
        short = slope_up and signal < 0

    return long, short


class MtfPDMAStrategy(BaseCryptoTradingStrategy):
    """PDMA / ma_b Strategy: Price from Last Touch"""
    params = (
        ('ma_types', ['dema', 'dema', 'dema', 'dema', 'dema']),  # MA types
        ('ma_periods', [50, 100, 150, 200, 250]),  # MA periods
        ('src', 'hlc3'),  # Source data
        ('smooth', 23),
        ('tpPerc', 10.0),
        ('slPerc', 10.0),
        #
        ('reverse', True),
        ('reverse_htf', False),
        #
        ('extra_timeframes', ['3m', '5m', '15m', '30m']),
        ('ltf', '3m'),
        ('htf', '30m'),
        #
        ('useZtime', True),
        ('lengthMA', 34),
        ('lengthSignal', 9),
        ('normalize_len', 200),
        ('signal_len', 15),
        ('ema_filter', [False, "dema", 360]),
        ('data_in_market_cap', False),
    )

    def __init__(self):
        super().__init__()
        # indicator 1m
        self.ind = TimeDistance(
            ma_lengths=(50, 100, 150, 200, 250),
            smooth=23,
            useZ=True,
            normalizing=200,
            signaling=15,
        )
        # Higher‑timeframe indicators (store in a dict)
        self.indicators_htf = {}
        for tf in self.extra_timeframes:
            self.indicators_htf[tf] = TimeDistance(
                ma_lengths=(50, 100, 150, 200, 250),
                smooth=23,
                useZ=True,
                normalizing=200,
                signaling=15,
            )

        if self.params.ema_filter[0]:
            # custom indicator
            period = self.p.ema_filter[2]
            if self.params.ema_filter[1] == "dema":
                self.ema = DEMA(period=period)
            if self.params.ema_filter[1] == "ema":
                self.ema = bt.indicators.EMA(self.datas[0], period=period)
            else:
                self.ema = bt.indicators.EMA(self.datas[0], period=period)
        print("init done.")

    def _execute_trading_logic(self):
        price = self.datas[0].close[0]
        # --- 1. Get current 1‑minute bar data ---
        row = {
            "time": self.datas[0].datetime[0],   # Unix timestamp
            "open": self.datas[0].open[0],
            "high": self.datas[0].high[0],
            "low": self.datas[0].low[0],
            "close": self.datas[0].close[0],
            "volume": self.datas[0].volume[0],
        }

        # --- 2. Update base indicator (1m) ---
        self.ind.update(self.datas[0])  # update gets a candle object which should have object.close
        # if self.params.ema_filter[0]:
        #     self.ema.update(self.datas[0])
        #     ema_value = self.ema.values()["value"]

        # Get indicator values

        # --- 3. Aggregate higher timeframes and update their indicators ---
        for tf in self.extra_timeframes:
            finished = self._update_aggregate(tf, row)
            if finished is not None:
                # A new higher‑timeframe candle is complete → update the indicator
                finished = self._update_aggregate(tf, row)
                # Convert dict to a simple object that behaves like a Backtrader line
                fake_data = SimpleNamespace(
                    close=[finished["close"]],
                    high=[finished["high"]],
                    low=[finished["low"]],
                    open=[finished["open"]],
                    volume=[finished["volume"]],
                    datetime=[finished["timestamp"]]
                )
                # Now your .update() can use fake_data.close[0] if it's written that way
                self.indicators_htf[tf].update(fake_data)

        # --- 4. Get indicator values ---
        # 1m conditions
        longCond_1m, shortCond_1m = _pdma_conditions(self.ind.values(), self.params.reverse)

        # Higher timeframe conditions
        longCond_ltf, shortCond_ltf = _pdma_conditions(self.indicators_htf[self.params.ltf].values(), self.params.reverse)
        longCond_htf, shortCond_htf = _pdma_conditions(self.indicators_htf[self.params.htf].values(), self.params.reverse_htf)

        longCond = longCond_ltf and longCond_htf
        shortCond = shortCond_ltf and shortCond_htf

        # print("longCond",longCond,"shortCond:",shortCond,"Signal:",ma_b_norm_signal,"Up:",slope_ma_b_down,"Down:",slope_ma_b_up)
        # Execute trades
        # =========================
        # NO POSITION
        # =========================

        if not self.position:
            if longCond:
                if self.params.ema_filter[0]:
                    if price > self.ema[0]:
                        self.buy()
                else:
                    self.buy()

            elif shortCond:
                if self.params.ema_filter[0]:
                    if price < self.ema[0]:
                        self.sell()
                else:
                    self.sell()

        # =========================
        # POSITION OPEN
        # =========================
        else:
            entry_price = self.position.price

            tpPerc = self.params.tpPerc / 100.0
            slPerc = self.params.slPerc / 100.0

            # ---------- LONG ----------
            if self.position.size > 0:
                tp_price = entry_price * (1 + tpPerc)
                sl_price = entry_price * (1 - slPerc)

                # TP / SL check
                if price >= tp_price or price <= sl_price:
                    self.close()
                    return

                # Opposite signal
                if shortCond:
                    self.close()
                    # self.sell()
                    return

            # ---------- SHORT ----------
            elif self.position.size < 0:
                tp_price = entry_price * (1 - tpPerc)
                sl_price = entry_price * (1 + slPerc)

                # TP / SL check
                if price <= tp_price or price >= sl_price:
                    self.close()
                    return

                # Opposite signal
                if longCond:
                    self.close()
                    # self.buy()
                    return
