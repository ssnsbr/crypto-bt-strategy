import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
# from ..utils.utils import format_marketcap
# from utils.utils import format_marketcap
from zigzag import *
# from utils.data_utils import ready_df


def format_marketcap(marketcap):
    """
    Calculates market cap and formats it to K or M.
    """
    if marketcap >= 1_000_000_000:  # Billions
        return f"{marketcap / 1_000_000_000:.2f}B!"
    elif marketcap >= 1_000_000:  # Millions
        return f"{marketcap / 1_000_000:.2f}M"
    elif marketcap >= 1_000:  # Thousands
        return f"{marketcap / 1_000:.2f}K"
    else:
        return f"{marketcap:.2f}"  # Less than a thousand, show raw value


def zigzag_percent_changes(prices, percent_threshold=0.3):
    prices = np.array(prices)
    pivots = [0]  # first index always a pivot
    last_pivot = 0
    direction = 0  # 0 = unknown, 1 = up, -1 = down

    for i in range(1, len(prices)):
        change = (prices[i] - prices[last_pivot]) / prices[last_pivot]
        if direction == 0:
            if abs(change) >= percent_threshold:
                direction = np.sign(change)
                pivots.append(i)
                last_pivot = i
        elif direction == 1:  # up
            if prices[i] > prices[last_pivot]:
                pivots[-1] = i
                last_pivot = i
            elif prices[i] < prices[last_pivot] * (1 - percent_threshold):
                direction = -1
                pivots.append(i)
                last_pivot = i
        elif direction == -1:  # down
            if prices[i] < prices[last_pivot]:
                pivots[-1] = i
                last_pivot = i
            elif prices[i] > prices[last_pivot] * (1 + percent_threshold):
                direction = 1
                pivots.append(i)
                last_pivot = i

    pivot_idxs = np.array(pivots)
    pivot_prices = prices[pivot_idxs]

    # Calculate percent changes
    pct_changes = np.diff(pivot_prices) / pivot_prices[:-1] * 100

    # Relative to previous wave
    relative_changes = [np.nan]  # first one has no prior wave
    for i in range(1, len(pct_changes)):
        prev = abs(pct_changes[i - 1])
        curr = abs(pct_changes[i])
        relative_changes.append(curr / prev if prev != 0 else np.nan)

    return pivot_idxs, pivot_prices, pct_changes, relative_changes


def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def get_pivots(df, up_thresh=0.3, down_thresh=-0.3):
    # Example: your price series
    # prices = pd.read_csv(df)['close'].values
    prices = df['close'].values
    timestamps = df.index  # assuming index is datetime
    # Calculate moving average of volume
    df['volume_ma_15'] = df['volume'].rolling(window=15).mean()
    df['volume_ma_30'] = df['volume'].rolling(window=30).mean()
    df['volume_ma_60'] = df['volume'].rolling(window=60).mean()

    df['rsi_14'] = calculate_rsi(df['close'], period=14).fillna(50)
    df['rsi_30'] = calculate_rsi(df['close'], period=30).fillna(50)
    df['rsi_60'] = calculate_rsi(df['close'], period=60).fillna(50)

    pivots = peak_valley_pivots(prices, up_thresh=up_thresh, down_thresh=down_thresh)
    # pivot_indices, pivot_prices, pct_changes, relative_changes = zigzag_percent_changes(prices, 0.1)
    # df["pivots"] = pivots
    # df["pivots"] = pivots

    # Get pivot indices and values
    # ts_pivots = ts_pivots[pivots != 0]
    # ts_pivots = pd.Series(X, index=X.index)
    pdf = pd.DataFrame()
    pivot_indices = np.where(pivots != 0)[0]
    pivot_prices = prices[pivot_indices]
    pivot_timestamp = df["timestamp"].values[pivot_indices]
    pivot_times = df["datetime"].values[pivot_indices]

    pdf["rsi_14"] = df["rsi_14"].values[pivot_indices]
    pdf["rsi_30"] = df["rsi_30"].values[pivot_indices]
    pdf["rsi_60"] = df["rsi_60"].values[pivot_indices]

    pdf["volume_ma_15"] = df["volume_ma_15"].values[pivot_indices]
    pdf["volume_ma_30"] = df["volume_ma_30"].values[pivot_indices]
    pdf["volume_ma_60"] = df["volume_ma_60"].values[pivot_indices]

    # Example data
    pdf["pivot_idx"] = pivot_indices
    # pdf["pivot_idx"] = df.index[pivot_indices]
    pdf["pivot_prices"] = pivot_prices
    pdf["pivot_times"] = pivot_times
    pdf["pivot_timestamp"] = pivot_timestamp

    return df, pdf


