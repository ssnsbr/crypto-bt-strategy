
from riskmanagers.BaseRiskManagement import BaseRiskManagement
from strategies.Base import BaseTradingStrategy


class FiboR78Once(BaseTradingStrategy):
    params = (
        ('tp_percent', 0.5),
        ('sl_percent', 0.70),  # price * (1 - self.strategy.p.sl_percent)
        ('green_candle_streak_required', 2),
        ('data_in_market_cap', False),
        ('log', True),

        # Exit Strategy Enable/Disable Flags (with defaults)
        ('enable_emergency_exit', False),
        ('enable_stop_loss', False),
        ('enable_take_profit', True),
        ('enable_trailing_stop_loss', False),
        ('enable_trailing_take_profit', False),
        ('enable_dynamic_take_profit', False),  # Default Disabled

        # Trailing Stop Loss Parameters
        ('trailing_sl_percent', 0.02),
        ('trailing_sl_activation_profit_percent', 0.01),

        # Trailing Take Profit Parameters
        ('trailing_tp_percent', 0.01),
        ('trailing_tp_activation_profit_percent', 0.05),

        # Dynamic Take Profit Parameters
        ('dynamic_tp_peak_profit_percent', 0.10),  # Profit % from avg_buy_price to start tracking peak
        ('dynamic_tp_pullback_percent', 0.01),   # Percentage pullback from peak to trigger DTP

        # indicators
        ('rsi_period', 15),
        ('lookback_period', 50),  # Period to find the last significant high/low
        ('atr_period', 15),
        ('bb_period', 20),
        ('bb_devfactor', 2),
    )

    def __init__(self):
        super().__init__()  # Call the base class constructor
        # Instantiate the RiskManagement class
        self.risk_manager = BaseRiskManagement(self)
        self.buying = False
        self.tp = 0
        self.current_fibo = 0
        self.current_fibo_index = -1
        self.fibo_buy = 0.22
        # self.fibo_buy = 0.328
        # self.fibo_buy = 0.5
        # self.fibo_buy = 0.618
        # self.fibo_buy = 0.786
        self.Fibonacci_Buy_MCAP_78 = 0
        self.bought_78 = False
        self.once = True

    def update_ath(self):
        if super().update_ath():
            self.Fibonacci_Buy_MCAP_78 = self.ath * self.fibo_buy
            if not self.once:
                self.bought_78 = False

    def _execute_trading_logic(self):
        if self.ath <= 0.0:
            return
        if self.order:
            return

        tolerance = 0.02  # 2% buffer
        upper_bound = self.Fibonacci_Buy_MCAP_78 * (1 + tolerance)

        if self.current_price <= upper_bound and not self.bought_78:
            self.log(f'↑ BUY SIGNAL | Price: {self._format_value_for_log_mcap(self.current_price)}, at: {self._format_value_for_log_mcap(self.Fibonacci_Buy_MCAP_78)}, Fibo Level: {self.fibo_buy}')
            self.order = self.buy()
            self.bought_78 = True
        # Check upward touch


class FiboR78OnceFalse(FiboR78Once):
    """
    Just a copy of FiboR78OnceFalse with once is Off.
    """

    def __init__(self):
        super().__init__()  # Call the base class constructor
        self.once = False
