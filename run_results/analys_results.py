import numpy as np
import pandas as pd
import os


def read_analysers(strategy):
    """ For each token, This happens after run to collect data from analyzers """
    sharpe_ratio = strategy.analyzers.mysharpe.get_analysis().get('sharperatio', 'N/A')
    drawdown_data = strategy.analyzers.mydrawdown.get_analysis().get('max', {})
    trade_data = strategy.analyzers.mytradeanalyzer.get_analysis()
    returns_data = strategy.analyzers.myreturns.get_analysis()
    duration_data = strategy.analyzers.mytradeduration.get_analysis()
    vwr_data = strategy.analyzers.myvwr.get_analysis()
    sqn_data = strategy.analyzers.mysqn.get_analysis()
    pyfolio_data = strategy.analyzers.mypyfolio.get_analysis()
    counter_data = strategy.analyzers.mybacounteranalyzer.get_analysis()

    # --- extract numeric pnl values safely ---
    won_pnl = trade_data.get('won', {}).get('pnl', {}).get('total', 0)
    lost_pnl = trade_data.get('lost', {}).get('pnl', {}).get('total', 0)
    print(trade_data)
    mcap_supply = 1_000_000_000
    # Build result dictionary
    analysis_results = {
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': pyfolio_data.get('sortino', 'N/A'),
        'calmar_ratio': pyfolio_data.get('calmar', 'N/A'),
        'vwr': vwr_data.get('vwr', 'N/A'),
        'sqn': sqn_data.get('sqn', 'N/A'),
        'max_drawdown': drawdown_data.get('drawdown', 'N/A'),
        'avg_drawdown': strategy.analyzers.mydrawdown.get_analysis().get('drawdown', 'N/A'),

        # --- Trade metrics ---
        'total_trades': trade_data.get('total', {}).get('closed', 0),
        # 'open_trades': trade_data.get('total', {}).get('open', 0),
        # 'closed_trades': trade_data.get('total', {}).get('closed', 0),
        # Streaks
        'current_winning_streak': trade_data.get('streak', {}).get('won', {}).get('current', 0),
        'longest_winning_streak': trade_data.get('streak', {}).get('won', {}).get('longest', 0),
        'current_losing_streak': trade_data.get('streak', {}).get('lost', {}).get('current', 0),
        'longest_losing_streak': trade_data.get('streak', {}).get('lost', {}).get('longest', 0),
        # PnL
        'gross_total_pnl': trade_data.get('pnl', {}).get('gross', {}).get('total', 0.0) / mcap_supply,
        'gross_average_pnl': trade_data.get('pnl', {}).get('gross', {}).get('average', 0.0) / mcap_supply,
        'net_total_pnl': trade_data.get('pnl', {}).get('net', {}).get('total', 0.0) / mcap_supply,
        'net_average_pnl': trade_data.get('pnl', {}).get('net', {}).get('average', 0.0) / mcap_supply,

        # Winning trades
        'winning_trades': trade_data.get('won', {}).get('total', 0),
        'winning_total_pnl': trade_data.get('won', {}).get('pnl', {}).get('total', 0.0) / mcap_supply,
        'winning_avg_pnl': trade_data.get('won', {}).get('pnl', {}).get('average', 0.0) / mcap_supply,
        'winning_max_pnl': trade_data.get('won', {}).get('pnl', {}).get('max', 0.0) / mcap_supply,

        # Losing trades
        'losing_trades': trade_data.get('lost', {}).get('total', 0),
        'losing_total_pnl': trade_data.get('lost', {}).get('pnl', {}).get('total', 0.0) / mcap_supply,
        'losing_avg_pnl': trade_data.get('lost', {}).get('pnl', {}).get('average', 0.0) / mcap_supply,
        'losing_max_pnl': trade_data.get('lost', {}).get('pnl', {}).get('max', 0.0) / mcap_supply,

        # Long trades
        # 'long_trades': trade_data.get('long', {}).get('total', 0),
        # 'long_won': trade_data.get('long', {}).get('won', 0),
        # 'long_lost': trade_data.get('long', {}).get('lost', 0),
        # 'long_total_pnl': trade_data.get('long', {}).get('pnl', {}).get('total', 0.0) / mcap_supply,
        # 'long_avg_pnl': trade_data.get('long', {}).get('pnl', {}).get('average', 0.0) / mcap_supply,

        # Short trades
        # 'short_trades': trade_data.get('short', {}).get('total', 0),
        # 'short_won': trade_data.get('short', {}).get('won', 0),
        # 'short_lost': trade_data.get('short', {}).get('lost', 0),
        # 'short_total_pnl': trade_data.get('short', {}).get('pnl', {}).get('total', 0.0),
        # 'short_avg_pnl': trade_data.get('short', {}).get('pnl', {}).get('average', 0.0),

        # Trade duration stats
        'time_total': trade_data.get('len', {}).get('total', 0),
        'time_average': trade_data.get('len', {}).get('average', 0.0),
        'time_max': trade_data.get('len', {}).get('max', 0),
        'time_min': trade_data.get('len', {}).get('min', 0),

        # Winning trade durations
        'time_won_total': trade_data.get('len', {}).get('won', {}).get('total', 0),
        'time_won_avg': trade_data.get('len', {}).get('won', {}).get('average', 0.0),
        'time_won_max': trade_data.get('len', {}).get('won', {}).get('max', 0),
        'time_won_min': trade_data.get('len', {}).get('won', {}).get('min', 0),

        # Losing trade durations
        'time_lost_total': trade_data.get('len', {}).get('lost', {}).get('total', 0),
        'time_lost_avg': trade_data.get('len', {}).get('lost', {}).get('average', 0.0),
        'time_lost_max': trade_data.get('len', {}).get('lost', {}).get('max', 0),
        'time_lost_min': trade_data.get('len', {}).get('lost', {}).get('min', 0),

        'win_rate': (
            trade_data.get('won', {}).get('total', 0) /
            trade_data.get('total', {}).get('closed', 1)
        ) if trade_data.get('total', {}).get('closed', 0) > 0 else 0,
        'avg_trade_pnl': trade_data.get('pnl', {}).get('average', 0),
        'best_trade_pnl': trade_data.get('pnl', {}).get('max', 0),
        'worst_trade_pnl': trade_data.get('pnl', {}).get('min', 0),

        # --- profit factor ---
        'profit_factor': (
            (won_pnl / abs(lost_pnl)) if lost_pnl else 'N/A'
        ),

        # --- Returns ---
        'annualized_return': returns_data.get('rnorm100', 'N/A'),
        'cumulative_return': returns_data.get('rtot', 'N/A'),

        # --- Trade duration stats ---
        'trade_duration_mean': duration_data.get('mean', 0),
        'trade_duration_median': duration_data.get('median', 0),
        'trade_duration_min': duration_data.get('min', 0),
        'trade_duration_max': duration_data.get('max', 0),
        'trade_duration_std': duration_data.get('std', 0),
        'trade_duration_count': duration_data.get('count', 0),
    }
    # counter_data:
    # [RUN]  ib_count 0
    # [RUN]  tp_count 0
    # [RUN]  sl_count 0
    # [RUN]  ba_round_count 0
    # [RUN]  ba_count 0
    # [RUN]  counter_list []
    return analysis_results | counter_data


