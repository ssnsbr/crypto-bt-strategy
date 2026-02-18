from ._base_condition import Condition
import backtrader as bt


class FixedTPSLCond(Condition):
    """
    Fixed percentage Take Profit and Stop Loss
    Simple risk/reward based exits
    """
    default_params = {
        "tp_pct": 0.02,     # 2% take profit
        "sl_pct": 0.01,     # 1% stop loss
        "use_tp": True,
        "use_sl": True,
    }

    def __init__(self, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)
        self.price = price
        self.entry_price = None

    def get_name(self):
        return f"FixedTPSL(TP:{self.params['tp_pct']*100:.1f}%,SL:{self.params['sl_pct']*100:.1f}%)"

    def set_entry_price(self, price):
        """Call this when entering a position"""
        self.entry_price = price

    def long(self):
        """No entry logic - this is exit-only condition"""
        return False, ""

    def short(self):
        """No entry logic - this is exit-only condition"""
        return False, ""

    def exit_long(self):
        """Exit long on TP or SL"""
        if self.entry_price is None:
            return False, ""

        tp_level = self.entry_price * (1 + self.params["tp_pct"])
        sl_level = self.entry_price * (1 - self.params["sl_pct"])

        tp_hit = self.params["use_tp"] and self.price[0] >= tp_level
        sl_hit = self.params["use_sl"] and self.price[0] <= sl_level

        if tp_hit:
            return True, f"{self.get_name()} TP hit: {self.price[0]:.2f} >= {tp_level:.2f}"
        if sl_hit:
            return True, f"{self.get_name()} SL hit: {self.price[0]:.2f} <= {sl_level:.2f}"

        return False, ""

    def exit_short(self):
        """Exit short on TP or SL"""
        if self.entry_price is None:
            return False, ""

        tp_level = self.entry_price * (1 - self.params["tp_pct"])
        sl_level = self.entry_price * (1 + self.params["sl_pct"])

        tp_hit = self.params["use_tp"] and self.price[0] <= tp_level
        sl_hit = self.params["use_sl"] and self.price[0] >= sl_level

        if tp_hit:
            return True, f"{self.get_name()} TP hit: {self.price[0]:.2f} <= {tp_level:.2f}"
        if sl_hit:
            return True, f"{self.get_name()} SL hit: {self.price[0]:.2f} >= {sl_level:.2f}"

        return False, ""


