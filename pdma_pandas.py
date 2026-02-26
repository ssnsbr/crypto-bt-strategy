import numpy as np
import pandas as pd


# ==============================
# === LOAD YOUR DATA FIRST ====
# ==============================
# usingdf must contain:
# ['open','high','low','close','volume']
# index should be datetime

# Example:
# usingdf = pd.read_csv("sol.csv", parse_dates=True, index_col=0)


# ==============================
# === INDICATOR FUNCTIONS ======
# ==============================

def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()


def dema(series, length):
    e1 = ema(series, length)
    e2 = ema(e1, length)
    return 2 * e1 - e2


def cross(series1, series2):
    return (
        ((series1 > series2) & (series1.shift(1) <= series2.shift(1))) |
        ((series1 < series2) & (series1.shift(1) >= series2.shift(1)))
    )


def bars_since(condition):
    idx = np.where(condition, np.arange(len(condition)), np.nan)
    idx = pd.Series(idx, index=condition.index).ffill()
    return pd.Series(np.arange(len(condition)), index=condition.index) - idx


# ==============================
# === STRATEGY PARAMETERS ======
# ==============================

base_ma = 50
multipliers = [1, 2, 3, 4, 5]
smooth = 23
normalize_len = 200
signal_len = 15
tpPerc = 0.01     # 1%
slPerc = 0.01     # 1%
use_tp = True
use_sl = True


# ==============================
# === BUILD INDICATORS =========
# ==============================

usingdf["hlc3"] = (usingdf["high"] + usingdf["low"] + usingdf["close"]) / 3

ma_periods = [base_ma * m for m in multipliers]

bars_list = []

for p in ma_periods:
    ma = dema(usingdf["hlc3"], p)
    usingdf[f"ma_{p}"] = ma

    c = cross(usingdf["close"], ma)
    bars = bars_since(c)

    bars_norm = bars / p
    bars_list.append(bars_norm)

# Average like Pine
usingdf["ma_b_raw"] = sum(bars_list) / len(bars_list)

# Smooth
usingdf["ma_b_smooth"] = ema(usingdf["ma_b_raw"], smooth)

# Z-score normalization
rolling_mean = usingdf["ma_b_smooth"].rolling(normalize_len).mean()
rolling_std = usingdf["ma_b_smooth"].rolling(normalize_len).std()

usingdf["ma_b_norm"] = (usingdf["ma_b_smooth"] - rolling_mean) / rolling_std

# Signal line
usingdf["ma_b_signal"] = ema(usingdf["ma_b_norm"], signal_len)


# ==============================
# === STRATEGY LOGIC ===========
# ==============================

usingdf["slope_up"] = usingdf["ma_b_norm"] > usingdf["ma_b_signal"]
usingdf["slope_down"] = usingdf["ma_b_norm"] < usingdf["ma_b_signal"]

usingdf["longCond"] = usingdf["slope_down"] & (usingdf["ma_b_signal"] > 0)
usingdf["shortCond"] = usingdf["slope_up"] & (usingdf["ma_b_signal"] < 0)


# ==============================
# === POSITION GENERATION ======
# ==============================

usingdf["position"] = 0

usingdf.loc[usingdf["longCond"], "position"] = 1
usingdf.loc[usingdf["shortCond"], "position"] = -1

# Hold position until opposite signal
usingdf["position"] = usingdf["position"].replace(0, np.nan).ffill().fillna(0)


# ==============================
# === SIMPLE BACKTEST ==========
# ==============================

usingdf["returns"] = usingdf["close"].pct_change()

usingdf["strategy_returns"] = usingdf["position"].shift(1) * usingdf["returns"]

