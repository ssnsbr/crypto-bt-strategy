
import numpy as np


class LivelinessTracker:
    def __init__(self, window=60):
        self.window = window      # number of ticks to remember
        self.prices = []           # rolling window of recent prices

    def update(self, current_price):
        """Call this every round with latest price."""
        self.prices.append(current_price)
        if len(self.prices) > self.window:
            self.prices.pop(0)     # keep window size fixed

    def get_liveliness(self):
        """Return liveliness ∈ [0,1], where 0=dead straight move, 1=very bouncy."""
        if len(self.prices) < 3:
            return 0.0

        prices = np.array(self.prices)
        direct_move = abs(prices[-1] - prices[0])
        total_path = np.sum(np.abs(np.diff(prices)))

        if total_path == 0:
            return 0.0

        efficiency = direct_move / total_path
        liveliness = 1 - efficiency
        return float(liveliness)


class WeightedLivelinessTracker(LivelinessTracker):
    def get_liveliness(self):
        if len(self.prices) < 3:
            return 0.0
        prices = np.array(self.prices)
        returns = np.diff(prices) / prices[:-1]
        vol = np.std(returns)
        direct_move = abs(prices[-1] - prices[0])
        total_path = np.sum(np.abs(np.diff(prices)))
        if total_path == 0:
            return 0.0
        efficiency = direct_move / total_path
        liveliness = (1 - efficiency) * vol * 10  # scale for readability
        return float(min(liveliness, 1.0))
