
from dataclasses import asdict

import pandas as pd
import numpy as np


def find_rows_with_same_att(index, df, by_strategy_core=True, by_sizer=True, by_size=True, by_strategy_end=True, list_of_att=[]):
    main_row = df.iloc[index]
    filtered_df = df.copy()
    if by_sizer:
        print("Filtering by sizer_multiplier:", main_row["sizer_multiplier"])
        filtered_df = filtered_df[filtered_df["sizer_multiplier"] == main_row["sizer_multiplier"]]
    if by_size:
        print("Filtering by sizer_stake_cash:", main_row["sizer_stake_cash"], "sizer_percentage:", main_row["sizer_percentage"])
        filtered_df = filtered_df[filtered_df["sizer_stake_cash"] == main_row["sizer_stake_cash"]]
        filtered_df = filtered_df[filtered_df["sizer_percentage"] == main_row["sizer_percentage"]]
    if by_strategy_core:
        print("Filtering by strategy_tp:", main_row["strategy_tp"], "strategy_sl:", main_row["strategy_sl"], "strategy_buy_again:", main_row["strategy_buy_again"], "strategy_max_buy_count:", main_row["strategy_max_buy_count"])

        filtered_df = filtered_df[filtered_df["strategy_tp"] == main_row["strategy_tp"]]
        filtered_df = filtered_df[filtered_df["strategy_sl"] == main_row["strategy_sl"]]
        filtered_df = filtered_df[filtered_df["strategy_buy_again"] == main_row["strategy_buy_again"]]
        filtered_df = filtered_df[filtered_df["strategy_max_buy_count"] == main_row["strategy_max_buy_count"]]

    if by_strategy_end:
        print("Filtering by strategy_end_mcap:", main_row["strategy_end_mcap"], "strategy_dead_coin_market_cap:", main_row["strategy_dead_coin_market_cap"])
        filtered_df = filtered_df[filtered_df["strategy_end_mcap"] == main_row["strategy_end_mcap"]]
        filtered_df = filtered_df[filtered_df["strategy_dead_coin_market_cap"] == main_row["strategy_dead_coin_market_cap"]]

    if len(list_of_att) > 0:
        for att in list_of_att:
            filtered_df = filtered_df[filtered_df[att] == main[att]]
    return filtered_df


def safe_equals(df, key, val):
    """Return boolean mask treating NaN == None and None == NaN as equal."""
    if key not in df.columns:
        return pd.Series(True, index=df.index)  # ignore non-existent key

    col = df[key]
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return col.isna()
    else:
        # also count NaN as non-match
        return col.fillna(np.nan) == val


def if_duplicate(file_to_run,
                 sizer_class,
                 strategy_class,
                 strategy_params,
                 sizer_params,
                 config):
    """
    Check if a run with same strategy, sizer, and params already exists in merged_df.
    Returns True if duplicate found, False otherwise.
    """
    merged_df = pd.read_csv("/content/drive/MyDrive/charts/merged_df.csv")
    print(len(merged_df))
    # Convert dataclass config to dict
    config_dict = asdict(config) if hasattr(config, "__dataclass_fields__") else config

    # Start filtering
    df_filtered = merged_df.copy()

    # Strategy and sizer match
    if "strategy" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["strategy"] == strategy_class.__name__]
    if "sizer" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["sizer"] == sizer_class.__name__]
    print(len(df_filtered))

    # Check all matching keys in params
    for k, v in strategy_params.items():
        k = "strategy_" + k
        if k in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[k] == v]
    print(len(df_filtered))

    for k, v in sizer_params.items():
        k = "sizer_" + k
        if k in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[k] == v]
    print(len(df_filtered))

    for k, v in config_dict.items():
        k = "runner_" + k
        if k in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[k] == v]
    print(len(df_filtered))

    # If any row remains → duplicate
    duplicate_found = not df_filtered.empty

    if duplicate_found:
        print("⚠️ Duplicate found for this configuration.", len(df_filtered))
        print(df_filtered.head())  # optional: preview matching entry
    else:
        print("✅ Unique configuration. Proceed with run.")

    return duplicate_found
