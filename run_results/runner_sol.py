import json
import pickle
import os

from run_results.runner import calculate_starting_index_time, run_backtest_for_df
from run_results.runner_config import RunConfig
from sizers.FiboMartingaleSizer import FiboMartingaleSizer
from strategies import FiboMartingaleStrategy
from utils.utils import get_name
import backtrader as bt


def run_crypto_df(dataframe,
                  coin_name,
                  sizer_class=FiboMartingaleSizer,
                  strategy_class=FiboMartingaleStrategy,
                  sizer_params=None,
                  strategy_params=None,
                  commission_class=None,
                  config: RunConfig = RunConfig()
                  ):
    """
    Runs backtests for multiple dataframes and aggregates results.

    Args:
         strategy_class: The Backtrader strategy class to use.

    Returns:
        tuple: (pd.DataFrame of all results, dict of {'coin_name': cerebro_object}, dict of {'coin_name': portfolio_history_series})
    """

    print(f"\n{'*' * 20} Running backtest for {coin_name} ( Len: {len(dataframe)}) {'*' * 20}")
    df = dataframe

    tmp_start_marg = calculate_starting_index_time(df, after_ath=config.after_ath, randomize=config.randomize_start_margin, min_random_start_margin=config.min_start_margin, max_random_start_margin=config.max_start_margin, end_margin=config.df_end_margin, min_start_minutes_to_wait=config.min_start_minutes_to_wait)
    print("Start margin:", tmp_start_marg)
    analysis_result, cerebro_obj, portfolio_history_series = run_backtest_for_df(
        df[tmp_start_marg:config.df_end_margin],
        coin_name=coin_name,
        strategy_class=strategy_class,
        cash=config.cash,
        sizer_class=sizer_class,
        strategy_params=strategy_params,
        commission_class=commission_class,
        sizer_params=sizer_params,
        runonce=config.cerebro_runonce)

    analysis_result["time_token"] = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]) / 1000
    analysis_result["len_index_token"] = len(df)

    return analysis_result, cerebro_obj, portfolio_history_series


def run_and_save_crypto(dataframe, sizer_class, strategy_class, strategy_params, sizer_params, commission_class, config: RunConfig):
    name, detail = get_name(strategy_class, strategy_params, sizer_class, sizer_params, len(dataframe), config=config)
    results_folder = config.results_folder
    full_save_name = name + "_crypto.csv"
    full_detail_name = "details_" + name + "_crypto_details.txt"
    print(name, detail)
    if commission_class is None:
        class CommSOLAxiom(bt.CommissionInfo):
            # 0.005 means 0.5% of the operation value
            params = dict(commission=0.001)
        commission_class = CommSOLAxiom

    all_results_df, all_cerebros_objects, all_portfolio_histories = run_crypto_df(dataframe,
                                                                                  sizer_class=sizer_class,
                                                                                  strategy_class=strategy_class,
                                                                                  strategy_params=strategy_params,
                                                                                  sizer_params=sizer_params,
                                                                                  config=config,
                                                                                  commission_class=commission_class,
                                                                                  )

    df_save_path = results_folder + full_save_name

    # Save details
    with open(os.path.join(results_folder, full_detail_name), "w") as f:
        f.write(json.dumps(detail, indent=4))

    all_results_df.to_csv(df_save_path)
    portfolio_histories_save_path = results_folder + "_crypto_all_portfolio_histories" + name
    print("df saved to ", df_save_path)
    try:
        with open(portfolio_histories_save_path, 'wb') as f:  # 'wb' for write binary
            pickle.dump(all_portfolio_histories, f)
        print("\nDictionary successfully saved to ", portfolio_histories_save_path)
    except Exception as e:
        print(f"Error saving dictionary: {e}")