def pivot_changes(pdf):
    pivot_prices = pdf["pivot_prices"]
    pct_changes = pivot_prices.pct_change() * 100
    raw_changes = pivot_prices.diff()
    raw_changes_ratio = (raw_changes / raw_changes.shift(1)).abs()
    pdf["pct_changes"] = pct_changes
    pdf["raw_changes"] = raw_changes

    pdf["raw_retr"] = raw_changes_ratio
    pdf["pct_retr"] = (pct_changes / pct_changes.shift(1)).abs()

    pdf["raw_ABC"] = (raw_changes / raw_changes.shift(2)).abs()
    pdf["pct_ABC"] = (pct_changes / pct_changes.shift(2)).abs()

    pdf["time_len"] = pdf["pivot_timestamp"].diff() / 1000
    pdf["index_len"] = pdf["pivot_idx"].diff()

    pdf["time_retr"] = (pdf["time_len"] / pdf["time_len"].shift(1)).abs()
    pdf["index_retr"] = (pdf["index_len"] / pdf["index_len"].shift(1)).abs()

    pdf["time_ABC"] = (pdf["time_len"] / pdf["time_len"].shift(2)).abs()
    pdf["index_ABC"] = (pdf["index_len"] / pdf["index_len"].shift(2)).abs()

    pdf["time_index_ratio"] = pdf["index_len"] / pdf["time_len"]

    return pdf


def get_relative_changes(pdf):
    pivot_prices = pdf["pivot_prices"]

    # Relative % change to previous wave (compare size of waves)
    wave_heights = np.abs(pivot_prices[1:] - pivot_prices[:-1])
    relative_changes = np.zeros_like(wave_heights)

    for i in range(1, len(wave_heights)):
        prev_wave = wave_heights[i - 1]
        curr_wave = wave_heights[i]
        relative_changes[i] = 100 * curr_wave / prev_wave if prev_wave != 0 else np.nan
    return relative_changes


def plot_pivot_1(df, pdf):
    pivot_prices = pdf["pivot_prices"]
    pivot_idx = pdf["pivot_idx"]
    pct_changes = pdf["pct_changes"]
    relative_changes = pdf["raw_changes_ratio"]
    ath_rel = pdf["ath_rel"]

    migration_price = 70_000
    migration_idx = df[df["close"] > migration_price].index
    first_migration_time = migration_idx[0]
    migration_value = df.loc[first_migration_time, "close"]

    # Plot the main chart
    timestamps = df.index
    plt.figure(figsize=(14, 6))
    plt.plot(timestamps, df["close"], label='Price', alpha=0.6)
    plt.plot(pivot_idx, pivot_prices, 'ro-', label='ZigZag Pivots')
    plt.plot(first_migration_time, migration_value, 'mo')  # magenta dot
    # plt.axvline(first_migration_time, color='purple', linestyle='--', alpha=0.6, label='Migration >70K')
    plt.annotate("Migration\n>70K",
                 (first_migration_time, migration_value),
                 textcoords="offset points",
                 xytext=(0, 80),  # label 40 points above the dot
                 ha='center',
                 fontsize=9,
                 color='purple',
                 arrowprops=dict(arrowstyle='-', color='purple', alpha=0.6, lw=1.5))  # vertical line

    # Add labels with both % values
    for i in range(1, len(pivot_prices)):
        x = pivot_idx[i]
        y = pivot_prices[i]
        abs_pct = pct_changes[i]
        rel_pct = relative_changes[i] if i < len(relative_changes) else np.nan
        color = 'green' if abs_pct > 0 else 'red'
        y_offset = 10 if abs_pct > 0 else -50  # green above, red below

        plt.annotate(f"{abs_pct:.1f}%\n({rel_pct:.2f}X)\n{format_marketcap(y)}\n{ath_rel[i]:.2f}ath", (x, y),
                     textcoords="offset points", xytext=(0, y_offset),
                     ha='center', fontsize=9,
                     color=color)

    plt.title("ZigZag: Absolute % and Wave-relative %")
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def after_migration(df, migration_price=70_000):
    pivot_prices = df["pivot_prices"]

    migration_idx = df[df["pivot_prices"] > migration_price].index
    first_migration_time = None
    if not migration_idx.empty:
        first_migration_time = migration_idx[0]

    df["after_migraion"] = pivot_prices.index.to_series().apply(
        lambda idx: 0 if first_migration_time is None or idx < first_migration_time else 1
    )
    return df


