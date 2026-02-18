# MarkofStrategy.py
import backtrader as bt
import enum

from backtrader_extended.strategies.Base_Crypto import BaseCryptoTradingStrategy


class MarkofState(enum.Enum):
    UNDECIDED = 0
    TRENDING = 1     # trend trade (take partials as we climb)
    CORRECTION = 2      # buy the dip / mean reversion in trend
    MOMENTUM = 3        # breakout / momentum trade
    EXIT_ALL = 4


class MarkofStrategy(BaseCryptoTradingStrategy):
    params = dict(
        ema1=10,        # short fast EMA (for trend detection)
        ema2=20,
        ema3=240,       # big trend EMA
        ema4=14400,       # big trend EMA
        rsi_period=14,
        rsi_oversold=35,
        rsi_overbought=65,
        breakout_pct=0.02,   # breakout threshold relative to recent highs/lows (2%)
        correction_pct=0.03,  # depth to consider a corrective dip (3%)
        sl_pct=0.03,         # stop loss (3% default)
        tp1_pct=0.03,        # first partial take profit 3%
        tp2_pct=0.08,        # second take profit 8%
        momentum_rsi=70,
        momentum_macd_hist_threshold=0.0,
        momentum_window=10,  # used for recent high/low
        stake=1.0,           # default size (can map to cash sizing externally)
        verbose=False,
    )

    def __init__(self):
        # indicators
        self.ema1 = bt.ind.EMA(period=self.p.ema1)   # 50
        self.ema2 = bt.ind.EMA(period=self.p.ema2)   # 100
        self.ema3 = bt.ind.EMA(period=self.p.ema3)   # 200
        self.ema4 = bt.ind.EMA(period=self.p.ema4)   # 200

        self.rsi = bt.ind.RSI(period=self.p.rsi_period)
        self.macd = bt.ind.MACD(self.data.close)
        self.macd_hist = self.macd.histo

        # track state
        self.state = MarkofState.UNDECIDED
        self.entry_price = None
        self.recent_high = None
        self.recent_low = None

    def is_uptrend(self):
        return (self.current_price > self.ema1[0] > self.ema2[0])

    def is_downtrend(self):
        return (self.current_price < self.ema1[0] < self.ema2[0])

    def is_htf_uptrend(self):
        return (self.ema3[0] > self.ema4[0])

    def is_htf_downtrend(self):
        return (self.ema3[0] < self.ema4[0])

    def next(self):
        # Determine trend
        uptrend = self.is_uptrend()
        downtrend = self.is_downtrend()
        htf_uptrend = self.is_htf_uptrend()
        htf_downtrend = self.is_htf_downtrend()

        # ---------- State machine transitions ----------
        # pick direction if EMA alignment found
        if uptrend and htf_uptrend:
            self.state = MarkofState.TRENDING
            self.log('STATE -> TRENDING_TP (uptrend detected)')
        elif downtrend and htf_downtrend:
            self.state = MarkofState.TRENDING
            self.log('STATE -> TRENDING_TP (downtrend detected)')
        else:
            self.state = MarkofState.CORRECTION

        # ---------- TRENDING ----------
        if self.state == MarkofState.TRENDING:
            # If we have no position, take a trend position when price pulls slightly above/below EMA1.
            if not self.position:
                # Buy in uptrend when price is above EMA1 and continuing upward momentum
                if uptrend:
                    self.order = self.buy()
                    return
                # short in downtrend when price is below EMA1
                if downtrend:
                    self.order = self.sell()
                    return
            else:
                # Manage existing trend position: partial TP and watch for correction
                # take first partial if price moved tp1_pct above entry for long
                if self.position.size > 0:  # long
                    if (self.current_price >= self.entry_price * (1 + self.p.tp1_pct)) and not self.took_partial:
                        # take partial profit
                        qty = self.position.size * 0.5
                        self.log(f'Partial TP1 for LONG qty={qty:.4f} price={self.current_price:.5f}')
                        self.order = self.close(size=qty)  # close part
                        self.took_partial = True
                        return
                    # full TP2
                    if self.current_price >= self.entry_price * (1 + self.p.tp2_pct):
                        self.log(f'Final TP2 LONG price={self.current_price:.5f}')
                        self.order = self.close()  # close all
                        self.state = MarkofState.UNDECIDED
                        self.took_partial = False
                        return
                    # detect correction (price falling from recent high)
                    if self.recent_high and self.current_price <= self.recent_high * (1 - self.p.correction_pct):
                        self.log('Detected CORRECTION within TREND (long). Moving to CORRECTION state')
                        self.state = MarkofState.CORRECTION
                        return
                    # if momentum breakout (new high + indicators), escalate to momentum
                    if self.recent_high and self.current_price >= self.recent_high * (1 + self.p.breakout_pct) and self.rsi[0] >= self.p.momentum_rsi and self.macd_hist[0] > self.p.momentum_macd_hist_threshold:
                        self.log('Momentum breakout detected. State -> MOMENTUM')
                        self.state = MarkofState.MOMENTUM
                        return
                    # stop loss check
                    if self.current_price <= self.entry_price * (1 - self.p.sl_pct):
                        self.log('SL hit on LONG - closing and resetting')
                        self.order = self.close()
                        self.state = MarkofState.UNDECIDED
                        self.took_partial = False
                        return

                elif self.position.size < 0:  # short
                    if (self.current_price <= self.entry_price * (1 - self.p.tp1_pct)) and not self.took_partial:
                        qty = abs(self.position.size) * 0.5
                        self.log(f'Partial TP1 for SHORT qty={qty:.4f} price={self.current_price:.5f}')
                        self.order = self.close(size=qty)
                        self.took_partial = True
                        return
                    if self.current_price <= self.entry_price * (1 - self.p.tp2_pct):
                        self.log('Final TP2 SHORT - closing all')
                        self.order = self.close()
                        self.state = MarkofState.UNDECIDED
                        self.took_partial = False
                        return
                    if self.recent_low and self.current_price >= self.recent_low * (1 + self.p.correction_pct):
                        self.log('Detected CORRECTION within TREND (short). Moving to CORRECTION state')
                        self.state = MarkofState.CORRECTION
                        return
                    if self.recent_low and self.current_price <= self.recent_low * (1 - self.p.breakout_pct) and self.rsi[0] <= (100 - self.p.momentum_rsi) and self.macd_hist[0] < -self.p.momentum_macd_hist_threshold:
                        self.log('Momentum breakout (short) detected. State -> MOMENTUM')
                        self.state = MarkofState.MOMENTUM
                        return
                    if self.current_price >= self.entry_price * (1 + self.p.sl_pct):
                        self.log('SL hit on SHORT - closing and resetting')
                        self.order = self.close()
                        self.state = MarkofState.UNDECIDED
                        self.took_partial = False
                        return

        # ---------- CORRECTION ----------
        if self.state == MarkofState.CORRECTION:
            # Means we are in a pullback inside a larger trend and we want to "buy the dip" (or sell the bounce)
            # Only take correction trades in direction of larger trend.
            if uptrend:
                # Wait for oversold-ish RSI and price near EMA1 or EMA2
                near_ema = self.current_price <= self.ema1[0] * (1 + 0.005) and self.current_price >= self.ema1[0] * (1 - 0.02)
                if self.rsi[0] <= self.p.rsi_oversold and near_ema:
                    size = self.p.stake
                    self.log('Placing CORRECTION BUY (buy the dip)')
                    self.order = self.buy(size=size)
                    self.state = MarkofState.TRENDING
                    return
                # if instead price breaks lower strongly -> maybe trend failed -> go MOMENTUM to follow breakout
                if self.recent_low and self.current_price <= self.recent_low * (1 - self.p.breakout_pct):
                    self.log('Correction turned into breakdown -> MOMENTUM state (short)')
                    self.state = MarkofState.MOMENTUM
                    return
            elif downtrend:
                near_ema = self.current_price >= self.ema1[0] * (1 - 0.005) and self.current_price <= self.ema1[0] * (1 + 0.02)
                if self.rsi[0] >= (100 - self.p.rsi_oversold) and near_ema:
                    size = self.p.stake
                    self.log('Placing CORRECTION SELL (sell the bounce)')
                    self.order = self.sell(size=size)
                    self.state = MarkofState.TRENDING_TP
                    return
                if self.recent_high and self.current_price >= self.recent_high * (1 + self.p.breakout_pct):
                    self.log('Correction turned into breakout (long) -> MOMENTUM')
                    self.state = MarkofState.MOMENTUM
                    return

        # ---------- MOMENTUM ----------
        if self.state == MarkofState.MOMENTUM:
            # Follow breakout/momentum aggressively: enter in direction of momentum.
            # For long momentum
            if self.recent_high and self.current_price >= self.recent_high * (1 + self.p.breakout_pct) and self.rsi[0] >= self.p.momentum_rsi and self.macd_hist[0] > self.p.momentum_macd_hist_threshold:
                # close any shorts and buy
                if self.position and self.position.size < 0:
                    self.log('Closing short before momentum long')
                    self.order = self.close()
                    return
                if not self.position:
                    self.log('Entering MOMENTUM LONG')
                    self.order = self.buy(size=self.p.stake * 1.0)
                    # in momentum we expect to ride -- use trailing logic via exit on some conditions
                    return
            # For short momentum
            if self.recent_low and self.current_price <= self.recent_low * (1 - self.p.breakout_pct) and self.rsi[0] <= (100 - self.p.momentum_rsi) and self.macd_hist[0] < -self.p.momentum_macd_hist_threshold:
                if self.position and self.position.size > 0:
                    self.log('Closing long before momentum short')
                    self.order = self.close()
                    return
                if not self.position:
                    self.log('Entering MOMENTUM SHORT')
                    self.order = self.sell(size=self.p.stake * 1.0)
                    return

            # Exit momentum if momentum indicators fade (MACD hist flips sign or RSI drops below threshold)
            if self.position:
                if self.position.size > 0 and (self.macd_hist[0] < 0 or self.rsi[0] < (self.p.momentum_rsi - 10)):
                    self.log('Momentum faded LONG -> closing')
                    self.order = self.close()
                    self.state = MarkofState.UNDECIDED
                    return
                if self.position.size < 0 and (self.macd_hist[0] > 0 or self.rsi[0] > (100 - (self.p.momentum_rsi - 10))):
                    self.log('Momentum faded SHORT -> closing')
                    self.order = self.close()
                    self.state = MarkofState.UNDECIDED
                    return

        # generic safety: if we have a position and it's heavily against us, close
        if self.position:
            if self.position.size > 0:
                if self.current_price <= self.entry_price * (1 - self.p.sl_pct):
                    self.log('Generic SL hit on LONG -> closing')
                    self.order = self.close()
                    self.state = MarkofState.UNDECIDED
                    self.took_partial = False
                    return
            elif self.position.size < 0:
                if self.current_price >= self.entry_price * (1 + self.p.sl_pct):
                    self.log('Generic SL hit on SHORT -> closing')
                    self.order = self.close()
                    self.state = MarkofState.UNDECIDED
                    self.took_partial = False
                    return