# Optional TP/SL (vectorized approximation)
if use_tp or use_sl:
    entry_price = usingdf["close"].where(
        (usingdf["position"] != usingdf["position"].shift(1))
    ).ffill()

    if use_tp:
        long_tp = entry_price * (1 + tpPerc)
        short_tp = entry_price * (1 - tpPerc)

    if use_sl:
        long_sl = entry_price * (1 - slPerc)
        short_sl = entry_price * (1 + slPerc)

    long_exit = False
    short_exit = False

    if use_tp and use_sl:
        long_exit = (usingdf["high"] >= long_tp) | (usingdf["low"] <= long_sl)
        short_exit = (usingdf["low"] <= short_tp) | (usingdf["high"] >= short_sl)

    elif use_tp:
        long_exit = usingdf["high"] >= long_tp
        short_exit = usingdf["low"] <= short_tp

    elif use_sl:
        long_exit = usingdf["low"] <= long_sl
        short_exit = usingdf["high"] >= short_sl

    exit_mask = (
        ((usingdf["position"] == 1) & long_exit) |
        ((usingdf["position"] == -1) & short_exit)
    )

    usingdf.loc[exit_mask, "position"] = 0
    usingdf["position"] = usingdf["position"].replace(0, np.nan).ffill().fillna(0)

    usingdf["strategy_returns"] = usingdf["position"].shift(1) * usingdf["returns"]

# ==========================================
# === TRADE EXTRACTION =====================
# ==========================================

# Detect trade entries/exits
usingdf["pos_shift"] = usingdf["position"].shift(1)

entries = usingdf[(usingdf["position"] != 0) & (usingdf["pos_shift"] == 0)]
exits   = usingdf[(usingdf["position"] == 0) & (usingdf["pos_shift"] != 0)]

# Align trades
trades = []

exit_iter = iter(exits.iterrows())
current_exit = next(exit_iter, None)

for entry_idx, entry_row in entries.iterrows():
    
    # Find corresponding exit
    while current_exit and current_exit[0] <= entry_idx:
        current_exit = next(exit_iter, None)

    if current_exit is None:
        break

    exit_idx, exit_row = current_exit

    direction = entry_row["position"]
    entry_price = entry_row["close"]
    exit_price = exit_row["close"]

    if direction == 1:
        pnl = (exit_price - entry_price) / entry_price
    else:
        pnl = (entry_price - exit_price) / entry_price

    trades.append(pnl)

    current_exit = next(exit_iter, None)

trades = np.array(trades)

# ==========================================
# === PERFORMANCE METRICS ==================
# ==========================================

if len(trades) > 0:

    wins = trades[trades > 0]
    losses = trades[trades < 0]

    win_rate = len(wins) / len(trades)

    gross_profit = wins.sum()
    gross_loss = abs(losses.sum())

    profit_factor = gross_profit / gross_loss if gross_loss != 0 else np.inf

    avg_win = wins.mean() if len(wins) > 0 else 0
    avg_loss = abs(losses.mean()) if len(losses) > 0 else 0

    risk_reward = avg_win / avg_loss if avg_loss != 0 else np.inf

    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

    print("Trades:", len(trades))
    print("Win Rate:", round(win_rate * 100, 2), "%")
    print("Profit Factor:", round(profit_factor, 2))
    print("Avg Win:", round(avg_win * 100, 3), "%")
    print("Avg Loss:", round(avg_loss * 100, 3), "%")
    print("Risk/Reward:", round(risk_reward, 2))
    print("Expectancy per trade:", round(expectancy * 100, 3), "%")

else:
    print("No trades found.")
    
# ==============================
# === PERFORMANCE METRICS ======
# ==============================

usingdf["equity"] = (1 + usingdf["strategy_returns"]).cumprod()

total_return = usingdf["equity"].iloc[-1] - 1
sharpe = (
    usingdf["strategy_returns"].mean() /
    usingdf["strategy_returns"].std()
) * np.sqrt(365 * 24)  # adjust for timeframe

max_dd = (
    usingdf["equity"] /
    usingdf["equity"].cummax() - 1
).min()

print("Total Return:", round(total_return * 100, 2), "%")
print("Sharpe:", round(sharpe, 2))
print("Max Drawdown:", round(max_dd * 100, 2), "%")
