
from backtrader_extended.strategies.Base_Crypto import BaseCryptoTradingStrategy
from meme_strategies.trade_engine_indicators import DEMA, TimeDistance
import backtrader as bt


class PDMAStrategy(BaseCryptoTradingStrategy):
    """PDMA / ma_b Strategy: Price from Last Touch"""
    params = (
        ('ma_types', ['dema', 'dema', 'dema', 'dema', 'dema']),  # MA types
        ('ma_periods', [50, 100, 150, 200, 250]),  # MA periods
        ('src', 'hlc3'),  # Source data
        ('smooth', 23),
        ('tpPerc', 10.0),
        ('slPerc', 10.0),
        ('reverse', False),
        ('useZtime', True),
        ('lengthMA', 34),
        ('lengthSignal', 9),
        ('normalize_len', 200),
        ('signal_len', 15),
        ('ema_filter', [True, "dema", 360])
    )

    def __init__(self):
        super().__init__()
        # custom indicator
        self.ind = TimeDistance(
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
        self.ind.update(self.datas[0])  # update gets a candle object which should have object.close
        # if self.params.ema_filter[0]:
        #     self.ema.update(self.datas[0])
        #     ema_value = self.ema.values()["value"]
        ema_value = self.ema[0]

        # Get indicator values

        ma_b_norm_signal = self.ind.values()["signal"]
        slope_ma_b_up = self.ind.values()["slope_up"]
        slope_ma_b_down = self.ind.values()["slope_down"]
        # slope_ma_b_up = ma_b_norm > ma_b_norm_signal
        # slope_ma_b_down = ma_b_norm < ma_b_norm_signal

        if self.params.reverse:
            longCond = slope_ma_b_down and ma_b_norm_signal > 0
            shortCond = slope_ma_b_up and ma_b_norm_signal < 0
        else:
            longCond = slope_ma_b_up and ma_b_norm_signal < 0
            shortCond = slope_ma_b_down and ma_b_norm_signal > 0
        # print("longCond",longCond,"shortCond:",shortCond,"Signal:",ma_b_norm_signal,"Up:",slope_ma_b_down,"Down:",slope_ma_b_up)

        # Execute trades

        # =========================
        # NO POSITION
        # =========================
        if not self.position:
            if longCond:
                if self.params.ema_filter[0]:
                    if price > ema_value:
                        self.buy()
                else:
                    self.buy()

            elif shortCond:
                if self.params.ema_filter[0]:
                    if price < ema_value:
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
