import matplotlib.dates as mdates
from matplotlib import patches, pyplot as plt
import pandas as pd
supply = 1_000_000_000
file = "axiom_chart_bars_2e3ocXtHGkkUpgRq4yEwRvYLWnozhrEGLyG2Anw8H1Bj_1755002288582.csv"
file = "axiom_chart_bars_5oeKooUKzdn6GVia93UKT85HzErM45J8ZupujGvUUWYS_1755004688588.csv"
f = "I:\\axiomchart\\1s\\" + file
data = pd.DataFrame()
data = pd.read_csv(f)

data["open"] = data["open"] * supply
data["high"] = data["high"] * supply
data["low"] = data["low"] * supply
data["close"] = data["close"] * supply


def plot_candles_with_trades_custom(df, title="Candlestick Chart "):
    fig, ax = plt.subplots(figsize=(18, 9))
    # width for 1s interval (in days), adjusted for better visual density
    width = 0.7 / (24 * 60 * 60)  # width for 1 second in matplotlib's date format

    # Apply filtering based on marketcap/price (your original 'drop_before'/'drop_after' logic)
    filtered_df = df.copy()

    # Plot candles
    for idx, row in filtered_df.iterrows():
        color = 'green' if row['close'] > row['open'] else 'red'
        # Wick
        ax.plot([idx, idx], [row['low'], row['high']], color=color, linewidth=1)

        # Body
        rect = patches.Rectangle(
            (mdates.date2num(idx) - width / 2, min(row['open'], row['close'])),
            width,
            abs(row['close'] - row['open']),
            facecolor=color,
            edgecolor='black' if color == 'red' else 'green',  # Better visual
            alpha=0.8
        )
        ax.add_patch(rect)

    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")  # Rotate for readability
    ax.set_title(title)
    ax.set_xlabel('Time')
    ax.set_ylabel('Price')
    ax.grid(True)
    # ax.legend() # Only if you want 'Buy' and 'Sell' labels in legend
    plt.tight_layout()
    plt.show()


plot_candles_with_trades_custom(data[1500:1800])