class ATRBasedTPSLCond(Condition):
    """
    ATR-based Take Profit and Stop Loss
    Adapts to market volatility
    """
    default_params = {
        "atr_period": 14,
        "tp_atr_mult": 2.0,    # TP at 2x ATR
        "sl_atr_mult": 1.0,    # SL at 1x ATR
        "use_tp": True,
        "use_sl": True,
    }

    def __init__(self, data, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = data.close
        self.atr = bt.indicators.ATR(data, period=self.params["atr_period"])
        self.entry_price = None
        self.entry_atr = None

    def get_name(self):
        return f"ATR_TPSL(TP:{self.params['tp_atr_mult']}x,SL:{self.params['sl_atr_mult']}x)"

    def set_entry_price(self, price):
        """Call this when entering a position"""
        self.entry_price = price
        self.entry_atr = self.atr[0]

    def long(self):
        """No entry logic - this is exit-only condition"""
        return False, ""

    def short(self):
        """No entry logic - this is exit-only condition"""
        return False, ""

    def exit_long(self):
        """Exit long on TP or SL based on ATR"""
        if self.entry_price is None or self.entry_atr is None:
            return False, ""

        tp_level = self.entry_price + (self.entry_atr * self.params["tp_atr_mult"])
        sl_level = self.entry_price - (self.entry_atr * self.params["sl_atr_mult"])

        tp_hit = self.params["use_tp"] and self.close[0] >= tp_level
        sl_hit = self.params["use_sl"] and self.close[0] <= sl_level

        if tp_hit:
            return True, f"{self.get_name()} TP hit: {self.close[0]:.2f} >= {tp_level:.2f}"
        if sl_hit:
            return True, f"{self.get_name()} SL hit: {self.close[0]:.2f} <= {sl_level:.2f}"

        return False, ""

    def exit_short(self):
        """Exit short on TP or SL based on ATR"""
        if self.entry_price is None or self.entry_atr is None:
            return False, ""

        tp_level = self.entry_price - (self.entry_atr * self.params["tp_atr_mult"])
        sl_level = self.entry_price + (self.entry_atr * self.params["sl_atr_mult"])

        tp_hit = self.params["use_tp"] and self.close[0] <= tp_level
        sl_hit = self.params["use_sl"] and self.close[0] >= sl_level

        if tp_hit:
            return True, f"{self.get_name()} TP hit: {self.close[0]:.2f} <= {tp_level:.2f}"
        if sl_hit:
            return True, f"{self.get_name()} SL hit: {self.close[0]:.2f} >= {sl_level:.2f}"

        return False, ""


class TrailingStopCond(Condition):
    """
    Trailing Stop Loss - Follows price at fixed distance
    Locks in profits as price moves favorably
    """
    default_params = {
        "trail_pct": 0.02,     # Trail 2% below high water mark
        "activation_pct": 0.01,  # Activate after 1% profit
    }

    def __init__(self, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close
        self.entry_price = None
        self.highest_since_entry = None
        self.lowest_since_entry = None

    def get_name(self):
        return f"TrailStop({self.params['trail_pct']*100:.1f}%)"

    def set_entry_price(self, price):
        """Call this when entering a position"""
        self.entry_price = price
        self.highest_since_entry = price
        self.lowest_since_entry = price

    def long(self):
        """No entry logic - this is exit-only condition"""
        return False, ""

    def short(self):
        """No entry logic - this is exit-only condition"""
        return False, ""

    def exit_long(self):
        """Exit long on trailing stop"""
        if self.entry_price is None:
            return False, ""

        # Update highest price since entry
        if self.close[0] > self.highest_since_entry:
            self.highest_since_entry = self.close[0]

        # Check if trailing stop should be active
        profit_pct = (self.close[0] - self.entry_price) / self.entry_price
        if profit_pct < self.params["activation_pct"]:
            return False, ""  # Not enough profit to activate trailing stop

        # Calculate trailing stop level
        trail_level = self.highest_since_entry * (1 - self.params["trail_pct"])

        if self.close[0] <= trail_level:
            return True, f"{self.get_name()} trailing SL: {self.close[0]:.2f} <= {trail_level:.2f} (HWM: {self.highest_since_entry:.2f})"

        return False, ""

    def exit_short(self):
        """Exit short on trailing stop"""
        if self.entry_price is None:
            return False, ""

        # Update lowest price since entry
        if self.close[0] < self.lowest_since_entry:
            self.lowest_since_entry = self.close[0]

        # Check if trailing stop should be active
        profit_pct = (self.entry_price - self.close[0]) / self.entry_price
        if profit_pct < self.params["activation_pct"]:
            return False, ""  # Not enough profit to activate trailing stop

        # Calculate trailing stop level
        trail_level = self.lowest_since_entry * (1 + self.params["trail_pct"])

        if self.close[0] >= trail_level:
            return True, f"{self.get_name()} trailing SL: {self.close[0]:.2f} >= {trail_level:.2f} (LWM: {self.lowest_since_entry:.2f})"

        return False, ""


class ATRTrailingStopCond(Condition):
    """
    ATR-based Trailing Stop - More adaptive to volatility
    Trails at N * ATR distance
    """
    default_params = {
        "atr_period": 14,
        "atr_mult": 2.0,       # Trail at 2x ATR
        "activation_atr": 1.0,  # Activate after 1x ATR profit
    }

    def __init__(self, data, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = data.close
        self.atr = bt.indicators.ATR(data, period=self.params["atr_period"])

        self.entry_price = None
        self.entry_atr = None
        self.highest_since_entry = None
        self.lowest_since_entry = None

    def get_name(self):
        return f"ATR_TrailStop({self.params['atr_mult']}x)"

    def set_entry_price(self, price):
        """Call this when entering a position"""
        self.entry_price = price
        self.entry_atr = self.atr[0]
        self.highest_since_entry = price
        self.lowest_since_entry = price

    def long(self):
        """No entry logic - this is exit-only condition"""
        return False, ""

    def short(self):
        """No entry logic - this is exit-only condition"""
        return False, ""

    def exit_long(self):
        """Exit long on ATR trailing stop"""
        if self.entry_price is None or self.entry_atr is None:
            return False, ""

        # Update highest price since entry
        if self.close[0] > self.highest_since_entry:
            self.highest_since_entry = self.close[0]

        # Check if trailing stop should be active
        profit = self.close[0] - self.entry_price
        if profit < self.entry_atr * self.params["activation_atr"]:
            return False, ""  # Not enough profit to activate

        # Calculate trailing stop using current ATR
        trail_level = self.highest_since_entry - (self.atr[0] * self.params["atr_mult"])

        if self.close[0] <= trail_level:
            return True, f"{self.get_name()} ATR trailing SL: {self.close[0]:.2f} <= {trail_level:.2f}"

        return False, ""

    def exit_short(self):
        """Exit short on ATR trailing stop"""
        if self.entry_price is None or self.entry_atr is None:
            return False, ""

        # Update lowest price since entry
        if self.close[0] < self.lowest_since_entry:
            self.lowest_since_entry = self.close[0]

        # Check if trailing stop should be active
        profit = self.entry_price - self.close[0]
        if profit < self.entry_atr * self.params["activation_atr"]:
            return False, ""  # Not enough profit to activate

        # Calculate trailing stop using current ATR
        trail_level = self.lowest_since_entry + (self.atr[0] * self.params["atr_mult"])

        if self.close[0] >= trail_level:
            return True, f"{self.get_name()} ATR trailing SL: {self.close[0]:.2f} >= {trail_level:.2f}"

        return False, ""


class SwingTPSLCond(Condition):
    """
    Swing-based TP/SL - Uses recent swing highs/lows
    More aligned with market structure
    """
    default_params = {
        "swing_period": 5,
        "tp_offset_pct": 0.005,  # TP slightly before swing point
        "sl_offset_pct": 0.005,  # SL slightly beyond swing point
        "use_tp": True,
        "use_sl": True,
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close
        self.highest = bt.indicators.Highest(high, period=self.params["swing_period"])
        self.lowest = bt.indicators.Lowest(low, period=self.params["swing_period"])

        self.entry_price = None

    def get_name(self):
        return f"SwingTPSL({self.params['swing_period']})"

    def set_entry_price(self, price):
        """Call this when entering a position"""
        self.entry_price = price

    def long(self):
        """No entry logic - this is exit-only condition"""
        return False, ""

    def short(self):
        """No entry logic - this is exit-only condition"""
        return False, ""

    def exit_long(self):
        """Exit long: TP at swing high, SL at swing low"""
        if self.entry_price is None:
            return False, ""

        # TP at recent swing high (with offset)
        tp_level = self.highest[0] * (1 - self.params["tp_offset_pct"])
        # SL at recent swing low (with offset)
        sl_level = self.lowest[0] * (1 - self.params["sl_offset_pct"])

        tp_hit = self.params["use_tp"] and self.close[0] >= tp_level
        sl_hit = self.params["use_sl"] and self.close[0] <= sl_level

        if tp_hit:
            return True, f"{self.get_name()} TP at swing high: {self.close[0]:.2f} >= {tp_level:.2f}"
        if sl_hit:
            return True, f"{self.get_name()} SL at swing low: {self.close[0]:.2f} <= {sl_level:.2f}"

        return False, ""

    def exit_short(self):
        """Exit short: TP at swing low, SL at swing high"""
        if self.entry_price is None:
            return False, ""

        # TP at recent swing low (with offset)
        tp_level = self.lowest[0] * (1 + self.params["tp_offset_pct"])
        # SL at recent swing high (with offset)
        sl_level = self.highest[0] * (1 + self.params["sl_offset_pct"])

        tp_hit = self.params["use_tp"] and self.close[0] <= tp_level
        sl_hit = self.params["use_sl"] and self.close[0] >= sl_level

        if tp_hit:
            return True, f"{self.get_name()} TP at swing low: {self.close[0]:.2f} <= {tp_level:.2f}"
        if sl_hit:
            return True, f"{self.get_name()} SL at swing high: {self.close[0]:.2f} >= {sl_level:.2f}"

        return False, ""


class RiskRewardTPSLCond(Condition):
    """
    Risk/Reward based TP/SL
    Set SL, calculate TP based on R:R ratio
    """
    default_params = {
        "sl_pct": 0.02,         # 2% stop loss
        "risk_reward": 2.0,     # 1:2 risk/reward (TP = 2x SL distance)
        "use_tp": True,
        "use_sl": True,
    }

    def __init__(self, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.price = price
        self.entry_price = None

    def get_name(self):
        return f"RR_TPSL(SL:{self.params['sl_pct']*100:.1f}%,RR:1:{self.params['risk_reward']:.1f})"

    def set_entry_price(self, price):
        """Call this when entering a position"""
        self.entry_price = price

    def long(self):
        """No entry logic - this is exit-only condition"""
        return False, ""

    def short(self):
        """No entry logic - this is exit-only condition"""
        return False, ""

    def exit_long(self):
        """Exit long with risk/reward based levels"""
        if self.entry_price is None:
            return False, ""

        sl_distance = self.entry_price * self.params["sl_pct"]
        tp_distance = sl_distance * self.params["risk_reward"]

        sl_level = self.entry_price - sl_distance
        tp_level = self.entry_price + tp_distance

        tp_hit = self.params["use_tp"] and self.price[0] >= tp_level
        sl_hit = self.params["use_sl"] and self.price[0] <= sl_level

        if tp_hit:
            return True, f"{self.get_name()} TP hit (1:{self.params['risk_reward']:.1f}): {self.price[0]:.2f} >= {tp_level:.2f}"
        if sl_hit:
            return True, f"{self.get_name()} SL hit: {self.price[0]:.2f} <= {sl_level:.2f}"

        return False, ""

    def exit_short(self):
        """Exit short with risk/reward based levels"""
        if self.entry_price is None:
            return False, ""

        sl_distance = self.entry_price * self.params["sl_pct"]
        tp_distance = sl_distance * self.params["risk_reward"]

        sl_level = self.entry_price + sl_distance
        tp_level = self.entry_price - tp_distance

        tp_hit = self.params["use_tp"] and self.price[0] <= tp_level
        sl_hit = self.params["use_sl"] and self.price[0] >= sl_level

        if tp_hit:
            return True, f"{self.get_name()} TP hit (1:{self.params['risk_reward']:.1f}): {self.price[0]:.2f} <= {tp_level:.2f}"
        if sl_hit:
            return True, f"{self.get_name()} SL hit: {self.price[0]:.2f} >= {sl_level:.2f}"

        return False, ""
