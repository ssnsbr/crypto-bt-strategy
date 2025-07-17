
import backtrader as bt
from utils.utils import format_marketcap, format_price_to_marketcap

import math


class ScalperMartingaleSizer(bt.Sizer):
    """
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
            print(f"[Sizer] [{self.__class__.__name__}]", text)

    def __init__(self):
        self.has_done_initial_buy_sizer = False
        self.current_martingale_quantity = 0.0  # This will hold the quantity for the *next* martingale step
        self.log(" Log On, FiboMartingaleSizer as sizer.")
        if self.params.data_in_market_cap:
            self._format_value_for_log_mcap = format_marketcap
            self.log("Price IS in Market Cap!")
        else:
            self._format_value_for_log_mcap = format_price_to_marketcap
            self.log(" Price is NOT in Market Cap!")

    def get_cash(self, cash=1):
        if self.params.type_fixed:
            self.log(" using fixed amount for buy!")
            return self.params.initial_buy_amount_fix
        return cash * self.params.initial_buy_amount_factor

    def reset(self):
        """Resets the sizer's internal state for a new trading cycle."""
        self.has_done_initial_buy_sizer = False
        self.current_martingale_quantity = 0.0
        self.params.buy_type_next = None  # Reset the signal
        self.log(" state reset.")

    def update(self):  # Update for next step
        self.current_martingale_quantity *= self.p.martingale_multiplier
        self.current_martingale_cash *= self.params.martingale_multiplier

    # --- Main Sizing Logic ---

    def _getsizing(self, comminfo, cash, data, isbuy):
        # We only size buy orders
        if not isbuy:
            return 0  # Strategy handles sell orders with self.close()

        current_price = data.close[0]
        # Adjust price if using market cap data
        if self.params.data_in_market_cap:
            current_price = current_price / 1_000_000_000

        # --- Determining Buy Type Internally ---

        # If we have not done the initial buy yet, this must be the initial buy.
        if not self.has_done_initial_buy_sizer:

            # --- Initial Buy Sizing ---
            cash_for_buy = self.get_cash(cash)
            size = math.floor(cash_for_buy / current_price)

            if size > 0:
                # Calculate the quantity/cash for the Next Martingale step
                self.current_martingale_quantity = size * self.params.martingale_multiplier
                self.current_martingale_cash = cash_for_buy * self.params.martingale_multiplier

                # Mark that the initial buy has been processed
                self.has_done_initial_buy_sizer = True

                self.log(f': Initial Buy Size Calculated: {size}, Next Martingale Qty: {self.current_martingale_quantity:.2f}, Next Martingale Cash: {self.current_martingale_cash:.4f}')
                return size
            else:
                self.log(f': Initial BUY: Not enough cash ({self.cash_when_mcap(cash)}) for meaningful buy at {self._format_value_for_log_mcap(current_price)}')
                return 0

        # If we *have* done the initial buy, any subsequent buy is a Martingale buy.
        else:
            # We should use size_to_buy if we are tracking quantity, or calculate from cash if tracking cash.
            # size_to_buy = math.floor(self.current_martingale_quantity)
            cost_of_buy = self.current_martingale_cash
            size_to_buy = math.floor(cost_of_buy / current_price)

            if size_to_buy > 0 and cash >= cost_of_buy:
                # Update the quantity/cash for the *next* martingale step *before* returning the current size.
                self.update()

                self.log(f': Martingale Buy Size Calculated: {size_to_buy}, Next Martingale Qty: {self.current_martingale_quantity:.2f}')
                return size_to_buy
            else:
                self.log(f': Martingale Buy: Insufficient cash {self.cash_when_mcap(cash)} for {size_to_buy} units at {self._format_value_for_log_mcap(current_price)} or quantity is zero.')
                return 0
