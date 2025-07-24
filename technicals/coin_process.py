from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
import numpy as np
import pandas as pd
import os


# Load and preprocess a raw CSV DataFrame
def ready_df(df_input, mcap=False):
    print("Preparing dataframe with size", len(df_input))

    df_input["timestamp"] = df_input["time"]
    df_input['time'] = pd.to_datetime(df_input['timestamp'], unit='ms')

    if mcap:
        for c in ["open", "high", "low", "close"]:
            df_input[c] = df_input[c] * 1_000_000_000

    df_input['color'] = np.where(df_input['close'] > df_input['open'], 'green', 'red')
    df_input = df_input.rename(columns={'time': 'datetime'})
    return df_input


def enrich_indicators(df):
    df['return'] = df['close'].pct_change()  # Price momentum per second

    # Momentum & volatility indicators
    df['rsi'] = RSIIndicator(df['close'], window=14).rsi()  # Overbought/oversold momentum
    df['atr'] = AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()  # True range volatility

    # Short-term volatility window profiles (1s, 5s, 15s)
    df['volatility_1s'] = df['return'].rolling(window=1).std()
    df['volatility_5s'] = df['return'].rolling(5).std()
    df['volatility_15s'] = df['return'].rolling(15).std()

    # Volume dynamics for surge/fade detection
    df['volume_rolling_60'] = df['volume'].rolling(60).sum()
    df['volume_rolling_300'] = df['volume'].rolling(300).mean()
    df['volume_surge'] = df['volume_rolling_60'] / (df['volume_rolling_300'] + 1e-9)  # Measures relative spike in activity

    # Measures breakout strength adjusted for volatility
    df['breakout_score'] = (df['close'] - df['close'].rolling(60).mean()) / (df['atr'] + 1e-9)

    # Impulse = sudden 5s spike in price + 10x volume → possible whale entry or bot spike
    df['impulse'] = (df['close'].pct_change(periods=5).abs() > 0.03) & \
                    (df['volume'] > df['volume'].rolling(60).mean() * 10)

    # Detect fakeouts: price pops but reverses quickly with higher sell volume
    df['fakeout'] = (
        (df['close'].pct_change() > 0.02) &
        (df['close'].shift(-1) < df['close']) &
        (df['volume'].shift(-1) > df['volume'])
    )

    # Quiet price + growing volume = likely pre-pump accumulation
    df['price_std_30s'] = df['close'].rolling(30).std()
    df['volume_slope'] = df['volume'].rolling(60).mean().diff()
    df['accumulation'] = (df['price_std_30s'] < df['price_std_30s'].median() * 0.5) & \
                         (df['volume_slope'] > 0)

    # Green candle streak with shrinking volume, then red → exhaustion pattern
    df['is_green'] = (df['color'] == 'green').astype(int)
    df['green_streak'] = df['is_green'].rolling(5).sum() == 5
    # df['green_streak'] = df['color'].rolling(5).apply(lambda x: all(i == 'green' for i in x), raw=False)
    # df['decreasing_vol'] = df['volume'].rolling(5).apply(lambda x: all(np.diff(x) < 0), raw=False)
    df['decreasing_vol'] = df['volume'].rolling(5).apply(
        lambda x: np.all(np.diff(x) < 0), raw=True
    )
    df['micro_reversal'] = (df['green_streak']) & (df['decreasing_vol']) & (df['color'].shift(-1) == 'red')

    # Max drawdown from ATH – shows when dumps begin
    df['ath'] = df['close'].cummax()
    df['drawdown'] = df['close'] / df['ath'] - 1
    df['big_dump'] = df['drawdown'] < -0.5  # More than 50% crash from peak

    # Detect consistent pressure moves (same color candles, low vol std) → possible whale trail
    df['whale_trail'] = False
    for i in range(10, len(df)):
        window = df.iloc[i - 10:i]
        if window['color'].nunique() == 1 and window['volume'].std() / (window['volume'].mean() + 1e-9) < 0.15:
            df.loc[df.index[i], 'whale_trail'] = True

    # Sharp directional moves over 5s → bot sweep or forced breakout
    df['ladder_sweep'] = False
    for i in range(5, len(df)):
        changes = df['close'].pct_change().iloc[i - 4:i + 1]
        if all(x > 0.02 for x in changes) or all(x < -0.02 for x in changes):
            df.loc[df.index[i], 'ladder_sweep'] = True

    # Volume burnout zone = price stalls despite extreme volume
    df['burnout_zone'] = (df['volume'] > df['volume'].rolling(60).quantile(0.98)) & \
                         (df['return'].abs() < 0.001)

    # Flash dump = large red candle with abnormally high volume
    df['flash_dump'] = (df['return'] < -0.05) & \
                       (df['volume'] > df['volume'].rolling(100).quantile(0.98)) & \
                       (df['color'] == 'red')

    # Wick vs. body analysis → price rejection / imbalance areas
    df['upper_wick'] = df['high'] - df[['close', 'open']].max(axis=1)
    df['lower_wick'] = df[['close', 'open']].min(axis=1) - df['low']
    df['body'] = (df['close'] - df['open']).abs()
    df['rejection'] = ((df['upper_wick'] > 2 * df['body']) | (df['lower_wick'] > 2 * df['body']))
    df['wick_body_ratio'] = (df['upper_wick'] + df['lower_wick']) / (df['body'] + 1e-9)
    df['imbalance'] = df['wick_body_ratio'] > 5  # Extreme wick/candle ratio → instability

    # Double top detector within 10s → early reversal signal
    df['double_top'] = False
    for i in range(10, len(df)):
        segment = df['high'].iloc[i - 10:i]
        if np.sum(np.isclose(segment, segment.max(), rtol=0.0005)) >= 2:
            df.loc[df.index[i], 'double_top'] = True

    # Compression = low price std → pre-breakout setup
    df['compression_zone'] = df['close'].rolling(60).std() < df['close'].std() * 0.25

    # Mean-reverting behavior: alternates red-green in short time
    df['reversal'] = df['return'] * df['return'].shift(1) < 0
    df['mean_reversion_rate'] = df['reversal'].rolling(30).mean()

    # Forward returns: simulate holding for 5/10/30 seconds
    for n in [5, 10, 30]:
        df[f'holding_return_{n}s'] = df['close'].shift(-n) / df['close'] - 1

    # Pump strength = overall price gain * volume / time to ATH
    ath_idx = df['close'].idxmax()
    time_to_ath = (ath_idx - df.index[0]).total_seconds()
    gain = df['close'].max() / df['close'].iloc[0] - 1
    df['psi'] = gain * df['volume'].mean() / (time_to_ath + 1)

    # Normalized price path (0–1 scale) → shape classification
    df['norm_price'] = (df['close'] - df['close'].min()) / (df['close'].max() - df['close'].min())

    return df


