import numpy as np
import backtrader as bt


class TradeDurationAnalyzer(bt.Analyzer):
    """
    Records the duration (in bars) of each completed trade.
    Provides statistics: mean, median, min, max, std.
    """

    def __init__(self):
        self.durations = []

    def notify_trade(self, trade):
        if trade.isclosed:
            duration = trade.barclose - trade.baropen
            self.durations.append(duration)

    def get_analysis(self):
        if not self.durations:
            return {
                'mean': 0,
                'median': 0,
                'min': 0,
                'max': 0,
                'std': 0,
                'count': 0
            }

        durations = np.array(self.durations)
        return {
            'mean': float(np.mean(durations)),
            'median': float(np.median(durations)),
            'min': int(np.min(durations)),
            'max': int(np.max(durations)),
            'std': float(np.std(durations)),
            'count': len(durations)
        }


class CashHistoryAnalyzer(bt.Analyzer):
    """
    An analyzer to record the cash balance at each bar.
    """

    def __init__(self):
        self.cash_history = {}

    def next(self):
        # Record cash at the end of each bar
        # self.data.datetime[0] gives the date of the current bar (as a float)
        # self.strategy.broker.getcash() gives the current cash balance
        dt = self.strategy.data.datetime.datetime(0)  # Get the current bar's datetime object
        cash = self.strategy.broker.getcash()
        # Record if first entry or if cash has changed since last bar
        if not self.cash_history or cash != list(self.cash_history.values())[-1]:
            self.cash_history[dt] = cash

    def get_analysis(self):
        # Return the dictionary of cash history
        return self.cash_history


class BACounterAnalyzer(bt.Analyzer):
    """
    Records strategy-specific counters and exposes them at the end.
    """

    def __init__(self):
        self.results = {}

    def start(self):
        """Called once at the start"""
        self.results = {
            'ib_count': 0,
            'tp_count': 0,
            'sl_count': 0,
            'ba_round_count': 0,
            'ba_count': 0,
            'counter_list': [],
            'main_list': []
        }

    def notify_trade(self, trade):
        """Optional: update counters on trade events"""
        pass  # If you want to increment counts per trade

    def stop(self):
        """Called at the end of the strategy"""
        # Pull values from the strategy instance
        s = self.strategy
        self.results = {
            'ib_count': getattr(s, 'ib_count', 0),
            'tp_count': getattr(s, 'tp_count', 0),
            'sl_count': getattr(s, 'sl_count', 0),
            'ba_round_count': getattr(s, 'ba_round_count', 0),
            'ba_count': getattr(s, 'ba_count', 0),
            'counter_list': getattr(s, 'counter_list', []),
            'main_list': getattr(s, 'main_list', [])
        }

    def get_analysis(self):
        return self.results
