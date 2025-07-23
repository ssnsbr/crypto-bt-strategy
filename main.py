import os
import pandas as pd

from sizers.ScalperMartingaleSizer import ScalperMartingaleSizer
from strategies.Fibo78 import FiboR
from strategies.MAMACDStrategy import MAMACDStrategy
from strategies.FastScalperStrategy import FastScalperStrategy
from strategies.FiboCheck import FiboChecker
from strategies.SimpleTest import SimpleTest
from utils.data_utils import ready_df
from utils.plotting_utils import plot_all_portfolio_histories, plot_all_portfolio_histories_by_time, plot_single_backtest
from utils.runner import run_all  # Import pandas for data preparation

import backtrader as bt
# !pip install backtrader
# %matplotlib inline


# Connect to Google Drive
# drive.mount('/content/drive')
if __name__ == "__main__":
    # Define path to your CSV files

    folder_path = 'I:\\axiomchart\\'
    file_csv = "15s_axiom_chart_bars_Ekv9HdumWqnXZgq5G6ge6bk1ZRHKXYC2WnSFL94sQmLJ_1752166201266.csv"

    # List all CSV files
    csv_files = [folder_path + f for f in os.listdir(folder_path) if f.endswith('.csv')]
    print(f"Found {len(csv_files)} CSV files.", [len(pd.read_csv(csv_files[df_index])) for df_index in range(len(csv_files))])
    df_index = 6

    file_csv = csv_files[df_index]
    print(csv_files[df_index])
    print(ready_df(pd.read_csv(csv_files[df_index]), True).head(2))

    df = pd.read_csv(csv_files[df_index])
    print(len(df))

    df = ready_df(df)
    print(df.head())

    df.head()

    # sizer_params = {"initial_buy_amount_factor":strategy_class.params.initial_buy_amount_factor,  # buggy, it reads default values of strategy_class
    #                  "martingale_multiplier":strategy_class.params.martingale_multiplier,  # buggy, it reads default values of strategy_class
    #                  "data_in_market_cap": mcap,
    #                  "log":sizer_log}
    mcap = True
    log = True
    sizer_log = True
    # strategy_class = FastScalperStrategy
    # strategy_class = FiboChecker
    # strategy_class = MAMACDStrategy
    strategy_class = FiboR
    strategy_params = {'data_in_market_cap': mcap, "log": log}
    # sizer_class = bt.sizers.FixedSize()
    sizer_class = ScalperMartingaleSizer
    sizer_params = {
        "initial_buy_amount_factor": strategy_params.get('initial_buy_amount_factor', 0.05),
        "martingale_multiplier": strategy_params.get('martingale_multiplier', 2.0),
        "data_in_market_cap": mcap,
        "log": sizer_log
    }
    sizer_class = bt.sizers.PercentSizer
    sizer_params = None
    all_results_df, all_cerebros_objects, all_portfolio_histories = run_all([file_csv],
                                                                            sizer_class=sizer_class,
                                                                            strategy_class=strategy_class,
                                                                            strategy_params=strategy_params,
                                                                            sizer_params=sizer_params,
                                                                            cash=1000,
                                                                            mcap=mcap,
                                                                            )
    print("All Runs Complete!")
    # if __name__ == '__main__':
    # Step 1: Run all backtests
    # all_results_df, all_cerebros_objects, all_portfolio_histories = run_all(csv_files[:2], FiboMartingaleStrategy, 10, 0.1, mcap=True)

    # Step 2: Display the aggregated results DataFrame
    g = all_results_df[all_results_df["start_value"] < all_results_df["final_value"]]
    print(f"{len(g)} of {len(all_results_df)} were profitable!")
    # print(g)

    print("\n--- Aggregated Backtest Results ---")

    all_results_df

    import matplotlib.pyplot as plt
    plt.rcParams['figure.figsize'] = [18, 20]  # Adjust as desired
    plt.rcParams['figure.dpi'] = 100
    # The %matplotlib inline is for Jupyter/Colab environment and should be run directly in a cell,
    # For a script, you manage matplotlib output differently (e.g., plt.savefig)
    # %matplotlib inline

    # Step 3: Plot all portfolio histories on one chart
    plot_all_portfolio_histories_by_time(all_portfolio_histories, title="Portfolio Value Over Time for All Coins")
    # plot_all_portfolio_histories(all_portfolio_histories, title="Portfolio Value Over Time for All Coins")

    # Step 4: Select an interesting backtest and plot it
    # You can choose based on 'sharpe_ratio', 'final_value', etc.
    # For example, let's plot the coin with the highest final value
    best_coin_row = all_results_df.loc[all_results_df['final_value'].idxmax()]
    best_coin_name = best_coin_row['coin']

    print(f"\n--- Plotting best performing coin: {best_coin_name} ---")
    if best_coin_name in all_cerebros_objects:
        plot_single_backtest(all_cerebros_objects[best_coin_name], title=f"Backtest for {best_coin_name}")
    else:
        print(f"Cerebro object for {best_coin_name} not found.")

    # You can also manually select a coin to plot, e.g.:
    # plot_single_backtest(all_cerebros_objects['coin_0'], title="Backtest for coin_0")
