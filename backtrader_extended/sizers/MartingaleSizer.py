# from utils.utils import format_marketcap, format_price_to_marketcap
import backtrader as bt

# class MartingaleSizer(bt.Sizer):
#     """
#     A position sizer that doubles the stake (position size) after each loss.
#     This is a classic Martingale strategy, increasing risk after losses.
#     """
#     params = (
#         ('stake', 1),          # Base stake (initial position size)
#         ('multiplier', 2),     # Factor to multiply stake by after a loss
#         ('max_multiplier', 16),  # Maximum allowed multiplier to prevent excessive risk
#     )

#     def __init__(self):
#         self.loss_streak = 0
#         self.cash_to_buy = self.p.stake_cash

#     def notify_trade(self, trade):
#         """
#         Updates the loss streak and cash to buy based on the outcome of a closed trade.
#         """
#         if trade.isclosed:
#             if trade.pnl > 0:
#                 self.loss_streak = 0
#                 self.cash_to_buy = self.p.stake_cash
#             else:
#                 self.loss_streak += 1
#                 multiplier = min(self.p.multiplier ** self.loss_streak, self.p.max_multiplier)
#                 self.cash_to_buy = self.p.stake_cash * multiplier

#     def _getsizing(self, comminfo, cash, data, isbuy):
#         """
#         Calculates the position size (in units) for the next trade based on the
#         cash amount to be spent and the current price.
#         """
#         if isbuy:
#             size = self.cash_to_buy / data.close[0]
#             # Ensure we don't try to buy more than available cash
#             if self.cash_to_buy > cash:
#                 size = cash / data.close[0]
#             return size
#         else:  # Sell order
#             return self.getsizing(data)  # Close the entire position

#     def _getsizing(self, comminfo, cash, data, isbuy):
#         """
#         Calculates the position size for the next trade.
#         """
#         # Calculate the multiplier, capped by max_multiplier
#         multiplier = min(self.p.multiplier ** self.loss_streak, self.p.max_multiplier)
#         return self.p.stake * multiplier


class MartingaleSizer(bt.Sizer):
    params = (
        ('stake_cash', 5.0),      # Base cash amount for the initial position
        ('multiplier', 2),        # Multiplier for each subsequent buy
        ('max_multiplier', 16),   # Maximum multiplier cap
        ('percentage', 10),        # % of cash for initial buy (0 disables)
        ('log', True)
    )

    def __init__(self):
        self.buy_count = 0
        self.reset_on_next_buy = False
        self.starter_cash = self.p.stake_cash

    def log(self, text):
        if self.p.log:
            print(text)

    def reset(self):
        """Reset the sizer state - called when starting fresh"""
        self.log("[Sizer] RESET SCHEDULED - Will reset on next buy")
        self.reset_on_next_buy = True

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            # Check if we need to reset
            if self.reset_on_next_buy:
                self.log("[Sizer] RESETTING NOW - Back to Buy #1")
                self.buy_count = 0
                self.reset_on_next_buy = False
                self.starter_cash = self.p.stake_cash

            current_multiplier = min(self.p.multiplier ** self.buy_count, self.p.max_multiplier)
            # --- Initial buy uses percentage of cash ---
            if self.buy_count == 0 and self.p.percentage > 0:
                # Calculate cash amount for this buy
                cash_to_use = cash * (self.p.percentage / 100.0)
                self.starter_cash = cash_to_use
                self.log(f"[Sizer] Initial Buy: {self.p.percentage}% of cash = ${cash_to_use:.2f}")

            else:
                # Subsequent buys use martingale logic
                cash_to_use = self.starter_cash * current_multiplier
                self.log(f"[Sizer] Buy #{self.buy_count + 1}: using ${cash_to_use:.2f} (multiplier: {current_multiplier})")

            # Calculate size from cash amount
            price = data.close[0]
            size = cash_to_use / price

            # Check if we have enough cash (including commission)
            total_cost = size * price * (1 + comminfo.p.commission)
            if total_cost > cash:
                size = cash / (price * (1 + comminfo.p.commission))
                actual_cash = size * price
                self.log(f"[Sizer] Insufficient cash, using available ${actual_cash:.2f}")

            self.log(f"[Sizer] Buy #{self.buy_count + 1}: {size:.2f} units for ${cash_to_use:.2f} (multiplier: {current_multiplier})")

            # Increment buy count for next time
            self.buy_count += 1

            return size
        else:
            # Sell everything
            position = self.broker.getposition(data)
            if position.size > 0:
                self.log(f"[Sizer] Selling all {position.size:.2f} units")
            return position.size
