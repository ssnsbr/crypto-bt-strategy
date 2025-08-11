import os
from matplotlib import patches, pyplot as plt
import pandas as pd

from data_utils import ready_df
import matplotlib.dates as mdates


def create_test():

    import pandas as pd
    import numpy as np

    # Define the start and end time for the data, covering 120 seconds.
    start_time = pd.to_datetime('2020-06-10 21:16:00')
    end_time = start_time + pd.Timedelta(seconds=119)  # 120 seconds total, from 0 to 119

    # Create a full range of 1-second timestamps.
    date_range = pd.date_range(start=start_time, end=end_time, freq='S')

    # Create a linear price path from 5000 to 100000 over 120 seconds.
    # We add some random noise to make it more realistic.
    price_path = np.linspace(5000, 100000, len(date_range)) + np.random.randn(len(date_range)) * 10

    # Create the DataFrame
    df = pd.DataFrame(index=date_range)
    df['open'] = price_path
    df['close'] = df['open'] + np.random.randn(len(df)) * 50
    df['high'] = df[['open', 'close']].max(axis=1) + np.abs(np.random.randn(len(df)) * 10)
    df['low'] = df[['open', 'close']].min(axis=1) - np.abs(np.random.randn(len(df)) * 10)
    df['volume'] = np.random.randint(10, 500, len(df))

    # Randomly drop a few rows to simulate missing data points
    # This will drop a random number of rows between 5 and 10
    rows_to_drop = np.random.choice(df.index, size=np.random.randint(5, 10), replace=False)
    df = df.drop(rows_to_drop)

    # Reset the index to make the datetime a column again
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'datetime'}, inplace=True)

    # Reorder the columns to match the MT5 import format
    df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]

    # Save the DataFrame to a CSV file
    output_filename = 'test.csv'
    df.to_csv(output_filename, index=False)

    print(f"Test data successfully created and saved to '{output_filename}'")
    print(f"The file contains {len(df)} rows and has a price range from {df['low'].min():.2f} to {df['high'].max():.2f}.")
    print("Some seconds are missing from the sequence, as requested.")


def to_mt5(df, to_path='1s_as_m1_data.csv'):
    print("Converting to MT5 format...")
    # df['datetime'] = pd.to_datetime(df['datetime'])
    df['datetime'] = df["timestamp_fake1min"]
    folder = "I:\\axiomchart\\MT5\\"
    # MT5 requires the data in a specific format for import.
    # The standard format is: datetime, open, high, low, close, volume.
    # You can rename columns if they don't match exactly.
    # Example of renaming:
    # df.rename(columns={'timestamp': 'datetime'}, inplace=True)

    # Select only the necessary columns in the correct order.
    df_ready_for_mt5 = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
    # df_ready_for_mt5[df_ready_for_mt5["volume"] < 1]["volume"] = 1
    df_ready_for_mt5["volume"].fillna(1)
    df_ready_for_mt5.loc[df_ready_for_mt5["volume"] < 1, "volume"] = 1

    df_ready_for_mt5["tickvolume"] = df_ready_for_mt5["volume"]
    df_ready_for_mt5["spread"] = 1

    # Save the data to a CSV file without the index.
    # This file now contains your 1-second data, but when imported as M1,
    # each row will be interpreted as a 1-minute candle.
    # The `index=False` parameter ensures the dataframe's index is not written to the CSV.
    df_ready_for_mt5.to_csv(folder + to_path, index=False)
    print(df_ready_for_mt5.head())
    print(df_ready_for_mt5.tail())
    print("Data successfully saved to 1s_as_m1_data.csv")
    print("This file contains your 1-second data, formatted for MT5 import.")


def fill_missing_candles(df, freq='s'):
    print("Filling missing candles...")
    df = df.copy()
    df.set_index('datetime', inplace=True)
    df["datetime"] = df.index
    # Create full index for desired frequency
    full_idx = pd.date_range(start=df["datetime"].min(), end=df["datetime"].max(), freq=freq)
    print(len(full_idx), full_idx)
    # Reindex to full timeline, inserting NaNs for missing candles
    df = df.reindex(full_idx)

    # Forward fill OHLC prices for missing candles from previous close
    df['close'] = df['close'].ffill()

    # Fill open with previous close
    df['open'] = df['open'].fillna(df['close'])

    # For high/low, temporarily fill with open if missing
    df['high'] = df['high'].combine_first(df['open'])
    df['low'] = df['low'].combine_first(df['open'])

    # Fix any logical inconsistencies
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)

    # Set volume for missing candles to 0
    df['volume'] = df['volume'].fillna(1)

    df.reset_index(inplace=True)
    df.rename(columns={'index': 'filleddatetime'}, inplace=True)

    return df


