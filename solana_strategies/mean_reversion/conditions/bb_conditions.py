
from ._base_condition import Condition
import backtrader as bt


class MeanReversionBBCond(Condition):
    """
    Mean reversion using Bollinger Bands - buy at lower band, sell at upper band
    """
    default_params = {
        "period": 20,
        "devfactor": 2,
        "exit_mid": True,  # Exit at middle band or opposite band
    }

    def __init__(self, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)
        self.price = price
        self.bb = bt.indicators.BollingerBands(
            price,
            period=self.params["period"],
            devfactor=self.params["devfactor"]
        )

    def get_name(self):
        return f"BB_MeanRev({self.params['period']},{self.params['devfactor']})"

    def long(self):
        """Enter long when price touches/breaks below lower band"""
        ok = self.price[0] <= self.bb.lines.bot[0]
        return ok, f"{self.get_name()} LONG price={self.price[0]:.2f} <= bot={self.bb.lines.bot[0]:.2f}"

    def short(self):
        """Enter short when price touches/breaks above upper band"""
        ok = self.price[0] >= self.bb.lines.top[0]
        return ok, f"{self.get_name()} SHORT price={self.price[0]:.2f} >= top={self.bb.lines.top[0]:.2f}"

    def exit_long(self):
        """Exit long when price returns to middle (or upper band)"""
        if self.params["exit_mid"]:
            ok = self.price[0] >= self.bb.lines.mid[0]
            return ok, f"{self.get_name()} exit LONG price={self.price[0]:.2f} >= mid={self.bb.lines.mid[0]:.2f}"
        else:
            ok = self.price[0] >= self.bb.lines.top[0]
            return ok, f"{self.get_name()} exit LONG price={self.price[0]:.2f} >= top={self.bb.lines.top[0]:.2f}"

    def exit_short(self):
        """Exit short when price returns to middle (or lower band)"""
        if self.params["exit_mid"]:
            ok = self.price[0] <= self.bb.lines.mid[0]
            return ok, f"{self.get_name()} exit SHORT price={self.price[0]:.2f} <= mid={self.bb.lines.mid[0]:.2f}"
        else:
            ok = self.price[0] <= self.bb.lines.bot[0]
            return ok, f"{self.get_name()} exit SHORT price={self.price[0]:.2f} <= bot={self.bb.lines.bot[0]:.2f}"