def analys_trades(df, name=""):
    #  Unnamed: 0        coin  start_value  final_value  sharpe_ratio    max_drawdown  total_trades  winning_trades  losing_trades  annualized_return
    # + pnl_perc + value_pnl + final_value_numeric + start_value_numeric
    # print("analys_trades:"+name,"\n",df)
    pnl_perc_stats = df["pnl%"].describe()

    return {
        name + "mean_ath": df["ath"].mean() if "ath" in df and not df["ath"].empty else 0,
        name + "mean_time_len": df["time_len"].mean() if "time_len" in df and not df["time_len"].empty else 0,
        name + "mean_time_to_ath": df["time_to_ath"].mean() if "time_to_ath" in df and not df["time_to_ath"].empty else 0,
        name + "mean_time_after_ath": df["time_after_ath"].mean() if "time_after_ath" in df and not df["time_after_ath"].empty else 0,

        name + "cnt_trades": df["total_trades"].sum(),
        name + "mean_cnt_trades": df["total_trades"].mean(),
        name + "total_cnt_sl": df["losing_trades"].sum(),
        name + "mean_cnt_sl": df["losing_trades"].mean(),
        name + "total_cnt_tp": df["winning_trades"].sum(),
        name + "mean_cnt_tp": df["winning_trades"].mean(),
        #
        name + "total_annualized_return": df["annualized_return"].sum(),
        name + "mean_annualized_return": df["annualized_return"].mean(),
        name + "mean_max_drawdown": df["max_drawdown"].mean(),
        #
        name + 'mean_pnl%': pnl_perc_stats['mean'],
        name + 'max_pnl%': pnl_perc_stats['max'],
        name + 'min_pnl%': pnl_perc_stats['min'],
        name + 'std_pnl%': pnl_perc_stats['std'],
        name + 'median_pnl%': pnl_perc_stats['50%'],
        #
        name + "time_average": df["time_average"].mean() if "time_average" in df and not df["time_average"].empty else 0,
        name + "time_won_avg": df["time_won_avg"].mean() if "time_won_avg" in df and not df["time_won_avg"].empty else 0,
        name + "time_lost_avg": df["time_lost_avg"].mean() if "time_lost_avg" in df and not df["time_lost_avg"].empty else 0,
        #
        name + "mean_InitBuy": df["ib_count"].mean() if "ib_count" in df and not df["ib_count"].empty else 0,
        name + "mean_TP_count": df["tp_count"].mean() if "tp_count" in df and not df["tp_count"].empty else 0,
        name + "mean_SL_count": df["sl_count"].mean() if "sl_count" in df and not df["sl_count"].empty else 0,
        name + "mean_BA_round_count": df["ba_round_count"].mean() if "ba_round_count" in df and not df["ba_round_count"].empty else 0,
        name + "mean_BA_count": df["ba_count"].mean() if "ba_count" in df and not df["ba_count"].empty else 0,
        # name + "Counter_list": df["counter_list"].iloc[0] if "counter_list" in df and not df["counter_list"].empty else [],
        #
        name + "sum_InitBuy": df["ib_count"].sum() if "ib_count" in df and not df["ib_count"].empty else 0,
        name + "sum_TP_count": df["tp_count"].sum() if "tp_count" in df and not df["tp_count"].empty else 0,
        name + "sum_SL_count": df["sl_count"].sum() if "sl_count" in df and not df["sl_count"].empty else 0,
        name + "sum_BA_round_count": df["ba_round_count"].sum() if "ba_round_count" in df and not df["ba_round_count"].empty else 0,
        name + "sum_BA_count": df["ba_count"].sum() if "ba_count" in df and not df["ba_count"].empty else 0,
        # name + "Counter_list": df["counter_list"].iloc[0] if "counter_list" in df and not df["counter_list"].empty else [],
        #


    }


