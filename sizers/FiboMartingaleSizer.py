import math
import backtrader as bt
from utils.utils import format_marketcap, format_price_to_marketcap


class FiboMartingaleSizer(bt.Sizer):
    """
    A custom sizer for the FiboMartingaleStrategy, handling initial buy
    and subsequent Fibonacci-based Martingale quantities,
    decoupled from direct strategy state inspection.
    """
    params = (
        ('initial_buy_amount_factor', 0.05),
        ('initial_buy_amount_fix', 0.1),
        ('martingale_multiplier', 2.0),
        ('type_fixed', True),
        # A flag/state that the strategy can set on the sizer, or pass via order params
        ('buy_type_next', None),  # Used to signal the type of buy for the next getsizing call
        ('log', True),
        ('data_in_market_cap', False),
    )

    def cash_when_mcap(self, value):
        """
        when using marketcap, the cash was multiplied by 1B for math reasons, so when logging divid it by 1B
        """
        if self.params.data_in_market_cap:
            return value / 1_000_000_000
        else:
            return value

    def log(self, text):
        if self.params.log:
            print("[Sizer]", self.__class__.__name__, text)

    def __init__(self):
        self.has_done_initial_buy_sizer = False
        self.current_martingale_quantity = 0.0  # This will hold the quantity for the *next* martingale step
        self.log("Log On, FiboMartingaleSizer as sizer.")
        if self.params.data_in_market_cap:
            self._format_value_for_log_mcap = format_marketcap
            self.log("Price IS in Market Cap!")
        else:
            self._format_value_for_log_mcap = format_price_to_marketcap
            self.log("Price is NOT in Market Cap!")

    def get_cash(self, cash=1):
        if self.params.type_fixed:
            self.log("using fixed amount for buy!")
            return self.params.initial_buy_amount_fix
        return cash * self.params.initial_buy_amount_factor

    def reset(self):
        """Resets the sizer's internal state for a new trading cycle."""
        self.has_done_initial_buy_sizer = False
        self.current_martingale_quantity = 0.0
        self.params.buy_type_next = None  # Reset the signal
        self.log("state reset.")

    def update(self):  # Update for next step
        self.current_martingale_quantity *= self.p.martingale_multiplier
        self.current_martingale_cash *= self.params.martingale_multiplier

    def _getsizing(self, comminfo, cash, data, isbuy):
        # We only size buy orders
        if not isbuy:
            return 0  # Strategy handles sell orders with self.close()

        # The strategy signals the buy type via a parameter on the sizer instance
        buy_type = self.params.buy_type_next
        # Reset the signal immediately after reading it
        self.params.buy_type_next = None

        current_price = data.close[0]  # Use the current bar's close price for sizing
        if self.params.data_in_market_cap:
            current_price = current_price / 1_000_000_000
        # --- Initial Buy Sizing ---
        if buy_type == 'initial_buy':
            if not self.has_done_initial_buy_sizer:
                cash_for_buy = self.get_cash(cash)
                size = math.floor(cash_for_buy / current_price)
                if size > 0:
                    self.current_martingale_quantity = size * self.params.martingale_multiplier
                    self.current_martingale_cash = cash_for_buy * self.params.martingale_multiplier
                    self.has_done_initial_buy_sizer = True
                    self.log(f'Initial Buy Size Calculated: {size}, Next Martingale Qty: {self.current_martingale_quantity:.2f}, cash {self.current_martingale_cash:.4f}')
                    return size
                else:
                    self.log(f'Initial BUY: Not enough cash ({self.cash_when_mcap(cash)}) for meaningful buy at {self._format_value_for_log_mcap(current_price)}')
                    return 0
            else:
                # This should ideally not happen if strategy logic is correct
                self.log("Warning Attempted initial_buy but already done initial buy. Returning 0.")
                return 0

        # --- Fibonacci Martingale Buy Sizing ---
        elif buy_type == 'fibo_martingale_buy':
            if self.has_done_initial_buy_sizer:  # Must have done initial buy first
                size_to_buy = math.floor(self.current_martingale_quantity)
                # cost_of_buy = size_to_buy * current_price
                cost_of_buy = self.current_martingale_cash
                size = math.floor(cost_of_buy / current_price)

                if size_to_buy > 0 and cash >= cost_of_buy:
                    self.update()
                    self.log(f'Fibo Buy Size Calculated: {size_to_buy}, Next Martingale Qty: {self.current_martingale_quantity:.2f}')
                    return size_to_buy
                else:
                    self.log(f'Fibo Buy: Insufficient cash  {self.cash_when_mcap(cash)} for {size_to_buy} units at {self._format_value_for_log_mcap(current_price)} or quantity is zero.')
                    return 0
            else:
                self.log("Attempted fibo_martingale_buy before initial buy. Returning 0.")
                return 0
        else:
            # This handles cases where _getsizing is called for an unexpected buy type
            # (e.g., if strategy tries self.buy() without setting buy_type_next)
            self.log(f"Warning Unknown buy_type_next: {buy_type}. Returning 0.")
            return 0
