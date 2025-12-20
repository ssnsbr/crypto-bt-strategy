import backtrader as bt
import math


# -------------------------
# DEMA
# -------------------------
class DEMA(bt.Indicator):
    lines = ('dema',)
    params = (('period', 20),)

    def __init__(self):
        ema1 = bt.indicators.EMA(self.data, period=self.p.period)
        ema2 = bt.indicators.EMA(ema1, period=self.p.period)
        self.lines.dema = 2 * ema1 - ema2


# -------------------------
# TEMA
# -------------------------
class TEMA(bt.Indicator):
    lines = ('tema',)
    params = (('period', 20),)

    def __init__(self):
        ema1 = bt.indicators.EMA(self.data, period=self.p.period)
        ema2 = bt.indicators.EMA(ema1, period=self.p.period)
        ema3 = bt.indicators.EMA(ema2, period=self.p.period)
        self.lines.tema = 3 * (ema1 - ema2) + ema3


class NEMA(bt.Indicator):
    """
    N-th Order EMA:
    N=1 → EMA
    N=2 → DEMA
    N=3 → TEMA
    N=4 → Quadruple EMA
    ...
    """
    lines = ('nema',)
    params = (('period', 20), ('n', 3))

    def __init__(self):
        # Step 1 — compute EMA1, EMA2, ..., EMA_N
        emas = []
        ema_prev = bt.ind.EMA(self.data, period=self.p.period)
        emas.append(ema_prev)

        for i in range(2, self.p.n + 1):
            ema_prev = bt.ind.EMA(ema_prev, period=self.p.period)
            emas.append(ema_prev)

        # Step 2 — build NEMA using binomial formula
        # NEMA = Σ (-1)^k * C(N-1, k) * EMA(k+1)
        nema = 0
        N = self.p.n

        for k in range(N):
            coeff = ((-1) ** k) * math.comb(N - 1, k)
            nema += coeff * emas[k]

        self.lines.nema = nema