def geometric_mean(returns):
    """
    Why: Compounding-style average return (less sensitive to huge pumps)
    Use: For typical multiplicative growth rate (CAGR-like behavior)
    """
    r = np.asarray(returns) / 100  # convert % to decimal if in percent
    r = np.clip(r, -0.9999, None)  # avoid log(negative or zero)
    return (np.exp(np.mean(np.log1p(r))) - 1) * 100


def trimmed_mean(values, trim_ratio=0.05):
    """
    Why: Removes top/bottom extremes that distort average
    Use: For 'typical' central performance, excluding few moonshots/crashes
    """
    vals = np.sort(np.asarray(values))
    n = len(vals)
    k = int(n * trim_ratio)
    trimmed = vals[k:n - k] if n > 2 * k else vals
    return np.mean(trimmed)


def analys(dfname, df=None, df_filename=None):
    # """Analyze trading results and return summary statistics as a DataFrame"""
    # try:
    # print("analys",dfname)
    if df is None:
        all_results_df = pd.read_csv(dfname)
        filename = os.path.basename(dfname)
    else:
        all_results_df = df
        filename = df_filename
    # Convert to numeric
    all_results_df["final_value_numeric"] = pd.to_numeric(all_results_df["final_value"], errors='coerce')
    all_results_df["start_value_numeric"] = pd.to_numeric(all_results_df["start_value"], errors='coerce')
    #
    all_results_df["value_pnl"] = all_results_df["final_value_numeric"] - all_results_df["start_value_numeric"]
    all_results_df["pnl%"] = (100 * all_results_df["value_pnl"]) / all_results_df["start_value_numeric"]
    #
    # print("analys(dfname) all_results_df columns:",all_results_df.columns)
    #  Index(['coin', 'start_value', 'final_value', 'sharpe_ratio', 'sortino_ratio',
    #    'calmar_ratio', 'vwr', 'sqn', 'max_drawdown', 'avg_drawdown',
    #    'total_trades', 'current_winning_streak', 'longest_winning_streak',
    #    'current_losing_streak', 'longest_losing_streak', 'gross_total_pnl',
    #    'gross_average_pnl', 'net_total_pnl', 'net_average_pnl',
    #    'winning_trades', 'winning_total_pnl', 'winning_avg_pnl',
    #    'winning_max_pnl', 'losing_trades', 'losing_total_pnl',
    #    'losing_avg_pnl', 'losing_max_pnl', 'time_total', 'time_average',
    #    'time_max', 'time_min', 'time_won_total', 'time_won_avg',
    #    'time_won_max', 'time_won_min', 'time_lost_total', 'time_lost_avg',
    #    'time_lost_max', 'time_lost_min', 'win_rate', 'avg_trade_pnl',
    #    'best_trade_pnl', 'worst_trade_pnl', 'profit_factor',
    #    'annualized_return', 'cumulative_return', 'trade_duration_mean',
    #    'trade_duration_median', 'trade_duration_min', 'trade_duration_max',
    #    'trade_duration_std', 'trade_duration_count', 'ib_count', 'tp_count',
    #    'sl_count', 'ba_round_count', 'ba_count', 'counter_list', 'ath',
    #    'time_len', 'time_to_ath', 'time_after_ath', 'final_value_numeric',
    #    'start_value_numeric', 'value_pnl', 'pnl%'],
    #   dtype='object')
    profitable_tokens_df = all_results_df[all_results_df["start_value_numeric"] < all_results_df["final_value_numeric"]]
    loss_tokens_df = all_results_df[all_results_df["start_value_numeric"] > all_results_df["final_value_numeric"]]
    no_change_df = all_results_df[all_results_df["start_value_numeric"] == all_results_df["final_value_numeric"]]
    # Tokens
    total_tokens = len(all_results_df)
    profitable_tokens = len(profitable_tokens_df)
    loss_tokens = len(loss_tokens_df)
    none_tokens = len(no_change_df)
    # Filter only changed ones
    # all_results_df = all_results_df[all_results_df["final_value_numeric"]!=100]

    # Calculate statistics
    total_start_value = all_results_df["start_value_numeric"].sum()
    total_final_value = all_results_df["final_value_numeric"].sum()

    # Count different outcomes
    # none_count = len(all_results_df[all_results_df["start_value"] == all_results_df["final_value"]])
    # sl_count = len(all_results_df[all_results_df["start_value"] > all_results_df["final_value"]])  # Stop Loss
    # tp_count = len(all_results_df[all_results_df["start_value"] < all_results_df["final_value"]])  # Take Profit
    # Get descriptive statistics
    # final_value_stats = all_results_df["final_value_numeric"].describe()

    # Create result dictionary
    token_result = {
        'filename': filename,
        'total_tokens': total_tokens,
        'profitable_tokens': profitable_tokens,
        'loss_tokens': loss_tokens,
        'none_tokens': none_tokens,

        '%profitable_tokens': ((profitable_tokens / total_tokens) * 100) if total_tokens > 0 else 0,
        '%loss_tokens': ((loss_tokens / total_tokens) * 100) if total_tokens > 0 else 0,
        '%none_tokens': ((none_tokens / total_tokens) * 100) if total_tokens > 0 else 0,

        # 'total_start_value': total_start_value,
        # 'total_final_value': total_final_value,
        # 'value_pnl': total_final_value - total_start_value,
        '%total_pnl': ((total_final_value - total_start_value) / total_start_value * 100) if total_start_value > 0 else 0,

        # 'mean_final_value': final_value_stats['mean'],
        # 'max_final_value': final_value_stats['max'],
        # 'min_final_value': final_value_stats['min'],
        # 'std_final_value': final_value_stats['std'],
        # 'median_final_value': final_value_stats['50%']


    }
    r2 = {
        "geo_mean_return": geometric_mean(all_results_df["pnl%"]),
        "trimmed_mean_5pct": trimmed_mean(all_results_df["pnl%"], 0.03),
        "median": np.median(all_results_df["pnl%"]),
        "p25": np.percentile(all_results_df["pnl%"], 25),
        "p75": np.percentile(all_results_df["pnl%"], 75),
        "win_rate": (all_results_df["pnl%"] > 100).mean(),
        "max": np.max(all_results_df["pnl%"]),
        "min": np.min(all_results_df["pnl%"]),
        "iqr": np.percentile(all_results_df["pnl%"], 75) - np.percentile(all_results_df["pnl%"], 25),
        "mad": np.median(np.abs(all_results_df["pnl%"] - np.median(all_results_df["pnl%"]))),
    }
    return token_result | r2 | analys_trades(all_results_df, "all:") | analys_trades(profitable_tokens_df, "profit_tokens:") | analys_trades(loss_tokens_df, "loss_tokens:")

    # except Exception as e:

    #     print("Error",e)
    #     return {
    #         'filename': os.path.basename(dfname),
    #         'error': str(e),
    #         'total_trades': 0,
    #         'profitable_trades': 0,
    #         'profitable_percentage': 0,
    #         'total_start_value': 0,
    #         'total_final_value': 0,
    #         'total_pnl': 0,
    #         'pnl_percentage': 0,
    #         'none_count': 0,
    #         'none_percentage': 0,
    #         'sl_count': 0,
    #         'sl_percentage': 0,
    #         'tp_count': 0,
    #         'tp_percentage': 0,
    #         'mean_final_value': 0,
    #         'max_final_value': 0,
    #         'min_final_value': 0,
    #         'std_final_value': 0,
    #         'median_final_value': 0
    #     }


