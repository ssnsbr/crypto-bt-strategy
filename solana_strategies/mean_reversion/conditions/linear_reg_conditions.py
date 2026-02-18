import backtrader as bt
from ._base_condition import Condition


class LinearRegressionCond(Condition):
    """
    Linear Regression - Trend line with angle
    """
    default_params = {
        "period": 20,
        "angle_threshold": 10,  # Degrees - minimum angle for trend
    }

    def __init__(self, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close
        self.linreg = bt.indicators.LinearRegression(close, period=self.params["period"])

    def get_name(self):
        return f"LinReg({self.params['period']})"

    def _calculate_angle(self):
        """Calculate angle of linear regression line"""
        import math

        # Angle based on slope
        slope = (self.linreg[0] - self.linreg[-1]) / self.params["period"]
        angle = math.degrees(math.atan(slope / self.close[0]))
        return angle

    def long(self):
        """Enter long when price above regression line with positive angle"""
        angle = self._calculate_angle()
        above_line = self.close[0] > self.linreg[0]
        strong_uptrend = angle > self.params["angle_threshold"]

        ok = above_line and strong_uptrend
        msg = f"{self.get_name()} LONG price above line, angle={angle:.1f}°"
        return ok, msg

    def short(self):
        """Enter short when price below regression line with negative angle"""
        angle = self._calculate_angle()
        below_line = self.close[0] < self.linreg[0]
        strong_downtrend = angle < -self.params["angle_threshold"]

        ok = below_line and strong_downtrend
        msg = f"{self.get_name()} SHORT price below line, angle={angle:.1f}°"
        return ok, msg

    def exit_long(self):
        """Exit long when price crosses below regression line"""
        ok = self.close[0] < self.linreg[0]
        msg = f"{self.get_name()} exit LONG price below regression"
        return ok, msg

    def exit_short(self):
        """Exit short when price crosses above regression line"""
        ok = self.close[0] > self.linreg[0]
        msg = f"{self.get_name()} exit SHORT price above regression"
        return ok, msg
