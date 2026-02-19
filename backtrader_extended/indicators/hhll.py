import backtrader as bt
from enum import Enum
import pandas as pd
from backtrader_extended.strategies.Base_Crypto import BaseCryptoTradingStrategy


# class BounceDetectorState:
#     min
#     min_time
#     max
#     max_time
#     extreme
#     extreme_time
#     bounce_list
#     direction = "up"


class BounceDetector:
    def __init__(self):
        self.afterbuy = None

    def detect_bounce(self, current_price, current_time=None, up_bounce_threshold=1.1, down_bounce_threshold=0.9):
        """
        Detects meaningful bounces after the first buy.

        Args:
            current_price: Current price to evaluate
            up_bounce_threshold: Multiplier for upward bounce (1.1 = +10%)
            down_bounce_threshold: Multiplier for downward bounce (0.9 = -10%)

        Returns:
            dict: Current bounce state including bounce_list
        """
        # === Initialize on first call ===
        if self.afterbuy is None:
            self.afterbuy = {
                "min": current_price,
                "min_time": current_time,
                "max": current_price,
                "max_time": current_time,
                "extreme": current_price,  # Last extreme point (top or bottom)
                "extreme_time": current_time,
                "bounce_list": [],
                "direction": None,  # "up" or "down"
            }

        ab = self.afterbuy

        # === Update min/max trackers ===
        if current_price < ab["min"]:
            ab["min"] = current_price
            ab["min_time"] = current_time
        if current_price > ab["max"]:
            ab["max"] = current_price
            ab["max_time"] = current_time
        # ab["min"] = min(ab["min"], current_price)
        # ab["max"] = max(ab["max"], current_price)

        # === Initialize direction on first move ===
        if ab["direction"] is None:
            if current_price > ab["extreme"]:
                ab["direction"] = "up"
            elif current_price < ab["extreme"]:
                ab["direction"] = "down"
            ab["extreme"] = current_price
            ab["extreme_time"] = current_time
            return ab

        # === Track in current direction ===
        if ab["direction"] == "up":
            # Update top if price goes higher
            if current_price > ab["extreme"]:
                ab["extreme"] = current_price
                ab["extreme_time"] = current_time

            # Check for downward bounce (price drops by threshold from top)
            elif current_price / ab["extreme"] <= down_bounce_threshold:
                # Record the completed UP bounce
                prev_bottom = ab["bounce_list"][-1]["end"] if ab["bounce_list"] else ab["min"]
                prev_bottom_time = ab["bounce_list"][-1]["end_time"] if ab["bounce_list"] else ab["min_time"]

                ab["bounce_list"].append({
                    "start_time": prev_bottom_time,
                    "end_time": ab["extreme_time"],
                    "type": "up",
                    "start": prev_bottom,
                    "end": ab["extreme"],
                    "gain": ab["extreme"] / prev_bottom - 1.0,
                })
                # Switch to down direction
                ab["direction"] = "down"
                ab["extreme"] = current_price
                ab["extreme_time"] = current_time

        elif ab["direction"] == "down":
            # Update bottom if price goes lower
            if current_price < ab["extreme"]:
                ab["extreme"] = current_price
                ab["extreme_time"] = current_time

            # Check for upward bounce (price rises by threshold from bottom)
            elif current_price / ab["extreme"] >= up_bounce_threshold:
                # Record the completed DOWN bounce
                prev_top = ab["bounce_list"][-1]["end"] if ab["bounce_list"] else ab["max"]
                prev_top_time = ab["bounce_list"][-1]["end_time"] if ab["bounce_list"] else ab["max_time"]

                ab["bounce_list"].append({
                    "start_time": prev_top_time,
                    "end_time": ab["extreme_time"],
                    "type": "down",
                    "start": prev_top,
                    "end": ab["extreme"],
                    "gain": ab["extreme"] / prev_top - 1.0,
                })
                # Switch to up direction
                ab["direction"] = "up"
                ab["extreme"] = current_price
                ab["extreme_time"] = current_time

        return ab

    def get_state(self):
        return self.afterbuy

    def reset(self):
        """Reset the detector state"""
        self.afterbuy = None


# ==== Enums ====
class TREND(Enum):
    UP = 1
    DOWN = -1
    SIDE = 0


class DIRECTION(Enum):
    WITH_TREND = 1
    CORRECTION = -1
    SIDEWAYS = 0