# Feature aggregation for modeling / clustering
def extract_features(df):
    features = {
        "volatility_mean_15s": df["volatility_15s"].mean(),
        "mean_volume_surge": df["volume_surge"].mean(),
        "max_breakout_score": df["breakout_score"].max(),
        "impulse_events": df["impulse"].sum(),
        "fakeout_events": df["fakeout"].sum(),
        "accumulation_flags": df["accumulation"].sum(),
        "reversal_signals": df["micro_reversal"].sum(),
        "time_to_ath": df["close"].idxmax() - df.index[0],
        "time_to_dump": next((i for i, v in enumerate(df['big_dump']) if v), None),
        "whale_trails": df["whale_trail"].sum(),
        "ladder_sweeps": df["ladder_sweep"].sum(),
        "burnout_zones": df["burnout_zone"].sum(),
        "flash_dumps": df["flash_dump"].sum(),
        "rejections": df["rejection"].sum(),
        "imbalances": df["imbalance"].sum(),
        "double_tops": df["double_top"].sum(),
        "compression_flags": df["compression_zone"].sum(),
        "mean_reversion_rate": df["mean_reversion_rate"].mean(),
        "psi": df["psi"].iloc[-1],
    }
    return features


# Load and process a single coin CSV
def process_coin(file_path):
    df = pd.read_csv(file_path)
    print(df.head(2))
    df["timestamp"] = df["time"]
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['color'] = np.where(df['close'] > df['open'], 'green', 'red')
    df['index'] = df.index
    df.set_index('datetime', inplace=True)
    # print(df.columns)
    # print(df.head(2))
    print("Processing ", file_path)
    df = enrich_indicators(df)
    features = extract_features(df)
    return df, features