# Main analysis loop - collect all results into a DataFrame
# results_list = []
# print("=" * 80)

# for f in os.listdir(results_folder):

#     if f.endswith('.csv') and not f.startswith("all_portfolio_histories"):
#         lenstr = f.split("_")[-2].split("-")[-1]
#         if int(lenstr) > 100:
#             result = analys(os.path.join(results_folder, f))
    # print(result)
    # e/100
    # results_list.append(result)

# Create comprehensive results DataFrame
# summary_df = pd.DataFrame(results_list)

# Display the results
# print("Analysis Summary:")
# print("=" * 80)
# print(summary_df.to_string(index=False))

# Optional: Save to CSV
# summary_df.to_csv('trading_analysis_summary.csv', index=False)

# # You can also access specific columns or filter the data
# print("\n" + "=" * 80)
# print("Top 5 Most Profitable (by PnL %):")
# top_profitable = summary_df.nlargest(5, 'pnl_percentage')[['filename', 'total_trades', 'profitable_percentage', 'pnl_percentage']]
# print(top_profitable.to_string(index=False))

# print("\n" + "=" * 80)
# print("Summary Statistics:")
# print(f"Total files analyzed: {len(summary_df)}")
# print(f"Average profitable percentage: {summary_df['profitable_percentage'].mean():.2f}%")
# print(f"Average PnL percentage: {summary_df['pnl_percentage'].mean():.2f}%")
# print(f"Files with errors: {len(summary_df[summary_df['total_trades'] == 0])}")
