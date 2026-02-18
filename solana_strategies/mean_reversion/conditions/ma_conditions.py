from ._base_condition import Condition
import backtrader as bt


class TrendFollowPriceMACond(Condition):
    """
    Trend following based on price position relative to a moving average.
    Supports multiple MA types: SMA, EMA, WMA, DEMA, TEMA, T3, Hull
    """
    default_params = {
        "ma_type": "ema",
        "period": 20,
    }

    def __init__(self, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.price = price
        self.ma = self._create_ma(price,
                                  self.params["ma_type"],
                                  self.params["period"])

    def _create_ma(self, price, ma_type, period):
        """Factory method to create different MA types"""
        ma_type = ma_type.lower()

        if ma_type == "sma":
            return bt.indicators.SMA(price, period=period)
        elif ma_type == "ema":
            return bt.indicators.EMA(price, period=period)
        elif ma_type == "wma":
            return bt.indicators.WMA(price, period=period)
        elif ma_type == "dema":
            return bt.indicators.DEMA(price, period=period)
        elif ma_type == "tema":
            return bt.indicators.TEMA(price, period=period)
        elif ma_type == "hull" or ma_type == "hma":
            return bt.indicators.HullMovingAverage(price, period=period)
        elif ma_type == "t3":
            return bt.indicators.T3(price, period=period)
        else:
            # Default to EMA if unknown type
            print(f"Warning: Unknown MA type '{ma_type}', defaulting to EMA")
            return bt.indicators.EMA(price, period=period)

    def get_name(self):
        ma_type = self.params["ma_type"].upper()
        return f"TrendPriceMA({ma_type}{self.params['period']})"

    # ---------------- ENTRY ---------------- #
    def long(self):
        """Enter long when price is above MA (uptrend)"""
        ok = self.price[0] > self.ma[0]
        msg = f"{self.get_name()} LONG price={self.price[0]:.2f} > ma={self.ma[0]:.2f}"
        return ok, msg

    def short(self):
        """Enter short when price is below MA (downtrend)"""
        ok = self.price[0] < self.ma[0]
        msg = f"{self.get_name()} SHORT price={self.price[0]:.2f} < ma={self.ma[0]:.2f}"
        return ok, msg

    # ---------------- EXIT ---------------- #
    def exit_long(self):
        """Exit long when price crosses below MA"""
        ok = self.price[0] < self.ma[0]
        msg = f"{self.get_name()} exit LONG (price below MA) price={self.price[0]:.2f} < ma={self.ma[0]:.2f}"
        return ok, msg

    def exit_short(self):
        """Exit short when price crosses above MA"""
        ok = self.price[0] > self.ma[0]
        msg = f"{self.get_name()} exit SHORT (price above MA) price={self.price[0]:.2f} > ma={self.ma[0]:.2f}"
        return ok, msg


class TrendFollow2MACond(Condition):
    """
    Trend following based on two moving averages with support for multiple MA types
    """
    default_params = {
        "fast_type": "ema",
        "slow_type": "ema",
        "fast_period": 20,
        "slow_period": 60,
    }

    def __init__(self, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)
        self.price = price

        # Create MAs based on type
        self.ma_fast = self._create_ma(price,
                                       self.params["fast_type"],
                                       self.params["fast_period"])
        self.ma_slow = self._create_ma(price,
                                       self.params["slow_type"],
                                       self.params["slow_period"])

    def _create_ma(self, price, ma_type, period):
        """Factory method to create different MA types"""
        ma_type = ma_type.lower()

        if ma_type == "sma":
            return bt.indicators.SMA(price, period=period)
        elif ma_type == "ema":
            return bt.indicators.EMA(price, period=period)
        elif ma_type == "wma":
            return bt.indicators.WMA(price, period=period)
        elif ma_type == "dema":
            return bt.indicators.DEMA(price, period=period)
        elif ma_type == "tema":
            return bt.indicators.TEMA(price, period=period)
        elif ma_type == "hull" or ma_type == "hma":
            return bt.indicators.HullMovingAverage(price, period=period)
        elif ma_type == "t3":
            return bt.indicators.T3(price, period=period)
        else:
            # Default to EMA if unknown type
            print(f"Warning: Unknown MA type '{ma_type}', defaulting to EMA")
            return bt.indicators.EMA(price, period=period)

    def get_name(self):
        fast_type = self.params["fast_type"].upper()
        slow_type = self.params["slow_type"].upper()
        return f"Trend2MA({fast_type}{self.params['fast_period']}/{slow_type}{self.params['slow_period']})"

    # ---------------- ENTRY ---------------- #
    def long(self):
        ok = self.ma_fast[0] > self.ma_slow[0]
        msg = f"{self.get_name()} LONG fast={self.ma_fast[0]:.2f} > slow={self.ma_slow[0]:.2f}"
        return ok, msg

    def short(self):
        ok = self.ma_fast[0] < self.ma_slow[0]
        msg = f"{self.get_name()} SHORT fast={self.ma_fast[0]:.2f} < slow={self.ma_slow[0]:.2f}"
        return ok, msg

    # ---------------- EXIT ---------------- #
    def exit_long(self):
        ok = self.ma_fast[0] < self.ma_slow[0]  # Trend broken
        msg = f"{self.get_name()} exit LONG (trend broken) fast={self.ma_fast[0]:.2f} < slow={self.ma_slow[0]:.2f}"
        return ok, msg

    def exit_short(self):
        ok = self.ma_fast[0] > self.ma_slow[0]  # Trend broken
        msg = f"{self.get_name()} exit SHORT (trend broken) fast={self.ma_fast[0]:.2f} > slow={self.ma_slow[0]:.2f}"
        return ok, msg


class MADistanceCond(Condition):
    default_params = {
        "ma_period": 50,
        "dist_thr": 0.01  # 1% distance from MA
    }

    def __init__(self, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.price = price
        self.ma = bt.indicators.EMA(price, period=self.params["ma_period"])

    def get_name(self):
        return f"MADist({self.params['ma_period']})"

    def long(self):
        ok = self.price[0] < self.ma[0] * (1 - self.params["dist_thr"])
        return ok, f"{self.get_name()} LONG price {self.price[0]:.2f} < MA*(1-{self.params['dist_thr']})"

    def short(self):
        ok = self.price[0] > self.ma[0] * (1 + self.params["dist_thr"])
        return ok, f"{self.get_name()} SHORT price {self.price[0]:.2f} > MA*(1+{self.params['dist_thr']})"

    def exit_long(self):
        ok = self.price[0] >= self.ma[0]
        return ok, f"{self.get_name()} exit LONG price {self.price[0]:.2f} >= MA"

    def exit_short(self):
        ok = self.price[0] <= self.ma[0]
        return ok, f"{self.get_name()} exit SHORT price {self.price[0]:.2f} <= MA"


class MeanReversionPriceMACond(Condition):
    """
    Mean reversion based on price distance from moving average.
    Enter when price is far from MA (oversold/overbought), exit when returning to MA.
    Supports multiple MA types: SMA, EMA, WMA, DEMA, TEMA, T3, Hull
    """
    default_params = {
        "ma_type": "ema",
        "period": 20,
        "distance_pct": 0.02,  # 2% away from MA to trigger entry
        "exit_at_ma": True,    # Exit when price reaches MA, or wait for opposite side
    }

    def __init__(self, price, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.price = price
        self.ma = self._create_ma(price,
                                  self.params["ma_type"],
                                  self.params["period"])

    def _create_ma(self, price, ma_type, period):
        """Factory method to create different MA types"""
        ma_type = ma_type.lower()

        if ma_type == "sma":
            return bt.indicators.SMA(price, period=period)
        elif ma_type == "ema":
            return bt.indicators.EMA(price, period=period)
        elif ma_type == "wma":
            return bt.indicators.WMA(price, period=period)
        elif ma_type == "dema":
            return bt.indicators.DEMA(price, period=period)
        elif ma_type == "tema":
            return bt.indicators.TEMA(price, period=period)
        elif ma_type == "hull" or ma_type == "hma":
            return bt.indicators.HullMovingAverage(price, period=period)
        elif ma_type == "t3":
            return bt.indicators.T3(price, period=period)
        else:
            print(f"Warning: Unknown MA type '{ma_type}', defaulting to EMA")
            return bt.indicators.EMA(price, period=period)

    def get_name(self):
        ma_type = self.params["ma_type"].upper()
        return f"MeanRev({ma_type}{self.params['period']},{self.params['distance_pct']*100:.1f}%)"

    # ---------------- ENTRY ---------------- #
    def long(self):
        """Enter long when price is significantly below MA (oversold)"""
        threshold = self.ma[0] * (1 - self.params["distance_pct"])
        ok = self.price[0] < threshold
        msg = f"{self.get_name()} LONG price={self.price[0]:.2f} < threshold={threshold:.2f} (MA={self.ma[0]:.2f})"
        return ok, msg

    def short(self):
        """Enter short when price is significantly above MA (overbought)"""
        threshold = self.ma[0] * (1 + self.params["distance_pct"])
        ok = self.price[0] > threshold
        msg = f"{self.get_name()} SHORT price={self.price[0]:.2f} > threshold={threshold:.2f} (MA={self.ma[0]:.2f})"
        return ok, msg

    # ---------------- EXIT ---------------- #
    def exit_long(self):
        """Exit long when price returns to MA (or crosses above if exit_at_ma=False)"""
        if self.params["exit_at_ma"]:
            # Exit when price reaches MA (mean reversion complete)
            ok = self.price[0] >= self.ma[0]
            msg = f"{self.get_name()} exit LONG (reached MA) price={self.price[0]:.2f} >= ma={self.ma[0]:.2f}"
        else:
            # Exit when price crosses above MA (stronger signal)
            threshold = self.ma[0] * (1 + self.params["distance_pct"])
            ok = self.price[0] > threshold
            msg = f"{self.get_name()} exit LONG (above MA) price={self.price[0]:.2f} > {threshold:.2f}"
        return ok, msg

    def exit_short(self):
        """Exit short when price returns to MA (or crosses below if exit_at_ma=False)"""
        if self.params["exit_at_ma"]:
            # Exit when price reaches MA (mean reversion complete)
            ok = self.price[0] <= self.ma[0]
            msg = f"{self.get_name()} exit SHORT (reached MA) price={self.price[0]:.2f} <= ma={self.ma[0]:.2f}"
        else:
            # Exit when price crosses below MA (stronger signal)
            threshold = self.ma[0] * (1 - self.params["distance_pct"])
            ok = self.price[0] < threshold
            msg = f"{self.get_name()} exit SHORT (below MA) price={self.price[0]:.2f} < {threshold:.2f}"
        return ok, msg
