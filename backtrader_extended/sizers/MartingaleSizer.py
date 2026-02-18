import backtrader as bt


class MartingaleSizer(bt.Sizer):
    """
    A position sizer that doubles the stake (position size) after each loss.
    This is a classic Martingale strategy, increasing risk after losses.
    """
    params = (
        ('stake', 1),          # Base stake (initial position size)
        ('multiplier', 2),     # Factor to multiply stake by after a loss
        ('max_multiplier', 16),  # Maximum allowed multiplier to prevent excessive risk
    )

    def __init__(self):
        self.loss_streak = 0  # Counter for consecutive losses

    def notify_trade(self, trade):
        """
        Updates the loss streak based on the outcome of a closed trade.
        """
        if trade.isclosed:
            self.loss_streak = 0 if trade.pnl > 0 else self.loss_streak + 1

    def _getsizing(self, comminfo, cash, data, isbuy):
        """
        Calculates the position size for the next trade.
        """
        # Calculate the multiplier, capped by max_multiplier
        multiplier = min(self.p.multiplier ** self.loss_streak, self.p.max_multiplier)
        return self.p.stake * multiplier