#! pip install pyarrow
def detect_timeframe(df):
    # Ensure datetime index
    diffs = pd.to_datetime(df["time"][100:200], unit="ms").diff().dropna()
    median_delta = diffs.median()
    # Convert timedelta to seconds
    seconds = median_delta.total_seconds()
    # Round to nearest int second, or keep as float for sub-second
    return seconds


# Main processor for a folder of CSVs
def process_all(all_csv_files, out_folder='features', force=False, allowed_timeframes=[1, 15]):
    os.makedirs(out_folder, exist_ok=True)  # Create output folder if missing

    for f in all_csv_files:
        base = os.path.basename(f).replace('.csv', '_features.parquet')
        out_path = os.path.join(out_folder, base)

        if os.path.exists(out_path) and not force:
            print(f"✅ Skipping {base} (already processed)")
            continue

        tf_seconds = detect_timeframe(pd.read_csv(f))
        print(f"Detected timeframe: {tf_seconds} seconds")

        if tf_seconds not in allowed_timeframes:
            print(f"⚠️ Skipping {base} due to timeframe {tf_seconds}s not in allowed {allowed_timeframes}")
            continue

        print(f"🔄 Processing {f}")
        df, meta = process_coin(f)
        df.to_parquet(out_path)
        print(f"💾 Saved to {out_path}")

    # results = {}
    # meta = {}
    # folder='candles_1s'
    # for fname in os.listdir(folder):
    #     symbol = fname.replace('.csv', '')
    #     try:
    #         df, features = process_coin(os.path.join(folder, fname))
    #         results[symbol] = df
    #         meta[symbol] = features
    #     except Exception as e:
    #         print(f"{symbol} failed: {e}")
    # return results, pd.DataFrame(meta).T


# Entry point
if __name__ == "__main__":
    # folder = 'candles_1s'
    # dfs, summary_df = process_all(folder)
    # summary_df.to_csv("coin_summary_features.csv")
    # print(summary_df.head())
    folder_path = 'I:\\axiomchart\\'
    file_csv = "15s_axiom_chart_bars_Ekv9HdumWqnXZgq5G6ge6bk1ZRHKXYC2WnSFL94sQmLJ_1752166201266.csv"

    # List all CSV files
    csv_files = [folder_path + f for f in os.listdir(folder_path) if f.endswith('.csv')]
    print(f"Found {len(csv_files)} CSV files.", [len(pd.read_csv(csv_files[df_index])) for df_index in range(len(csv_files))])
    df_index = 6

    file_csv = csv_files[df_index]
    print(file_csv)
    print("Processing Dataframe.")
    process_all(csv_files[:2])
    # df, f = process_coin(file_csv)
    # print(df.columns)
    # print(df.head())
    # print(f)
    # import matplotlib.pyplot as plt

    # # Highlight only rows where any event triggered
    # events = df[(df['impulse'] > 0) | (df['fakeout'] > 0) | (df['rejection'] > 0)]

    # plt.figure(figsize=(12, 6))
    # plt.plot(df['close'], label='Close Price', color='black')
    # plt.scatter(events.index, events['close'], c='red', label='Events', marker='o', s=15)
    # plt.title('Price with Event Markers')
    # plt.legend()
    # plt.show()