class PIVOTTYPE(Enum):
    HH = 99
    HL = 91
    LL = 11
    LH = 19
    BU = 2
    BD = 3
    BUMA = 21
    BDMA = 31
    START = 0


# ==== Pivot Struct ====
class Pivot:
    def __init__(self, time, pivot_type: PIVOTTYPE, direction: DIRECTION, trend: TREND, price):
        self.time = time
        self.pivot_type = pivot_type
        self.direction = direction
        self.trend = trend
        self.price = price

    def __repr__(self):
        return f"{self.pivot_type.name}@{self.price:.2f}@{self.time}-T{self.trend}-D{self.direction}"


class FindTrendByBounce:
    def __init__(self):
        self.last_pivot_type = None
        self.trend = TREND.SIDE
        self.direction = DIRECTION.SIDEWAYS
        self.structure = []
        self.main_structure = []
        self.last_processed_bounce = None
        self.current_undetermined_price = None
        self.ma_cross = None

    def _not_new(self, newb):
        if not self.last_processed_bounce:
            return False
        return (
            self.last_processed_bounce["type"] == newb["type"] and
            self.last_processed_bounce["start"] == newb["start"] and
            self.last_processed_bounce["end"] == newb["end"]
        )

    def _update_ma(self, time, price, ma):
        previous_pivot = self.main_structure[-1]
        previous_previous_pivot = self.main_structure[-2]
        ma_value = ma
        _p = None
        if self.ma_cross is None:
            self.ma_cross = 'above' if price > ma_value else 'below'
            return

        if self.ma_cross == 'below' and price > ma_value:
            self.ma_cross = 'above'
            _p = Pivot(time, pivot_type=PIVOTTYPE.BUMA, direction=DIRECTION.WITH_TREND, trend=TREND.UP, price=price)
            self.structure.append(_p)

        elif self.ma_cross == 'above' and price < ma_value:
            self.ma_cross = 'below'
            _p = Pivot(time, pivot_type=PIVOTTYPE.BDMA, direction=DIRECTION.WITH_TREND, trend=TREND.UP, price=price)
            self.structure.append(_p)

    def _update_price(self, time, price):
        previous_pivot = self.main_structure[-1]
        previous_previous_pivot = self.main_structure[-2]

        _p = None
        if self.structure[-1].pivot_type == PIVOTTYPE.BU:
            return
        if self.structure[-1].pivot_type == PIVOTTYPE.BD:
            return

        if previous_pivot.pivot_type == PIVOTTYPE.LL:
            if previous_previous_pivot.price < price:
                # A break out Happened!
                _p = Pivot(time, pivot_type=PIVOTTYPE.BU, direction=DIRECTION.WITH_TREND, trend=TREND.UP, price=price)

        elif previous_pivot.pivot_type == PIVOTTYPE.LH:
            if previous_pivot.price < price:
                # A break out Happened!
                _p = Pivot(time, pivot_type=PIVOTTYPE.BU, direction=DIRECTION.WITH_TREND, trend=TREND.UP, price=price)

        elif previous_pivot.pivot_type == PIVOTTYPE.HH:
            if previous_previous_pivot.price > price:
                # A break out Happened!
                _p = Pivot(time, pivot_type=PIVOTTYPE.BD, direction=DIRECTION.WITH_TREND, trend=TREND.DOWN, price=price)

        elif previous_pivot.pivot_type == PIVOTTYPE.HL:
            if previous_pivot.price > price:
                # A break out Happened!
                _p = Pivot(time, pivot_type=PIVOTTYPE.BD, direction=DIRECTION.WITH_TREND, trend=TREND.DOWN, price=price)
        else:
            print("Warning! This should NOT happen.", previous_pivot.pivot_type)
        if _p:
            print("NEW PIVOT", _p)
            self.structure.append(_p)

    def _update_bounces(self, bounces):

        previous_pivot = self.main_structure[-1]
        previous_previous_pivot = self.main_structure[-2]
        bounce = bounces[-1]
        # Determine New Pivot According to Bounce
        # / + / -> Warning!
        # /
        if (previous_pivot.pivot_type == PIVOTTYPE.HH and bounce["type"] == "up"):
            print("Warning! This should NOT happen. HH, ", bounce)

        if (previous_pivot.pivot_type == PIVOTTYPE.LL and bounce["type"] == "down"):
            print("Warning! This should NOT happen. LL, ", bounce)

        if (previous_pivot.pivot_type == PIVOTTYPE.HL and bounce["type"] == "down"):
            print("Warning! This should NOT happen. HL, ", bounce)

        if (previous_pivot.pivot_type == PIVOTTYPE.LH and bounce["type"] == "up"):
            print("Warning! This should NOT happen. LH, ", bounce)

        if previous_pivot.pivot_type == PIVOTTYPE.LL:
            if previous_previous_pivot.price <= bounce["end"]:
                # A break out Happened!
                p = Pivot(bounce["end_time"], pivot_type=PIVOTTYPE.HH, direction=DIRECTION.WITH_TREND, trend=TREND.UP, price=bounce["end"])
            else:
                # Normal correction
                p = Pivot(bounce["end_time"], pivot_type=PIVOTTYPE.LH, direction=DIRECTION.CORRECTION, trend=TREND.DOWN, price=bounce["end"])

        elif previous_pivot.pivot_type == PIVOTTYPE.LH:
            if previous_previous_pivot.price >= bounce["end"]:
                # Normal Trend
                p = Pivot(bounce["end_time"], pivot_type=PIVOTTYPE.LL, direction=DIRECTION.WITH_TREND, trend=TREND.DOWN, price=bounce["end"])
            else:
                # Werid correction
                p = Pivot(bounce["end_time"], pivot_type=PIVOTTYPE.HL, direction=DIRECTION.CORRECTION, trend=TREND.UP, price=bounce["end"])

        elif previous_pivot.pivot_type == PIVOTTYPE.HH:
            if previous_previous_pivot.price >= bounce["end"]:
                # A break out Happened!
                p = Pivot(bounce["end_time"], pivot_type=PIVOTTYPE.LL, direction=DIRECTION.WITH_TREND, trend=TREND.DOWN, price=bounce["end"])
            else:
                # Normal correction
                p = Pivot(bounce["end_time"], pivot_type=PIVOTTYPE.HL, direction=DIRECTION.CORRECTION, trend=TREND.UP, price=bounce["end"])

        elif previous_pivot.pivot_type == PIVOTTYPE.HL:
            if previous_previous_pivot.price <= bounce["end"]:
                # Normal Trend
                p = Pivot(bounce["end_time"], pivot_type=PIVOTTYPE.HH, direction=DIRECTION.WITH_TREND, trend=TREND.UP, price=bounce["end"])
            else:
                # Werid correction
                p = Pivot(bounce["end_time"], pivot_type=PIVOTTYPE.LH, direction=DIRECTION.CORRECTION, trend=TREND.DOWN, price=bounce["end"])
        else:
            print("Warning! This should NOT happen.", previous_pivot.pivot_type)
        print("NEW PIVOT", p)
        self.structure.append(p)
        self.main_structure.append(p)
        return

    def update(self, bounce_state, time, price, ma=None):
        bounces = bounce_state.get("bounce_list", [])
        if not bounces:
            return

        if len(bounces) == 1 and not self.last_processed_bounce:
            b = bounces[0]
            print(b)
            self.last_processed_bounce = b
            if b["type"] == "up":
                p = Pivot(min(b["start_time"], b["end_time"]), PIVOTTYPE.START, DIRECTION.WITH_TREND, TREND.UP, b["start"])
                self.structure.append(p)
                self.main_structure.append(p)
                print("NEW PIVOT", p)
                p = Pivot(max(b["start_time"], b["end_time"]), PIVOTTYPE.HH, DIRECTION.WITH_TREND, TREND.UP, b["end"])
                self.structure.append(p)
                self.main_structure.append(p)
                print("NEW PIVOT", p)

            else:
                p = (Pivot(min(b["start_time"], b["end_time"]), PIVOTTYPE.START, DIRECTION.WITH_TREND, TREND.DOWN, b["start"]))
                self.structure.append(p)
                self.main_structure.append(p)
                print("NEW PIVOT", p)
                p = (Pivot(max(b["start_time"], b["end_time"]), PIVOTTYPE.LL, DIRECTION.WITH_TREND, TREND.DOWN, b["end"]))
                self.structure.append(p)
                self.main_structure.append(p)
                print("NEW PIVOT", p)
            print("saved start!")
            self.current_undetermined_price = b["end"]
            return

        if ma:
            self._update_ma(time, price, ma)

        if self._not_new(bounces[-1]):
            self._update_price(time, price)
            return
        else:
            self.last_processed_bounce = bounces[-1]
            if self.current_undetermined_price != bounces[-1]["start"]:
                self.current_undetermined_price = bounces[-1]["end"]
                print("Warning! This should NOT happen.", "End is not START!", self.current_undetermined_price, "!=", bounces[-1]["start"])
            self.current_undetermined_price = bounces[-1]["end"]
            self._update_bounces(bounces)

        return

    def get_trend(self):
        return self.trend

    def get_structure(self):
        return self.structure

    def get_main_structure(self):
        return self.main_structure