def ath_rel(pdf):
    pivot_prices = pdf["pivot_prices"]
    ath_index = pivot_prices.idxmax()
    ath = pivot_prices.max()
    pdf["ath_rel"] = pivot_prices / ath
    # Mark position relative to ATH
    pdf["after_ath"] = pivot_prices.index.to_series().apply(
        lambda idx: -1 if idx < ath_index else (1 if idx > ath_index else 0)
    )

    start_timestamp = pdf["pivot_timestamp"].values[0]
    pdf["age"] = pdf["pivot_timestamp"] - start_timestamp
    pdf["age"] = pdf["age"] / 1000
    ath_timestamp = pdf["pivot_timestamp"].values[ath_index]
    pdf["age_ath_rel"] = pdf["pivot_timestamp"] - ath_timestamp
    pdf["age_ath_rel"] = (pdf["age_ath_rel"] / 1000).abs()

    pdf["ath_to_dis"] = pdf.index - ath_index
    pdf["ath_to_dis"] = pdf["ath_to_dis"].abs()

    return pdf


def custom_print(pdf):
    pivot_prices = pdf["pivot_prices"]
    ath_index = pivot_prices.idxmax()

    def get_string(dataframe):
        return [f'{"↑" if row["pct_changes"]>0 else "↓" } {row["pct_changes"]}({format_marketcap(row["pivot_prices"]):{row["ath_rel"]}}),' for _, row in dataframe.iterrows()
                ]
    logstr_1 = get_string(pdf[:ath_index])
    logstr_2 = get_string(pdf[ath_index:])
    print("*" * 20)
    print(logstr_1, f"**ATH:{format_marketcap(pivot_prices.max())}**")
    print(f"**--- ATH :{format_marketcap(pivot_prices.max())} ---**")
    print(logstr_2)
    print("*" * 20)

    def get_means(ser):
        downer = ser[ser < 0]
        uptre = ser[ser >= 0]
        return f" mean ↓:{downer.mean():.2f} ↑:{uptre.mean():.2f}, count=↓:{len(downer)} ↑:{len(uptre)}   sums: ↓:{downer.sum():.2f} ↑:{uptre.sum():.2f}"

    print(get_means(pdf[:ath_index]["pct_changes"]), "**ATH**", get_means(pdf[ath_index:]["pct_changes"]))


def ready_df(df_input, mcap=False):  # Renamed df to df_input to avoid conflict with local variable
    print("Preparing dataframe with size ", len(df_input))
    df_input["timestamp"] = df_input["time"]  # Assuming original 'time' is the ms timestamp
    df_input['time'] = pd.to_datetime(df_input['timestamp'], unit='ms')

    # Ensure your column names exactly match what Backtrader expects or map them.
    # Backtrader expects 'datetime', 'open', 'high', 'low', 'close', 'volume' by default.
    # If your original CSV columns are different, you'd map them here.
    # For example, if your original CSV has 'price_open', rename it to 'open'.

    # Your current scaling:
    if mcap:
        for c in ["open", "high", "low", "close"]:
            df_input[c] = df_input[c] * 1_000_000_000

    # Add color column (not directly used by Backtrader data feed, but fine to keep in DF)
    df_input['color'] = df_input.apply(lambda row: 'green' if row['close'] > row['open'] else 'red', axis=1)

    # Crucially, rename the 'time' column to 'datetime' as Backtrader expects 'datetime'
    df_input = df_input.rename(columns={'time': 'datetime'})

    return df_input


