
import backtrader as bt


class DynamicTrendHybridSizer(bt.Sizer):
    """
    A hybrid position sizer that dynamically switches between Martingale
    (increase on losses) and Anti-Martingale (increase on wins) logic
    based on an external trend filter.
    """
    params = (
        ('stake', 1),          # Base stake
        ('multiplier', 2),     # Multiplier for streaks
        ('max_multiplier', 16),  # Maximum allowed multiplier
        ('trend_filter', None),  # Callable: a function that returns True if trend is up (for Anti-Martingale)
    )

    def __init__(self):
        self.win_streak = 0
        self.loss_streak = 0

    def notify_trade(self, trade):
        """
        Updates win/loss streaks based on trade outcomes.
        """
        if trade.isclosed:
            if trade.pnl > 0:
                self.win_streak += 1
                self.loss_streak = 0  # Reset loss streak on a win
            else:
                self.loss_streak += 1
                self.win_streak = 0  # Reset win streak on a loss

    def _getsizing(self, comminfo, cash, data, isbuy):
        """
        Calculates the position size for the next trade, adapting to trend.
        """
        # Determine if the trend is up using the provided trend_filter callable
        # If no filter is provided, it defaults to False (Martingale logic)
        is_trending_up = self.p.trend_filter(data) if self.p.trend_filter else False

        # If trending up, use Anti-Martingale logic (increase on wins)
        # If not trending up (or trending down), use Martingale logic (increase on losses)
        streak = self.win_streak if is_trending_up else self.loss_streak

        # Calculate the multiplier, capped by max_multiplier
        multiplier = min(self.p.multiplier ** streak, self.p.max_multiplier)
        return self.p.stake * multiplier
