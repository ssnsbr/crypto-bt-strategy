
class MarketState(Enum):
    T = 0    # Trend
    SC = 1   # Small Correction
    NC = 2   # Normal Correction
    BC = 3   # Big Correction
    NT = 4   # New Trend
    ST = 5   # Small Move in Trend
    BT = 6   # Big Move in Trend


class MarketRegime(Enum):
    TRENDING = 0
    SIDEWAYS = 1

