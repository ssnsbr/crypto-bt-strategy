

from enum import Enum


class ActionType(str, Enum):
    BUY = "buy"
    INITIAL_BUY = "INITIAL_BUY"
    BUY_AGAIN = "BUY_AGAIN"
    SELL = "SELL"
    SELL_BFM = "SELL_BFM"
    SELL_TP = "SELL_TP"
    SELL_SL = "SELL_SL"


class IndicatorCondition:
    def __init__(self, strategy, initail_buy=False, buy_again=False, sell_tp=False, sell_sl=False, sell_bfm=False):
        self.strategy = strategy
        self.initail_buy = initail_buy
        self.buy_again = buy_again
        self.sell_tp = sell_tp
        self.sell_sl = sell_sl
        self.sell_bfm = sell_bfm

    def check(self, action: ActionType) -> bool:
        raise NotImplementedError


class RSICondition(IndicatorCondition):

    def check(self, action: ActionType) -> bool:

        rsi_value = self.strategy.rsi[0]

        if action in (ActionType.INITIAL_BUY, ActionType.BUY_AGAIN):
            return rsi_value < self.strategy.p.rsi_thr

        if action == ActionType.SELL:
            return rsi_value > self.strategy.p.rsi_thr

        return True


class LivelinessCondition(IndicatorCondition):

    def check(self, action: ActionType) -> bool:
        # ----------- On liveliness, -1 = liveliness is off.
        # if self.p.use_liveliness[0]:
        #     liveliness_cond = self.liveliness > self.p.min_liveliness_for_ba
        # else:
        #     liveliness_cond = True

        if not self.initail_buy:
            return True

        return self.strategy.liveliness > self.strategy.p.min_liveliness_for_ba


class StochasticCondition(IndicatorCondition):

    def check(self, action: ActionType) -> bool:
        s = self.strategy

        # --- Stochastic ---
        # if self.p.use_stoch[0]:
        #     stoch_k = self.stoch.percK
        #     stoch_d = self.stoch.percD
        #     stoch_cond = (stoch_k < self.p.STOCH_buy_threshold) and (stoch_k > stoch_d)
        #     # e.g. below 20 but %K crossing up %D
        # # === Combine all conditions ===
        k = s.stoch.percK[0]
        d = s.stoch.percD[0]

        # if action in (ActionType.INITIAL_BUY, ActionType.BUY_AGAIN):
        #     return k < s.p.stoch_buy_threshold and k > d

        # if action == ActionType.SELL:
        #     return k > 80 and k < d

        return True


class EMACondition(IndicatorCondition):

    # def _tema_cond(self,cond_for="ib"):
    #     _cond = True
    #     if actiontype == "ib" and self.p.use_tema[0]:
    #         _cond = self.current_price > self.tema
    #     if actiontype == "ba" and self.p.use_tema[1]:
    #         _cond = self.current_price > self.tema
    #     if actiontype == "sell" and self.p.use_tema[2]:
    #         _cond = self.current_price < self.tema
    #     return _cond

    # def _dema_cond(self,cond_for="ib"):
    #     _cond = True
    #     if actiontype == "ib" and self.p.use_dema[0]:
    #         _cond = self.current_price > self.dema
    #     if actiontype == "ba" and self.p.use_dema[1]:
    #         _cond = self.current_price > self.dema
    #     if actiontype == "sell" and self.p.use_dema[2]:
    #         _cond = self.current_price < self.dema
    #     return _cond

    # --- EMA ---
    # if self.p.use_ema[0]:
    #     ema_cond = self.current_price > self.ema * (1 - self.p.EMA_tolerance)
    # use 0.01 tolerance for 1% under EMA allowed
    def check(self, action: ActionType) -> bool:
        s = self.strategy

        ema_value = s.ema[0]
        price = s.current_price

        tolerance = s.p.EMA_tolerance

        if action in (ActionType.INITIAL_BUY, ActionType.BUY_AGAIN):
            return price > ema_value * (1 - tolerance)

        if action == ActionType.SELL:
            return price < ema_value

        return True


