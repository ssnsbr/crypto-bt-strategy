import pandas as pd


def before_ath(df, after_migration=False):
    if after_migration:
        df[(df["after_ath"] < 0) & (df["after_migraion"])]
    return df[df["after_ath"] < 0]


def at_ath(df):
    return df[df["after_ath"] == 0]


def after_ath(df):
    return df[df["after_ath"] > 0]


def up_trend(df):
    return df[df["pct_changes"] >= 0]


def down_trend(df):
    return df[df["pct_changes"] < 0]


def get_df(df, time_ath="after", trend="up"):
    if time_ath == "after":
        cdf = after_ath(df)
    else:
        cdf = before_ath(df)
    if trend == "up":
        fdf = up_trend(cdf)
    else:
        fdf = down_trend(cdf)
    return fdf


def ath_after_before_ratio(pdf, name=""):
    """
    Calculates and prints the ratio of data points after and before
    a coin's All-Time High (ATH), along with various trend statistics.

    Args:
      pdf (pd.DataFrame): The input DataFrame containing cryptocurrency data.
      name (str): The name of the file or data source for printing.
    """
    print("What is Ration of Before ATH and After ATH for each coin?", name.split("/")[-1])

    # Use a list of dictionaries to store results for each coin
    results = []

    # Iterate through each unique coin
    for meme in pd.unique(pdf["name"]):
        coinpdf = pdf[pdf["name"] == meme].copy()

        # Perform all necessary filtering
        bef_ath_cdf = before_ath(coinpdf)
        aft_ath_cdf = after_ath(coinpdf)
        bef_ath_aft_mig_cdf = before_ath(coinpdf, True)
        ath = at_ath(coinpdf)

        cdf_af_up = up_trend(aft_ath_cdf)
        cdf_af_down = down_trend(aft_ath_cdf)
        cdf_bf_up = up_trend(bef_ath_cdf)
        cdf_bf_down = down_trend(bef_ath_cdf)
        cdf_bef_aft_mig_up = up_trend(bef_ath_aft_mig_cdf)
        cdf_bef_aft_mig_down = down_trend(bef_ath_aft_mig_cdf)

        # Create a dictionary of results for the current coin
        coin_result = {
            "name": meme,
            "len": len(coinpdf),
            "ath_pct": ath["pct_changes"].values[0],
            "ath_next_pct": ath["next_wave_pct"].values[0],
            "bef_counts": len(bef_ath_cdf),
            "aft_counts": len(aft_ath_cdf),
            "bef_up_counts": len(cdf_bf_up),
            "bef_down_counts": len(cdf_bf_down),
            "aft_up_counts": len(cdf_af_up),
            "aft_down_counts": len(cdf_af_down),
            "bef_aft_mig_counts": len(bef_ath_aft_mig_cdf),
            "bef_aft_mig_up_counts": len(cdf_bef_aft_mig_up),
            "bef_aft_mig_down_counts": len(cdf_bef_aft_mig_down),
            "bef_up_pct_mean": cdf_bf_up["pct_changes"].mean() if not cdf_bf_up.empty else 0,
            "bef_down_pct_mean": cdf_bf_down["pct_changes"].mean() if not cdf_bf_down.empty else 0,
            "aft_up_pct_mean": cdf_af_up["pct_changes"].mean() if not cdf_af_up.empty else 0,
            "aft_down_pct_mean": cdf_af_down["pct_changes"].mean() if not cdf_af_down.empty else 0,
            "bef_aft_mig_up_pct_mean": cdf_bef_aft_mig_up["pct_changes"].mean() if not cdf_bef_aft_mig_up.empty else 0,
            "bef_aft_mig_down_pct_mean": cdf_bef_aft_mig_down["pct_changes"].mean() if not cdf_bef_aft_mig_down.empty else 0,
            "bef_up_time_len_mean": cdf_bf_up["time_len"].mean() if "time_len" in cdf_bf_up.columns and not cdf_bf_up.empty else 0,
            "bef_down_time_len_mean": cdf_bf_down["time_len"].mean() if "time_len" in cdf_bf_down.columns and not cdf_bf_down.empty else 0,
            "aft_up_time_len_mean": cdf_af_up["time_len"].mean() if "time_len" in cdf_af_up.columns and not cdf_af_up.empty else 0,
            "aft_down_time_len_mean": cdf_af_down["time_len"].mean() if "time_len" in cdf_af_down.columns and not cdf_af_down.empty else 0,
            "bef_aft_mig_up_time_len_mean": cdf_bef_aft_mig_up["time_len"].mean() if "time_len" in cdf_bef_aft_mig_up.columns and not cdf_bef_aft_mig_up.empty else 0,
            "bef_aft_mig_down_time_len_mean": cdf_bef_aft_mig_down["time_len"].mean() if "time_len" in cdf_bef_aft_mig_down.columns and not cdf_bef_aft_mig_down.empty else 0
        }

        # Append the dictionary to the main list
        results.append(coin_result)

    # Create the final results DataFrame from the list of dictionaries
    mdf = pd.DataFrame(results)

    # Calculate the ratio_counts after creating the DataFrame
    mdf["ratio_counts"] = mdf["aft_counts"] / mdf["bef_counts"]
    return mdf, mdf.describe()
    # print(mdf.head(2).to_string(float_format="%.4f", max_rows=10))
    # print(mdf.describe().to_string(float_format="%.4f", max_rows=10))