# ==== Indicator Wrapper ====
class BounceTrendIndicator(bt.Indicator):
    lines = ('trend',)
    plotinfo = dict(plot=True, subplot=False)
    plotlines = dict(trend=dict(color='blue', _name='Trend'))

    params = dict(
        up_bounce_threshold=1.01,
        down_bounce_threshold=0.99
    )

    def __init__(self):
        self.bd = BounceDetector()
        self.ft = FindTrendByBounce()
        self.ma = bt.indicators.SimpleMovingAverage(self.data, period=50)

    def next(self):
        price = self.data[0]
        state = self.bd.detect_bounce(price, self.data.datetime.datetime(0),
                                      up_bounce_threshold=self.p.up_bounce_threshold,
                                      down_bounce_threshold=self.p.down_bounce_threshold)

        self.ft.update(state, self.data.datetime.datetime(0), price, self.ma[0])

        structure = self.ft.get_structure()
        if structure:
            last_pivot = structure[-1]
            self.lines.trend[0] = 1 if last_pivot.trend == TREND.UP else -1
        else:
            self.lines.trend[0] = 0

    def get_pivots(self):
        st = self.ft.get_structure()
        return [(p.time, p.price, p.pivot_type.name) for p in self.ft.get_structure()]


# ==== Simple Test Strategy ====
class TestStrategy(BaseCryptoTradingStrategy):
    def __init__(self):
        super().__init__()
        self.bt_indicator = BounceTrendIndicator(self.data)
        self.results = {
            "l": [],
            "s": []
        }

    def next(self):
        trend = self.bt_indicator.trend[0]
        dt = self.data.datetime.datetime(0)
        ps = self.bt_indicator.get_pivots()
        self.results["s"] = (pd.unique(ps))
        self.results["l"].append((dt, self.data.close[0], trend, ps[-1] if len(ps) > 0 else None))
        # print(f"{self.data.datetime.date(0)} | Price={self.data[0]:.2f} | Trend={trend}")


