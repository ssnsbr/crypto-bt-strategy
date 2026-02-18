from ._base_condition import Condition
import backtrader as bt


class ChaikinVolatilityCond(Condition):
    """
    Chaikin Volatility - Rate of change of High-Low range
    Measures volatility expansion/contraction
    Rising CV = increasing volatility (potential breakout)
    Falling CV = decreasing volatility (consolidation)
    """
    default_params = {
        "ema_period": 10,    # EMA of High-Low range
        "roc_period": 10,    # Rate of change period
        "high_threshold": 10,  # Above this = high volatility
        "low_threshold": -10,  # Below this = low volatility
    }

    def __init__(self, high, low, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        # High-Low range
        hl_range = high - low

        # EMA of the range
        self.ema_range = bt.indicators.EMA(hl_range, period=self.params["ema_period"])

        # Rate of change of the EMA
        self.cv = bt.indicators.ROC(self.ema_range, period=self.params["roc_period"])

    def get_name(self):
        return f"ChaikinVol({self.params['ema_period']},{self.params['roc_period']})"

    def long(self):
        """Enter long when volatility expanding (breakout potential)"""
        ok = self.cv[0] > self.params["high_threshold"]
        msg = f"{self.get_name()} LONG volatility expanding CV={self.cv[0]:.2f}%"
        return ok, msg

    def short(self):
        """Enter short when volatility expanding (breakout potential)"""
        ok = self.cv[0] > self.params["high_threshold"]
        msg = f"{self.get_name()} SHORT volatility expanding CV={self.cv[0]:.2f}%"
        return ok, msg

    def exit_long(self):
        """Exit long when volatility contracting (momentum fading)"""
        ok = self.cv[0] < self.params["low_threshold"]
        msg = f"{self.get_name()} exit LONG volatility contracting CV={self.cv[0]:.2f}%"
        return ok, msg

    def exit_short(self):
        """Exit short when volatility contracting (momentum fading)"""
        ok = self.cv[0] < self.params["low_threshold"]
        msg = f"{self.get_name()} exit SHORT volatility contracting CV={self.cv[0]:.2f}%"
        return ok, msg


class ChaikinVolatilityFilterCond(Condition):
    """
    Chaikin Volatility as a filter - trade only in specific volatility regimes
    """
    default_params = {
        "ema_period": 10,
        "roc_period": 10,
        "regime": "expanding",  # "expanding", "contracting", or "stable"
        "expansion_threshold": 5,
        "contraction_threshold": -5,
    }

    def __init__(self, high, low, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        hl_range = high - low
        self.ema_range = bt.indicators.EMA(hl_range, period=self.params["ema_period"])
        self.cv = bt.indicators.ROC(self.ema_range, period=self.params["roc_period"])

    def get_name(self):
        return f"ChaikinVol_Filter({self.params['regime']})"

    def _check_regime(self):
        """Check if current volatility matches desired regime"""
        regime = self.params["regime"].lower()

        if regime == "expanding":
            return self.cv[0] > self.params["expansion_threshold"]
        elif regime == "contracting":
            return self.cv[0] < self.params["contraction_threshold"]
        elif regime == "stable":
            return (self.cv[0] >= self.params["contraction_threshold"] and
                    self.cv[0] <= self.params["expansion_threshold"])
        return False

    def long(self):
        """Enter long if volatility regime is suitable"""
        ok = self._check_regime()
        msg = f"{self.get_name()} LONG volatility regime OK CV={self.cv[0]:.2f}%"
        return ok, msg

    def short(self):
        """Enter short if volatility regime is suitable"""
        ok = self._check_regime()
        msg = f"{self.get_name()} SHORT volatility regime OK CV={self.cv[0]:.2f}%"
        return ok, msg

    def exit_long(self):
        """Exit if volatility regime changes"""
        ok = not self._check_regime()
        msg = f"{self.get_name()} exit LONG regime changed CV={self.cv[0]:.2f}%"
        return ok, msg

    def exit_short(self):
        """Exit if volatility regime changes"""
        ok = not self._check_regime()
        msg = f"{self.get_name()} exit SHORT regime changed CV={self.cv[0]:.2f}%"
        return ok, msg


class ChaikinVolatilityBreakoutCond(Condition):
    """
    Chaikin Volatility Breakout - Enter when volatility contracts then expands
    Classic squeeze-and-break pattern
    """
    default_params = {
        "ema_period": 10,
        "roc_period": 10,
        "squeeze_threshold": -5,    # Volatility contraction level
        "expansion_threshold": 10,  # Volatility expansion level
        "squeeze_bars": 3,          # Minimum bars in squeeze
    }

    def __init__(self, high, low, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close
        hl_range = high - low
        self.ema_range = bt.indicators.EMA(hl_range, period=self.params["ema_period"])
        self.cv = bt.indicators.ROC(self.ema_range, period=self.params["roc_period"])

        # Track squeeze state
        self.squeeze_count = 0

    def get_name(self):
        return f"ChaikinVol_Breakout({self.params['squeeze_bars']})"

    def _was_in_squeeze(self):
        """Check if we had recent volatility contraction"""
        squeeze_bars = 0
        for i in range(1, self.params["squeeze_bars"] + 1):
            if self.cv[-i] < self.params["squeeze_threshold"]:
                squeeze_bars += 1
        return squeeze_bars >= self.params["squeeze_bars"]

    def _is_expanding(self):
        """Check if volatility is now expanding"""
        return self.cv[0] > self.params["expansion_threshold"]

    def long(self):
        """Enter long after squeeze when volatility expands upward"""
        squeeze_happened = self._was_in_squeeze()
        expanding = self._is_expanding()
        price_up = self.close[0] > self.close[-1]

        ok = squeeze_happened and expanding and price_up
        msg = f"{self.get_name()} LONG breakout after squeeze CV={self.cv[0]:.2f}%"
        return ok, msg

    def short(self):
        """Enter short after squeeze when volatility expands downward"""
        squeeze_happened = self._was_in_squeeze()
        expanding = self._is_expanding()
        price_down = self.close[0] < self.close[-1]

        ok = squeeze_happened and expanding and price_down
        msg = f"{self.get_name()} SHORT breakdown after squeeze CV={self.cv[0]:.2f}%"
        return ok, msg

    def exit_long(self):
        """Exit long when volatility contracts again"""
        ok = self.cv[0] < self.params["squeeze_threshold"]
        msg = f"{self.get_name()} exit LONG volatility contracting CV={self.cv[0]:.2f}%"
        return ok, msg

    def exit_short(self):
        """Exit short when volatility contracts again"""
        ok = self.cv[0] < self.params["squeeze_threshold"]
        msg = f"{self.get_name()} exit SHORT volatility contracting CV={self.cv[0]:.2f}%"
        return ok, msg


class HistoricalVolatilityCond(Condition):
    """
    Historical Volatility - Standard deviation of returns
    Measures actual price volatility (not range)
    """
    default_params = {
        "period": 20,
        "annualize": True,
        "high_threshold": 50,   # High volatility threshold (%)
        "low_threshold": 20,    # Low volatility threshold (%)
    }

    def __init__(self, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close

        # Calculate returns
        returns = bt.indicators.PctChange(close, period=1)

        # Standard deviation of returns
        self.hv = bt.indicators.StandardDeviation(returns, period=self.params["period"])

        # Annualize if needed (multiply by sqrt(365) for daily data)
        if self.params["annualize"]:
            import math
            self.hv = self.hv * math.sqrt(365) * 100  # Convert to percentage

    def get_name(self):
        return f"HV({self.params['period']})"

    def long(self):
        """Enter long when volatility is high (momentum trading)"""
        ok = self.hv[0] > self.params["high_threshold"]
        msg = f"{self.get_name()} LONG high volatility HV={self.hv[0]:.2f}%"
        return ok, msg

    def short(self):
        """Enter short when volatility is high (momentum trading)"""
        ok = self.hv[0] > self.params["high_threshold"]
        msg = f"{self.get_name()} SHORT high volatility HV={self.hv[0]:.2f}%"
        return ok, msg

    def exit_long(self):
        """Exit when volatility drops (momentum fading)"""
        ok = self.hv[0] < self.params["low_threshold"]
        msg = f"{self.get_name()} exit LONG low volatility HV={self.hv[0]:.2f}%"
        return ok, msg

    def exit_short(self):
        """Exit when volatility drops (momentum fading)"""
        ok = self.hv[0] < self.params["low_threshold"]
        msg = f"{self.get_name()} exit SHORT low volatility HV={self.hv[0]:.2f}%"
        return ok, msg


class HistoricalVolatilityRankCond(Condition):
    """
    Historical Volatility Rank (HVR) - Current HV vs recent range
    HVR = (Current HV - Min HV) / (Max HV - Min HV) * 100
    """
    default_params = {
        "hv_period": 20,      # HV calculation period
        "rank_period": 252,   # Period for min/max (1 year of trading days)
        "high_rank": 75,      # High volatility rank
        "low_rank": 25,       # Low volatility rank
    }

    def __init__(self, close, **kwargs):
        self.params = dict(self.default_params)
        self.params.update(kwargs)

        self.close = close

        # Calculate HV
        returns = bt.indicators.PctChange(close, period=1)
        self.hv = bt.indicators.StandardDeviation(returns, period=self.params["hv_period"])

        # Calculate min/max of HV
        self.hv_min = bt.indicators.Lowest(self.hv, period=self.params["rank_period"])
        self.hv_max = bt.indicators.Highest(self.hv, period=self.params["rank_period"])

    def get_name(self):
        return f"HVR({self.params['hv_period']},{self.params['rank_period']})"

    def _calculate_hvr(self):
        """Calculate HV Rank"""
        hv_range = self.hv_max[0] - self.hv_min[0]
        if hv_range == 0:
            return 50  # Neutral if no range

        hvr = ((self.hv[0] - self.hv_min[0]) / hv_range) * 100
        return hvr

    def long(self):
        """Enter long when HVR is low (mean reversion - buy low volatility)"""
        hvr = self._calculate_hvr()
        ok = hvr < self.params["low_rank"]
        msg = f"{self.get_name()} LONG low volatility rank HVR={hvr:.1f}%"
        return ok, msg

    def short(self):
        """Enter short when HVR is low (mean reversion - sell low volatility)"""
        hvr = self._calculate_hvr()
        ok = hvr < self.params["low_rank"]
        msg = f"{self.get_name()} SHORT low volatility rank HVR={hvr:.1f}%"
        return ok, msg

    def exit_long(self):
        """Exit when HVR becomes high (volatility expanded)"""
        hvr = self._calculate_hvr()
        ok = hvr > self.params["high_rank"]
        msg = f"{self.get_name()} exit LONG high volatility rank HVR={hvr:.1f}%"
        return ok, msg

    def exit_short(self):
        """Exit when HVR becomes high (volatility expanded)"""
        hvr = self._calculate_hvr()
        ok = hvr > self.params["high_rank"]
        msg = f"{self.get_name()} exit SHORT high volatility rank HVR={hvr:.1f}%"
        return ok, msg