def fake_timestamp_as_1min(df, f="timestamp", f2="filleddatetime"):
    print("Faking timestamp as 1min...")
    df = df.copy()

    # Convert first timestamp to datetime, floor seconds
    start_datetime = pd.to_datetime(df[f].iloc[0], unit='ms').replace(second=0, microsecond=0)
    print("start_datetime:", start_datetime)
    # start_time = int(start_time.timestamp() * 1000)

    # Time delta from the floored start time in seconds
    df["diff_from_start"] = (df[f2] - start_datetime).dt.total_seconds()
    # df["diff_from_start"] = (df["filleddatetime"] - start_time) / 1000  # in seconds

    # Multiply by 60 to simulate 1s → 1m scale, convert back to datetime
    df["timestamp_fake1min"] = start_datetime + pd.to_timedelta(df["diff_from_start"] * 60, unit='s')
    # df["timestamp_fake1min"] = pd.to_datetime(start_time + df["diff_from_start"] * 60000, unit='ms')
    return df


def resample_to_higher_tf(df, tf='15T'):
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)

    resampled = df.resample(tf).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    resampled.loc[resampled["volume"] < 1, "volume"] = 1
    # resampled[resampled["volume"] < 1]["volume"] = 1
    resampled["tickvolume"] = resampled["volume"]
    resampled["spread"] = 1

    resampled.reset_index(inplace=True)
    return resampled


# --- Adapted Custom Plot for Candlesticks with Enhanced Trades ---
# This function is for when backtrader's default trade plotting isn't enough.
# It assumes you're passing in the *original* dataframe (or a slice of it)
# and a 'trades' DataFrame you've prepared (e.g., from analyze_trades or a custom process).
def plot_candles_with_trades_custom(df, only_around_trades=True, margin=60, drop_before=None, drop_after=None, title="Candlestick Chart with Trades"):
    fig, ax = plt.subplots(figsize=(18, 9))
    # width for 1s interval (in days), adjusted for better visual density
    width = 0.7 / (24 * 60 * 60)  # width for 1 second in matplotlib's date format

    # Apply filtering based on marketcap/price (your original 'drop_before'/'drop_after' logic)
    filtered_df = df.copy()
    if drop_before is not None:
        start_idx = filtered_df[filtered_df['open'] >= drop_before].first_valid_index()
        if start_idx is not None:
            filtered_df = filtered_df.loc[start_idx:].copy()
        else:
            print("No candle reached 'drop_before' threshold. Adjusting plot range.")

    if drop_after is not None:
        end_idx = filtered_df[filtered_df['open'] > drop_after].last_valid_index()
        if end_idx is not None:
            filtered_df = filtered_df.loc[:end_idx].copy()
        else:
            print("No candle exceeded 'drop_after' threshold. Adjusting plot range.")

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


if __name__ == "__main__":
    # create_test()
    folder_path = 'I:\\axiomchart\\1s\\'
    file_csv = "15s_axiom_chart_bars_Ekv9HdumWqnXZgq5G6ge6bk1ZRHKXYC2WnSFL94sQmLJ_1752166201266.csv"
    file_csv = "test.csv"

    # List all CSV files
    csv_files = [folder_path + f for f in os.listdir(folder_path) if f.endswith('.csv')]
    print(f"Found {len(csv_files)} CSV files.", [len(pd.read_csv(csv_files[df_index])) for df_index in range(len(csv_files))])
    #
    df_index = 33
    file_csv = csv_files[df_index]
    print(file_csv)
    df = pd.read_csv(file_csv)
    df = ready_df(df, mcap=True)
    #
    print(df.head())
    print(df.tail())
    df['high'] = df[['open', 'close', 'high', 'low']].max(axis=1)
    df['low'] = df[['open', 'close', 'low', 'high']].min(axis=1)

    print(len(df[df["open"] < df["low"]]))  # 9180
    print(len(df[df["open"] > df["low"]]))  # 9180
    print(len(df[df["open"] > df["high"]]))  # 8024
    print(len(df[df["open"] < df["high"]]))  # 8024

    print(len(df[df["close"] < df["low"]]))
    print(len(df[df["close"] > df["high"]]))
    print(len(df[df["low"] > df["high"]]))
    # plot_candles_with_trades_custom(df)
    # dffile = folder_path + "test.csv"
    # print("Reading", dffile)
    # df = pd.read_csv(dffile)
    # df = ready_df(df, mcap=True)
    fill = False
    if fill:
        df = fill_missing_candles(df)
        print(df.columns)
        print(df.head())
        df = fake_timestamp_as_1min(df, f="timestamp", f2="filleddatetime")
        print(df.head())
    else:
        df = fake_timestamp_as_1min(df, f="timestamp", f2="datetime")
        print(df.head())

    # Check if all timestamps are spaced exactly 1 minute apart
    # df['fake_datetime'] = pd.to_datetime(df['timestamp_fake1min'])
    # gaps = df['fake_datetime'].diff().dt.total_seconds()
    # print("gaps.value_counts():", gaps.value_counts())

    to_mt5(df)
    df_5m = resample_to_higher_tf(df, '5min')
    df_5m.to_csv("custom_5m_data.csv", index=False)

    df_15m = resample_to_higher_tf(df, '15min')
    df_15m.to_csv("custom_15m_data.csv", index=False)