all_results_df, all_cerebros_objects, all_portfolio_histories = run_me(TestStrategy, 2000)


# ==== Indicator Wrapper ====
class BounceTrendIndicator(bt.Indicator):
    lines = ('trend',)
    plotinfo = dict(plot=True, subplot=False)
    plotlines = dict(trend=dict(color='blue', _name='Trend'))

    params = dict(
        up_bounce_threshold=1.01,
        down_bounce_threshold=0.99
    )

    def __init__(self):
        self.bd = BounceDetector()
        self.ft = FindTrendByBounce()

    def next(self):
        price = self.data[0]
        state = self.bd.detect_bounce(price, self.data.datetime.datetime(0),
                                      up_bounce_threshold=self.p.up_bounce_threshold,
                                      down_bounce_threshold=self.p.down_bounce_threshold)
        self.ft.update(state, self.data.datetime.datetime(0), price)
        structure = self.ft.get_structure()
        if structure:
            last_pivot = structure[-1]
            self.lines.trend[0] = 1 if last_pivot.trend == TREND.UP else -1
        else:
            self.lines.trend[0] = 0

    def get_pivots(self):
        st = self.ft.get_structure()
        return [(p.time, p.price, p.pivot_type.name) for p in self.ft.get_structure()]


# ==== Simple Test Strategy ====
class TestStrategy(BaseCryptoTradingStrategy):
    def __init__(self):
        super().__init__()
        self.bt_indicator = BounceTrendIndicator(self.data)
        self.results = {
            "l": [],
            "s": []
        }

    def next(self):
        trend = self.bt_indicator.trend[0]
        dt = self.data.datetime.datetime(0)
        ps = self.bt_indicator.get_pivots()
        self.results["s"] = (pd.unique(ps))
        self.results["l"].append((dt, self.data.close[0], trend, ps[-1] if len(ps) > 0 else None))
        # print(f"{self.data.datetime.date(0)} | Price={self.data[0]:.2f} | Trend={trend}")


all_results_df, all_cerebros_objects, all_portfolio_histories = run_me(TestStrategy, 1000)
