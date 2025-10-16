
# --- Your DataFrame Preparation Function ---
import os
import json
import pandas as pd


def read_all_detail_files():
    # Collect all detail files
    base_path = "/content/drive/MyDrive/charts/results/"
    dfs = []

    for fname in os.listdir(base_path):
        if fname.endswith("_details.txt") and fname.startswith("details"):
            filepath = os.path.join(base_path, fname)

            try:
                thisdf = read_detail_file(filepath)
                dfs.append(thisdf)
            except Exception as e:
                print(f"⚠️ Skipping {fname}: {e}")

    details_df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    details_df = details_df[details_df["len"] > 50]

    print(details_df.columns)
    return details_df


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


def read_detail_file(filepath: str) -> pd.DataFrame:
    """
    Reads a 'detail*.txt' file containing JSON, returns a single-row DataFrame.
    Nested dicts (strategy_params, sizer_params) are flattened.
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    # Sometimes file contains JSON string instead of dict → decode again
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            raise ValueError(f"File {filepath} does not contain valid JSON")

    # Flatten nested dictionaries
    flat_data = {
        "strategy": data.get("strategy"),
        "sizer": data.get("sizer"),
        "time": data.get("time"),
        "len": data.get("len")
    }

    for k, v in data.get("strategy_params", {}).items():
        flat_data[f"strategy_{k}"] = v

    for k, v in data.get("sizer_params", {}).items():
        flat_data[f"sizer_{k}"] = v

    # Keep filename too (optional, helps debugging)
    flat_data["filename"] = os.path.basename(filepath)[8:-12] + "_memes.csv"

    return pd.DataFrame([flat_data])
