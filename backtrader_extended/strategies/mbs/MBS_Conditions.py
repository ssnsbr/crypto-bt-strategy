

from enum import Enum


class ActionType(str, Enum):
    BUY = "buy"
    INITIAL_BUY = "INITIAL_BUY"
    BUY_AGAIN = "BUY_AGAIN"
    SELL = "SELL"
    SELL_CUSTOM = "SELL_CUSTOM"
    SELL_TP = "SELL_TP"
    SELL_SL = "SELL_SL"


class IndicatorCondition:
    def __init__(self, strategy, initail_buy=False, buy_again=False, sell_tp=False, sell_sl=False, sell_custom=False):
        self.strategy = strategy
        self.initail_buy = initail_buy
        self.buy_again = buy_again
        self.sell_tp = sell_tp
        self.sell_sl = sell_sl
        self.sell_custom = sell_custom

    def b_cond(self):
        return True

    def s_cond(self):
        return True

    def ib_cond(self):
        return True

    def ba_cond(self):
        return True

    def sl_cond(self):
        return True

    def tp_cond(self):
        return True

    def custom_cond(self):
        return True

    def check(self, action: ActionType) -> bool:
        if action == ActionType.INITIAL_BUY:
            if not self.initail_buy:
                return True
            return self.ib_cond() and self.b_cond()

        if action == ActionType.BUY_AGAIN:
            if not self.buy_again:
                return True
            return self.ba_cond() and self.b_cond()

        if action == ActionType.SELL_SL:
            if not self.sell_sl:
                return True
            return self.sl_cond() and self.s_cond()

        if action == ActionType.SELL_TP:
            if not self.sell_tp:
                return True
            return self.tp_cond() and self.s_cond()

        if action == ActionType.SELL_CUSTOM:
            if not self.sell_custom:
                return False
            return self.custom_cond() and self.s_cond()

        if action == ActionType.SELL:
            return self.s_cond()

        if action == ActionType.BUY:
            return self.b_cond()

        print("Unknown action: ", action)
        return True


class RSICondition(IndicatorCondition):
    def __init__(self, rsi_thr, **kwarg):
        super().__init__(**kwarg)
        self.rsi_thr = rsi_thr

    def b_cond(self):
        return self.strategy.rsi[0] < self.rsi_thr

    def s_cond(self):
        return self.strategy.rsi[0] > self.rsi_thr


class LivelinessCondition(IndicatorCondition):
    def __init__(self, min_liveliness_for_ba=0, **kwarg):
        super().__init__(**kwarg)
        self.min_liveliness_for_ba = min_liveliness_for_ba

    # def ib_cond(self):
    #     liveliness_cond = self.liveliness > min_liveliness_for_ba
    #     return liveliness_cond


class StochasticCondition(IndicatorCondition):
    def __init__(self, stoch_buy_threshold=20, stoch_sell_threshold=80, **kwarg):
        super().__init__(**kwarg)
        self.stoch_buy_threshold = stoch_buy_threshold
        self.stoch_sell_threshold = stoch_sell_threshold

    def b_cond(self):
        stoch_k = self.strategy.stoch.percK[0]
        stoch_d = self.strategy.stoch.percD[0]
        # e.g. below 20 but %K crossing up %D
        stoch_cond = (stoch_k < self.stoch_buy_threshold) and (stoch_k > stoch_d)
        return stoch_cond

    def s_cond(self):
        stoch_k = self.strategy.stoch.percK[0]
        stoch_d = self.strategy.stoch.percD[0]
        # e.g. below 20 but %K crossing up %D
        stoch_cond = (stoch_k > self.stoch_sell_threshold) and (stoch_k < stoch_d)
        return stoch_cond


class TEMACondition(IndicatorCondition):
    def __init__(self, tolerance=0, **kwarg):
        super().__init__(**kwarg)
        # use 0.01 tolerance for 1% under EMA allowed
        self.tolerance = tolerance

    def b_cond(self):
        _value = self.strategy.tema[0]
        price = self.strategy.current_price
        _cond = price > _value * (1 - self.tolerance)
        return _cond

    def s_cond(self):
        _value = self.strategy.tema[0]
        price = self.strategy.current_price
        _cond = price < _value * (1 - self.tolerance)
        return _cond


