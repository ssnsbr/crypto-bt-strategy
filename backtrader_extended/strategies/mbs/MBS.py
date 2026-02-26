

from backtrader_extended.strategies.mbs.MBS_Conditions import ActionType, IndicatorEngine
from backtrader_extended.strategies.mbs.MBS_Utils import BaseMBSUTILS
from indicators.bounce_detector import BounceDetector
from indicators.liveliness_tracker import LivelinessTracker
import backtrader as bt

from utils.utils import format_marketcap


class MBS(BaseMBSUTILS):

    params = (
        ('log', True),
        ('tp', 1.2),                # Take profit at 120% of avg price
        ('sl', 0.7),
        ('buy_again', 0.8),         # Buy again at 70% of avg/last price
        ("add_dynamic_ba", 0.05),
        ('buy_again_from_top', False),
        ('max_buy_count', 4),
        ('end_mcap', 20_000),
        ('min_ib_mcap', 20_000),
        ('min_ba_mcap', 19_000),
        #
        ('dead_coin_market_cap', 9_000),
        ('migration_market_cap', 125_000),
        ('buy_again_avg', 1),   # Buy again when avg/last is less than buy_again of current price
        ('sell_tp_on_avg', 1),  # sell tp on avg/last
        ('sell_sl_on_avg', 1),  # sell tp on avg/last
        ("sell_on_no_loss", False),
        #
        # ('use_indicator', [initial_buy, buy_again, sell_tp, sell_sl, sell_custom]),
        ('DEMA_p', 300),
        ('use_dema', [False, False, False, False, False]),
        ('TEMA_p', 300),
        ('use_tema', [False, False, False, False, False]),
        ('MACD_p', [12, 26, 9]),
        ('MACD_2X', [30, 65, 23]),
        ('MACD_5X', [60, 130, 45]),
        ('use_macd', [False, False, False, False, False]),
        ('EMA_p', 60),
        ("EMA_tolerance", 0.1),
        ('use_ema', [False, False, False, False, False]),
        ('RSI_p', 60),
        ("rsi_thr", 50),
        ('use_rsi', [False, False, False, False, False]),
        ("liveliness_w", 120),
        ("min_liveliness_for_ba", 0.4),
        ('use_liveliness', [False, False, False, False, False]),
        ('STOCH_p', [60, 15, 15]),
        ("stoch_buy_threshold", 20),
        ('use_stochastic', [False, False, False, False, False]),
        ('uncatch_bounce_tp', 1.2),
        ("sell_on_current_bounce_from_min", 1.5),
        ("bounce_threshold_minor", [1.25, 0.75]),
        ("bounce_threshold", [1.5, 0.5]),
        ('use_bounce', [False, False, False, False, False]),
        ('use_down_fall', [False, False, False, False, False]),
        ("buy_after_bounce_down", [-0.3, 1.1, "down"]),
    )

    def __init__(self):
        super().__init__()

        self.rsi = bt.indicators.RSI_Safe(self.datas[0].close, period=self.p.RSI_p)
        self.ema = bt.indicators.EMA(self.datas[0].close, period=self.p.EMA_p)
        self.macd = bt.indicators.MACD(self.datas[0].close, period_me1=self.p.MACD_p[0], period_me2=self.p.MACD_p[1], period_signal=self.p.MACD_p[2])
        self.stoch = bt.indicators.StochasticFull(self.datas[0], period=self.p.STOCH_p[0], period_dfast=self.p.STOCH_p[1], period_dslow=self.p.STOCH_p[2])
        self.tema = bt.indicators.TEMA(self.datas[0].close, period=self.p.TEMA_p)
        self.dema = bt.indicators.DEMA(self.datas[0].close, period=self.p.DEMA_p)
        self.liveliness_tracker = LivelinessTracker(window=self.p.liveliness_w)
        self.macd_5X = bt.indicators.MACD(self.datas[0].close, period_me1=self.p.MACD_5X[0], period_me2=self.p.MACD_5X[1], period_signal=self.p.MACD_5X[2])
        self.macd = self.macd_5X

        self.done = False

        self.min_wait_before_buy = 2
        self.min_wait_before_sell = 2

        self.minorBounceDetector = BounceDetector(up_bounce_threshold=self.p.bounce_threshold_minor[0], down_bounce_threshold=self.p.bounce_threshold_minor[1])
        self.bounceDetector = BounceDetector(up_bounce_threshold=self.p.bounce_threshold[0], down_bounce_threshold=self.p.bounce_threshold[1])
        self.bounce_state = None
        self.indicator_engine = IndicatorEngine(self)

    def is_bounce_down(self):
        state = self.bounceDetector.get_state()
        if state is None:
            return False
        if len(state["bounce_list"]) < 2:
            return False
        # /\  down -0.5
        #   \/ 0.1 up
        last_bounce = state["bounce_list"][-1]
        current_min = state["min"]
        current_max = state["extreme"]
        r = current_max / current_min
        last_size_cond = last_bounce["gain"] < self.params.buy_after_bounce_down[0]
        current_b_cond = r > self.params.buy_after_bounce_down[1]
        last_type_cond = self.params.buy_after_bounce_down[2] == last_bounce["type"]
        # print("r", r, f"= {format_marketcap(current_max)} / {format_marketcap(current_min) }", "last_bounce gain", last_bounce["gain"], "last_type", last_bounce["type"])
        # print(last_type_cond, current_b_cond, last_size_cond)
        # print(state)

        if last_type_cond and current_b_cond and last_size_cond:
            return True
        return False

    def init_buy_cond(self):
        ib_cond = self.current_price > self.p.min_ib_mcap
        indicator_cond = self.indicator_engine.check(ActionType.INITIAL_BUY)
        return not self.in_position and not self.buy_wait() and ib_cond and indicator_cond

    def tp_cond(self):
        sell_cond_tp = False
        if self.in_position and not self.sell_wait():
            sell_cond_tp = self.current_price > self.targets["tp"]
        indicator_cond = self.indicator_engine.check(ActionType.SELL_TP)
        return sell_cond_tp and indicator_cond

    def sl_cond(self):
        # --- S2: Defeat Stop ---
        defeat_con_1 = self.buy_counter >= self.p.max_buy_count
        defeat_con_2 = self.current_price < self.targets["sl"]
        indicator_cond = self.indicator_engine.check(ActionType.SELL_SL)
        return self.in_position and defeat_con_1 and defeat_con_2 and not self.sell_wait() and indicator_cond

    def ba_cond(self):
        # --- B2: Averaging Down ---
        buy_price_cond = self.current_price < self.targets["ba"]
        _buy_counter_cond = self.buy_counter < self.p.max_buy_count
        indicator_cond = self.indicator_engine.check(ActionType.BUY_AGAIN)
        return self.in_position and indicator_cond and _buy_counter_cond and buy_price_cond

    def exit_signal_cond(self):
        indicator_cond = self.indicator_engine.check(ActionType.SELL_CUSTOM)
        return self.in_position and indicator_cond

    def _execute_trading_logic(self):
        # Update Custom Indicators
        # self.update_zz()
        self.bounce_state = self.bounceDetector.detect_bounce(self.current_price)
        # self.analyze_bounces(self.bounce_state["bounce_list"])

        if not self.migrated or self.done:
            return

        self.liveliness_tracker.update(self.current_price)
        self.liveliness = self.liveliness_tracker.get_liveliness()

        self.in_position = self.getposition(self.datas[0]).size > 0
        if self.in_position:
            if self.min_after_buy == 0:
                self.min_after_buy = self.current_price
            else:
                self.min_after_buy = min(self.min_after_buy, self.current_price)
            self.max_after_buy = max(self.max_after_buy, self.current_price)

        # self.indicator_engine.update()
        # --- B1: Initial Buy ---
        if self.init_buy_cond() and self.is_bounce_down():
            self.init_buy()
            return

        # --- B2: Averaging Down ---
        if self.ba_cond() and self.is_bounce_down():
            self.order = self.again_buy()
            return

        # --- NEWSell cs: Custom Sell
        if self.exit_signal_cond():
            self.sell_custom()
            return

        # --- NEWSell SnL: sell_on_no_loss
        if self.in_position and not self.sell_wait():
            if self.p.sell_on_no_loss and self.buy_counter != 1 and self.buy_counter != 0:
                if self.current_price > self.portfolio_avg_buy_price:
                    self.sell_no_loss()

        # --- NEWSell SnL: sell_on_no_loss
        if self.in_position and not self.sell_wait():
            if self.p.sell_on_no_loss and self.buy_counter != 1 and self.buy_counter != 0:
                if self.current_price > self.portfolio_avg_buy_price:
                    self.sell_no_loss()

        # --- S1: TP ---
        if self.tp_cond():
            self.sell_tp()
            return

        # --- S2: Defeat Stop ---
        if self.sl_cond():
            self.sell_sl()
            return

        # --- Z: END ---
        if self.in_position and self.current_price < self.p.end_mcap:
            self.log(f'Dead Coin SELL: {self.current_marketcap_str}')
            self.order = self.close()
            self.buy_counter *= -1
            self.add_to_list("d")
            self.done = True
            return


class After_MBS(MBS):
    pass
