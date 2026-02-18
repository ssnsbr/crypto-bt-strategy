
from ._base_condition import Condition
import backtrader as bt


class HighLowSwingCond(Condition):
    """
    Mean reversion strategy:
    - Enter LONG when price hits swing low
    - Exit LONG at SL (below low) or TP (above high)
    """
    default_params = {
        "period": 5,
        "entry_offset": 0.0,   # How close to swing point to enter
        "sl_offset": 0.01,     # 1% below low for long SL
        "tp_offset": 0.01,     # 1% above high for long TP
        "use_sl": True,
        "use_tp": True,
    }

    def __init__(self, high, low, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)
        self.price = price
        self.high = high
        self.low = low
        self.highest = bt.indicators.Highest(high, period=self.params["period"])
        self.lowest = bt.indicators.Lowest(low, period=self.params["period"])

    def get_name(self):
        return f"Swing({self.params['period']})"

    def long(self):
        """Enter when price at/near swing low"""
        ok = self.price[0] <= self.lowest[0] * (1 + self.params["entry_offset"])
        return ok, f"{self.get_name()} LONG at lowest={self.lowest[0]:.2f}"

    def short(self):
        """Enter when price at/near swing high"""
        ok = self.price[0] >= self.highest[0] * (1 - self.params["entry_offset"])
        return ok, f"{self.get_name()} SHORT at highest={self.highest[0]:.2f}"

    def exit_long(self):
        """Exit LONG: SL below low, TP above high"""
        sl_level = self.lowest[0] * (1 - self.params["sl_offset"])
        tp_level = self.highest[0] * (1 + self.params["tp_offset"])

        sl_hit = self.price[0] < sl_level
        tp_hit = self.price[0] > tp_level

        if self.params["use_sl"] and sl_hit:
            return True, f"{self.get_name()} SL {self.price[0]:.2f} < {sl_level:.2f}"

        if self.params["use_tp"] and tp_hit:
            return True, f"{self.get_name()} TP {self.price[0]:.2f} > {tp_level:.2f}"

        return False, ""

    def exit_short(self):
        """Exit SHORT: SL above high, TP below low"""
        sl_level = self.highest[0] * (1 + self.params["sl_offset"])
        tp_level = self.lowest[0] * (1 - self.params["tp_offset"])

        sl_hit = self.price[0] > sl_level
        tp_hit = self.price[0] < tp_level

        if self.params["use_sl"] and sl_hit:
            return True, f"{self.get_name()} SL {self.price[0]:.2f} > {sl_level:.2f}"

        if self.params["use_tp"] and tp_hit:
            return True, f"{self.get_name()} TP {self.price[0]:.2f} < {tp_level:.2f}"

        return False, ""