def main(df_file, log=False, draw=False, log_custom_print=False, up_thresh=0.4, down_thresh=-0.4):
    df, pdf = get_pivots(ready_df(pd.read_csv(df_file), True), up_thresh=up_thresh, down_thresh=down_thresh)
    pivot_indices = pdf["pivot_idx"]
    pivot_prices = pdf["pivot_prices"]
    pivot_idx = pdf["pivot_idx"]
    pdf = ath_rel(pdf)
    pdf = pivot_changes(pdf)
    pdf = after_migration(pdf)
    pdf["next_wave_pct"] = pdf["pct_changes"].shift(-1)
    # relative_changes = get_relative_changes(pdf)
    # pdf["relative_changes"] = relative_changes
    if log_custom_print:
        custom_print(pdf)
    pdf["sort_index"] = pdf.index

    # pdf["after_before_ration"] = pdf["pct_changes"] / pdf["next_wave_pct"] * -1
    pdf["bef_aft_pct_ratio"] = pdf["next_wave_pct"] / pdf["pct_changes"] * -1

    pdf["name"] = os.path.basename(df_file)

    if log:
        print(df_file)
        print(pdf)

    if draw:
        plot_pivot_1(df, pdf)
    return pdf


def make_save_pdf(csv_files_1s, output_folder='/content/drive/MyDrive/charts/1s_pivots/'):
    os.makedirs(output_folder, exist_ok=True)
    for i, path in enumerate(csv_files_1s):
        if i % 50 == 0:
            print(i, "of", len(csv_files_1s))
        try:
            pdf = main(path)
            name = os.path.basename(path).replace(".csv", "_pdf.csv")
            pdf.to_csv(os.path.join(output_folder, name), index=False)
        except Exception as e:
            print(f"Error in {path}: {e}")


def read_concat_pdf(pdfs_folder='/content/drive/MyDrive/charts/1s_pivots/', full_save_path="/content/drive/MyDrive/charts/all_pdf_combined.csv"):
    csv_files_pdf = [pdfs_folder + f for f in os.listdir(pdfs_folder) if f.endswith('.csv')]
    all_pdfs = []
    for i, path in enumerate(csv_files_pdf):
        if i % 50 == 0:
            print(i, "of", len(csv_files_pdf))
        try:
            pdf = pd.read_csv(path)
            all_pdfs.append(pdf)
        except Exception as e:
            print(f"Error in {path}: {e}")

    # Combine and save
    df_combined = pd.concat(all_pdfs, ignore_index=True)
    df_combined.to_csv(full_save_path, index=False)


def make_save_all(csv_files_1s, full_save_path="/content/drive/MyDrive/charts/all_pdf_combined.csv"):
    # Both
    all_pdfs = []

    for i, path in enumerate(csv_files_1s):
        if i % 50 == 0:
            print(i, "of", len(csv_files_1s))
        try:
            pdf = main(path)
            name = os.path.basename(path).replace(".csv", "_pdf.csv")
            all_pdfs.append(pdf)

            # pdf.to_csv(os.path.join(output_folder, name), index=False)
        except Exception as e:
            print(f"Error in {path}: {e}")

    # # Combine and save
    df_combined = pd.concat(all_pdfs, ignore_index=True)
    df_combined.to_csv(full_save_path, index=False)
    print(f"saved {len(df_combined)} rows in ", full_save_path)


# main("I:\\axiomchart\\15s_axiom_chart_bars_Ekv9HdumWqnXZgq5G6ge6bk1ZRHKXYC2WnSFL94sQmLJ_1752166201266.csv")
