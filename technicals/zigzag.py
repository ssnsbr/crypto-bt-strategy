import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
# from ..utils.utils import format_marketcap
# from utils.utils import format_marketcap
# from zigzag import peak_valley_pivots
from zigzag import *
from utils.data_utils import ready_df


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


def get_pivots(df, up_thresh=0.3, down_thresh=-0.3):
    # Example: your price series
    # prices = pd.read_csv(df)['close'].values
    prices = df['close'].values
    timestamps = df.index  # assuming index is datetime

    # Detect pivots (e.g., require ±30% move to switch trend)
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
    raw_changes_divided = (raw_changes / raw_changes.shift(1)).abs()
    pdf["pct_changes"] = pct_changes
    pdf["raw_changes"] = raw_changes
    pdf["raw_changes_divided"] = raw_changes_divided
    pdf["time_len"] = pdf["pivot_timestamp"].diff() / 1000
    pdf["index_len"] = pdf["pivot_idx"].diff()

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
    relative_changes = pdf["raw_changes_divided"]
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


def ath_rel(pdf):
    pivot_prices = pdf["pivot_prices"]
    ath_index = pivot_prices.idxmax()
    ath = pivot_prices.max()
    pdf["ath_rel"] = pivot_prices / ath
    # Mark position relative to ATH
    pdf["after_ath"] = pivot_prices.index.to_series().apply(
        lambda idx: -1 if idx < ath_index else (1 if idx > ath_index else 0)
    )
    return pdf


def custom_print(pdf):
    pivot_prices = pdf["pivot_prices"]
    ath_index = pivot_prices.idxmax()

    def get_string(dataframe):
        return [f'{"↑" if row["pct_changes"]>0 else "↓" } {row["pct_changes"]}({format_marketcap(row["pivot_prices"]):{row["ath_rel"]}}),' for _, row in dataframe.iterrows()
                ]
    logstr_1 = get_string(pdf[:ath_index])
    logstr_2 = get_string(pdf[ath_index:])
    print(logstr_1, f"**ATH:{format_marketcap(pivot_prices.max())}**")
    print(f"**ATH:{format_marketcap(pivot_prices.max())}**")
    print(logstr_2)

    def get_means(ser):
        downer = ser[ser < 0]
        uptre = ser[ser >= 0]
        return f" mean ↓:{downer.mean():.2f} ↑:{uptre.mean():.2f}, count=↓:{len(downer)} ↑:{len(uptre)}   sums: ↓:{downer.sum():.2f} ↑:{uptre.sum():.2f}"

    print(get_means(pdf[:ath_index]["pct_changes"]), "**ATH**", get_means(pdf[ath_index:]["pct_changes"]))


def main(df_file, log=False, draw=False):
    df, pdf = get_pivots(ready_df(pd.read_csv(df_file), True), 0.4, -0.4)
    pivot_indices = pdf["pivot_idx"]
    pivot_prices = pdf["pivot_prices"]
    pivot_idx = pdf["pivot_idx"]
    pdf = ath_rel(pdf)
    pivot_changes(pdf)
    pdf["next_wave_pct_changes"] = pdf["pct_changes"].shift(-1)
    # relative_changes = get_relative_changes(pdf)
    # pdf["relative_changes"] = relative_changes
    custom_print(pdf)
    pdf["name"] = os.path.basename(df_file)
    pdf["sort_index"] = pdf.index
    if log:
        print(df_file)
        print(pdf)

    if draw:
        plot_pivot_1(df, pdf)
    return pdf


def make_save_pdf(csv_files_1s, output_folder='/content/drive/MyDrive/charts/1s_pivots/'):
    os.makedirs(output_folder, exist_ok=True)
    for i, path in enumerate(csv_files_1s):
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
        if i % 20 == 0:
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
