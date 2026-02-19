# Base signal - just a callable that returns bool
class Signal:
    def evaluate(self, action: ActionType) -> bool:
        raise NotImplementedError

# Compositors handle AND / OR / NOT


class AndSignal(Signal):
    def __init__(self, *signals):
        self.signals = signals

    def evaluate(self, action):
        return all(s.evaluate(action) for s in self.signals)


class OrSignal(Signal):
    def __init__(self, *signals):
        self.signals = signals

    def evaluate(self, action):
        return any(s.evaluate(action) for s in self.signals)


class NotSignal(Signal):
    def __init__(self, signal):
        self.signal = signal

    def evaluate(self, action):
        return not self.signal.evaluate(action)