class MACDCondition(IndicatorCondition):

    def b_cond(self):
        macd_line = self.strategy.macd.macd[0]
        signal_line = self.strategy.macd.signal[0]
        macd_cond = (macd_line > signal_line) or macd_line > 0
        # ((macd_line > 0) and (signal_line > 0)) or
        return macd_cond


class BounceCondition(IndicatorCondition):
    # Detect if a local bounce of at least X% happened since first buy
    def s_cond(self) -> bool:
        c = self.current_bounce_from_min() > self.strategy.p.sell_on_current_bounce_from_min
        if c:
            print("BounceCondition", self.current_bounce_from_min(), self.strategy.current_price, self.strategy.min_after_buy)
        return c

    def were_there_uncatched_bounce(self):
        # 100ib-80ba-64ba-(50ba,76tp)-55-66
        # here it gave a bounce which we did not catch
        # Should I exit?
        if (self.strategy.current_price / self.strategy.min_after_buy) > self.strategy.p.uncatch_bounce_tp:
            print("uncatched BOUNCE UP!")
            return True

    def current_bounce_from_min(self):
        if self.strategy.min_after_buy != 0:
            return (self.strategy.current_price / self.strategy.min_after_buy)
        else:
            return 1


class DownFallCondition(IndicatorCondition):
    # Detect if a local bounce of at least X% happened since first buy
    def __init__(self, bounceDetector, **kwarg):
        super().__init__(**kwarg)
        self.bounceDetector = bounceDetector

    def ba_cond(self) -> bool:
        down_fall_cond = not self.is_on_down_fall()
        return down_fall_cond

    def is_on_down_fall(self):
        state = self.bounceDetector.get_state()
        b_counter = 0

        if state is None:
            return True
        if len(state["bounce_list"]) > self.strategy.buy_counter - 1:
            for b in state["bounce_list"]:
                if b["type"] == "up":
                    b_counter += 1
            if b_counter > self.strategy.buy_counter - 1:
                return False
            return True
        else:
            return True


class IndicatorEngine:

    def __init__(self, strategy):
        self.conditions = list[IndicatorCondition]
        param = strategy.p.use_rsi
        self.rsi_cond = RSICondition(rsi_thr=strategy.p.rsi_thr, strategy=strategy, initail_buy=param[0], buy_again=param[1], sell_tp=param[2], sell_sl=param[3], sell_custom=param[4])
        param = strategy.p.use_macd
        self.macd_cond = MACDCondition(strategy=strategy, initail_buy=param[0], buy_again=param[1], sell_tp=param[2], sell_sl=param[3], sell_custom=param[4])
        param = strategy.p.use_ema
        self.ema_condtion = TEMACondition(strategy=strategy, initail_buy=param[0], buy_again=param[1], sell_tp=param[2], sell_sl=param[3], sell_custom=param[4])
        param = strategy.p.use_stochastic
        self.stochastic_cond = StochasticCondition(strategy=strategy, initail_buy=param[0], buy_again=param[1], sell_tp=param[2], sell_sl=param[3], sell_custom=param[4])
        param = strategy.p.use_liveliness
        self.liveliness_cond = LivelinessCondition(strategy=strategy, initail_buy=param[0], buy_again=param[1], sell_tp=param[2], sell_sl=param[3], sell_custom=param[4])
        param = strategy.p.use_down_fall
        self.downfall_cond = DownFallCondition(bounceDetector=strategy.bounceDetector, strategy=strategy, initail_buy=param[0], buy_again=param[1], sell_tp=param[2], sell_sl=param[3], sell_custom=param[4])
        param = strategy.p.use_bounce
        self.bounce_cond = BounceCondition(strategy=strategy, initail_buy=param[0], buy_again=param[1], sell_tp=param[2], sell_sl=param[3], sell_custom=param[4])

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
            if not condition.check(action):
                # print("IndicatorEngine check", "False", action)
                return False
        # print("IndicatorEngine check", "True", action)
        return True