class MACDCondition(IndicatorCondition):

    # def _macd_cond(self,cond_for="ib"):
    #     macd_cond = True
    #     if actiontype == "ib" and self.p.use_macd[0]:
    #         macd_line = self.macd.macd[0]
    #         signal_line = self.macd.signal[0]
    #         macd_cond =  (macd_line > signal_line) or macd_line > 0
    #         # ((macd_line > 0) and (signal_line > 0)) or

    #     if actiontype == "ba" and self.p.use_macd[1]:
    #         macd_line = self.macd.macd[0]
    #         signal_line = self.macd.signal[0]
    #         macd_cond =  (macd_line > signal_line) or macd_line > 0
    #         # ((macd_line > 0) and (signal_line > 0)) or

    #     if actiontype == "sell" and self.p.use_macd[2]:
    #         pass
    #     return macd_cond
    def check(self, action: ActionType) -> bool:
        # macd_5X_hist = self.macd_5X.macd[0] - self.macd_5X.signal[0]
        # return macd_5X_hist > 0
        # # --- MACD ---
        # if self.p.use_macd[0]:
        #     macd_line = self.macd.macd[0]
        #     signal_line = self.macd.signal[0]
        #     macd_cond = (macd_line > 0) and (signal_line > 0) and (macd_line > signal_line)

        s = self.strategy

        macd_line = s.macd.macd[0]
        signal_line = s.macd.signal[0]

        if action in (ActionType.INITIAL_BUY, ActionType.BUY_AGAIN):
            return macd_line > signal_line

        if action == ActionType.SELL:
            return macd_line < signal_line

        return True


class DownFallCondition(IndicatorCondition):

    def check(self, action: ActionType) -> bool:
        # no_buy_on_down_fall = False -> down_fall_cond=False -> not down_fall_cond= True
        # no_buy_on_down_fall = True -> self.is_on_down_fall=False -> not down_fall_cond= True
        # no_buy_on_down_fall = True -> self.is_on_down_fall=True -> not down_fall_cond= False
        _d1 = self.p.use_down_fall and self.is_on_down_fall()
        down_fall_cond = not _d1
        # if not self.strategy.p.use_rsi[action.value]:
        #     return True

        # rsi_value = self.strategy.rsi[0]

        # if action in (ActionType.INITIAL_BUY, ActionType.BUY_AGAIN):
        #     return rsi_value < self.strategy.p.rsi_thr

        # if action == ActionType.SELL:
        #     return rsi_value > self.strategy.p.rsi_thr

        return down_fall_cond


class BounceCondition(IndicatorCondition):
    # Detect if a local bounce of at least X% happened since first buy

    def detect_bounce(self, current_price, up_bounce_threshold=1.1, down_bounce_threshold=0.9):
        # TODO for not buying again
        pass

    def check(self, action: ActionType) -> bool:
        # if not self.strategy.p.use_rsi[action.value]:
        #     return True

        # rsi_value = self.strategy.rsi[0]

        # if action in (ActionType.INITIAL_BUY, ActionType.BUY_AGAIN):
        #     return rsi_value < self.strategy.p.rsi_thr

        # if action == ActionType.SELL:
        #     return rsi_value > self.strategy.p.rsi_thr

        return True


class IndicatorEngine:

    def __init__(self, strategy):
        self.conditions = list[IndicatorCondition]
        param = strategy.p.use_rsi
        self.rsi_cond = RSICondition(strategy, initail_buy=param[0], buy_again=param[1], sell_tp=param[2], sell_sl=param[3], sell_bfm=param[4]),
        param = strategy.p.use_macd
        self.macd_cond = MACDCondition(strategy, initail_buy=param[0], buy_again=param[1], sell_tp=param[2], sell_sl=param[3], sell_bfm=param[4]),
        param = strategy.p.use_ema
        self.ema_condtion = EMACondition(strategy, initail_buy=param[0], buy_again=param[1], sell_tp=param[2], sell_sl=param[3], sell_bfm=param[4]),
        param = strategy.p.use_stochastic
        self.stochastic_cond = StochasticCondition(strategy, initail_buy=param[0], buy_again=param[1], sell_tp=param[2], sell_sl=param[3], sell_bfm=param[4]),
        param = strategy.p.use_liveliness
        self.liveliness_cond = LivelinessCondition(strategy, initail_buy=param[0], buy_again=param[1], sell_tp=param[2], sell_sl=param[3], sell_bfm=param[4]),
        param = strategy.p.use_down_fall
        self.downfall_cond = LivelinessCondition(strategy, initail_buy=param[0], buy_again=param[1], sell_tp=param[2], sell_sl=param[3], sell_bfm=param[4]),
        param = strategy.p.use_bounce
        self.bounce_cond = BounceCondition(strategy, initail_buy=param[0], buy_again=param[1], sell_tp=param[2], sell_sl=param[3], sell_bfm=param[4]),

        self.conditions = [
            self.rsi_cond,
            self.macd_cond,
            self.ema_condtion,
            self.stochastic_cond,
            self.liveliness_cond,
            self.downfall_cond,
            self.bounce_cond,
        ]

    def add_indicator(self, condition: IndicatorCondition):
        self.conditions.append(condition)

    def check(self, action: ActionType) -> bool:
        # print("Checking indicators...", action,self.conditions)
        for condition in self.conditions:
            # print("Checking condition:", condition)
            if not condition[0].check(action):
                return False
        return True
