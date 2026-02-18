import backtrader as bt


class AntiMartingaleSizer(bt.Sizer):
    """
    A position sizer that doubles the stake (position size) after each win.
    This is an Anti-Martingale strategy, increasing stake after wins to
    capitalize on positive streaks.
    """
    params = (
        ('stake', 1),          # Base stake
        ('multiplier', 2),     # Factor to multiply stake by after a win
        ('max_multiplier', 8),  # Maximum allowed multiplier
    )

    def __init__(self):
        self.win_streak = 0  # Counter for consecutive wins

    def notify_trade(self, trade):
        """
        Updates the win streak based on the outcome of a closed trade.
        """
        if trade.isclosed:
            self.win_streak = self.win_streak + 1 if trade.pnl > 0 else 0

    def _getsizing(self, comminfo, cash, data, isbuy):
        """
        Calculates the position size for the next trade.
        """
        # Calculate the multiplier, capped by max_multiplier
        multiplier = min(self.p.multiplier ** self.win_streak, self.p.max_multiplier)
        return self.p.stake * multiplier
