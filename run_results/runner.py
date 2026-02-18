import json
import pickle
from random import randint
import pandas as pd
import numpy as np
import os

import backtrader as bt
from backtrader_extended.commissions.CustomSolanaCommission import CustomSolanaCommission
from backtrader_extended.strategies.FiboMartingaleStrategy import FiboMartingaleStrategy
from run_results.analys_results import read_analysers
from run_results.custom_analyzers import BACounterAnalyzer, CashHistoryAnalyzer, TradeDurationAnalyzer
from run_results.runner_config import RunConfig
from backtrader_extended.sizers.FiboMartingaleSizer import FiboMartingaleSizer
from utils.data_utils import ready_df
from utils.utils import get_name


def _configure_cerebro(
    cerebro: bt.Cerebro,
    df: pd.DataFrame,
    strategy_class: type,
    strategy_params: dict,
    sizer_class: type,
    sizer_params: dict,
    commission_class: type,
    initial_cash: float,
    is_mcap: bool
):
    """
    Helper function to configure a Backtrader Cerebro object.
    """
    print(f"[RUN] Strategy: {strategy_class.__name__}, Params: {strategy_params}")
    cerebro.addstrategy(strategy_class, **strategy_params)

    data = bt.feeds.PandasData(
        dataname=df,
        datetime='datetime',
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        timeframe=bt.TimeFrame.Seconds,
        compression=1
    )
    cerebro.adddata(data)

    # REGISTER YOUR SIZER
    print(f"[RUN] Sizer: {sizer_class.__name__}, Params: {sizer_params}")
    cerebro.addsizer(sizer_class, **sizer_params)

    if is_mcap:
        cerebro.broker.setcash(initial_cash * 1_000_000_000)
        print(f"[RUN] In MCAP mode. Cash: {initial_cash}B, In-App Cash: {initial_cash * 1_000_000_000:.2f}")
    else:
        cerebro.broker.setcash(initial_cash)
        print(f"[RUN] Not in MCAP mode. Cash: {initial_cash:.2f}")

    print(f"[RUN] Commission: {commission_class.__name__}")
    cerebro.broker.addcommissioninfo(commission_class())

    # Add analyzers
    print("[RUN] Adding Analyzers and Observers.")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='mysharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='mydrawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='mytradeanalyzer')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='myreturns')
    cerebro.addanalyzer(bt.analyzers.PositionsValue, _name='mypositionsvalue')  # To get portfolio history
    cerebro.addanalyzer(CashHistoryAnalyzer, _name='mycashvalue')         # To get CASH history
    cerebro.addanalyzer(bt.analyzers.SQN, _name='mysqn')
    cerebro.addanalyzer(bt.analyzers.Transactions, _name='mytransactions')
    cerebro.addanalyzer(bt.analyzers.VWR, _name='myvwr')
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='mypyfolio')
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturns')
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annualreturn')
    cerebro.addanalyzer(bt.analyzers.PeriodStats, _name='periodstats')
    # cerebro.addanalyzer(bt.analyzers.Exposure, _name='exposure')
    cerebro.addanalyzer(bt.analyzers.GrossLeverage, _name='leverage')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio_A, _name='sharpe_annual')
    # cerebro.addanalyzer(bt.analyzers.SortinoRatio, _name='sortino')
    cerebro.addanalyzer(bt.analyzers.Calmar, _name='calmar')
    cerebro.addanalyzer(TradeDurationAnalyzer, _name='mytradeduration')
    cerebro.addanalyzer(BACounterAnalyzer, _name='mybacounteranalyzer')

    # Add observers (for plotting later)
    cerebro.addobserver(bt.observers.Broker)
    cerebro.addobserver(bt.observers.BuySell)
    cerebro.addobserver(bt.observers.Trades)


def run_backtest_for_df(df, coin_name,
                        sizer_class=None,
                        strategy_class=None,
                        commission_class=None,
                        cash=1000,
                        strategy_params=None,
                        sizer_params=None,
                        mcap=False,
                        print_cash_history=False,
                        runonce=True
                        ):
    """
    Runs a backtest for a single DataFrame and returns results and the cerebro object.
    Does NOT plot the result immediately.

    Args:
        df (pd.DataFrame): The dataframe containing OHLCV data.
        coin_name (str): The name of the coin for identification in results.
        strategy_class: The Backtrader strategy class to use.

    Returns:
        tuple: (dict of analysis results, bt.Cerebro object)
    """
    strategy_params = strategy_params or {}
    sizer_params = sizer_params or {}

    cerebro = bt.Cerebro(runonce=runonce)

    _configure_cerebro(
        cerebro=cerebro,
        df=df,
        strategy_class=strategy_class,
        strategy_params=strategy_params,
        sizer_class=sizer_class,
        sizer_params=sizer_params,
        commission_class=commission_class,
        initial_cash=cash,
        is_mcap=mcap
    )

    if mcap:
        print(f'[RUN] Starting backtest for {coin_name} - Initial Portfolio Value: {cerebro.broker.getvalue()/1_000_000_000:.2f}')
    else:
        print(f'[RUN] Starting backtest for {coin_name} - Initial Portfolio Value: {cerebro.broker.getvalue():.2f}')
    if len(df) < 100:
        print(f'[RUN] Not enough data for {coin_name}. Skipping backtest.')
        analysis_results = {
            'coin': coin_name,
            'start_value': cash,
            'final_value': cash,
        }
        return analysis_results, cerebro, []
    results = cerebro.run()
    strategy = results[0]
    print("[RUN] Cerebro Ended.")

    final_portfolio_value = cerebro.broker.getvalue()
    if mcap:
        final_portfolio_value = final_portfolio_value / 1_000_000_000
    print(f'[RUN] Final Portfolio Value for {coin_name}: {final_portfolio_value:.2f}')
    # Extract analysis results safely (with default fallbacks)
    # Extract analysis results
    analysis_results = {
        'coin': coin_name,
        'start_value': cash,
        'final_value': final_portfolio_value,
    }
    a_r = read_analysers(strategy)
    analysis_results = analysis_results | a_r

    print('Analyze:')
    for k, v in analysis_results.items():
        print("[RUN] ", k, v)

    # Extract portfolio history for plotting
    portfolio_history = {}
    for dt, value_list in strategy.analyzers.mypositionsvalue.get_analysis().items():
        np_value_array = np.array(value_list)

        if mcap:
            # Perform the division on the entire NumPy array at once
            processed_value_array = np_value_array / 1_000_000_000
            portfolio_history[dt] = processed_value_array.tolist()  # Store as list again if needed, or keep array
        else:
            portfolio_history[dt] = value_list

        # portfolio_history[dt] = value # dt is already a datetime object
    portfolio_history_series = pd.Series(portfolio_history).sort_index()

    # Extract CASH history , dt is already a datetime object
    cash_history = {dt: value for dt, value in strategy.analyzers.mycashvalue.get_analysis().items()}
    cash_history_series = pd.Series(cash_history).sort_index()

    if mcap:
        cash_history_series = cash_history_series / 1_000_000_000

    if print_cash_history:
        print("[RUN] Cash History:", cash_history_series.tolist())
        combined_array = np.column_stack((cash_history_series.values, portfolio_history_series.values))
        result_list_of_lists = combined_array.tolist()
        print("[RUN] Full History:", result_list_of_lists)

    return analysis_results, cerebro, cash_history_series


def calculate_starting_index_time(df, after_ath=False, randomize=True, min_random_start_margin=30, max_random_start_margin=100, end_margin=-1, min_start_minutes_to_wait=0):
    starting_index = 0
    df_to_run = df

    if after_ath:
        ath_index = df["close"].idxmax()
        ath = df["close"].max()
        print("ATH is ", ath, " at index ", ath_index, " of ", len(df))
        df_to_run = df.loc[ath_index + 1:]
        print("calculate_starting_index_time After ATH len:", len(df_to_run))
        starting_index = max(starting_index, ath_index)

    if min_start_minutes_to_wait != 0:
        df["date_time"] = pd.to_datetime(df["timestamp"], unit='ms')
        get_first = df["date_time"].iloc[0]
        cutoff = get_first + pd.Timedelta(minutes=min_start_minutes_to_wait)
        # Filter rows after that cutoff
        later_rows = df[df["date_time"] >= cutoff]
        min_len = 50
        if not later_rows.empty:
            starting_index = max(starting_index, later_rows.index[0])
            df_to_run = df[starting_index:]
            print("calculate_starting_index_time After time_to_wait len:", len(df_to_run), " starting index:", starting_index, " Time of first row: ", df["date_time"].iloc[0], " Cutoff to Time: ", df_to_run["date_time"].iloc[0])
        else:
            print(f"calculate_starting_index_time No rows found {min_start_minutes_to_wait}h after start; using default index len(df)- ", min_len, len(df) - min_len, " Time of first row: ", df["date_time"].iloc[0], " Time of last row: ", df["date_time"].iloc[-1])

            df_to_run = df[-min_len:]
            starting_index = max(starting_index, len(df) - min_len)
    else:
        pass
    if randomize:
        random_start_margin = randint(1, min(max_random_start_margin, len(df_to_run) - end_margin - 1))
        random_start_margin = max(min_random_start_margin, random_start_margin)
        print("calculate_starting_index_time Randomized start margin:", random_start_margin, " => ", starting_index + random_start_margin)
        return starting_index + random_start_margin
    return starting_index


def run_all(csv_files,
            sizer_class=FiboMartingaleSizer,
            strategy_class=FiboMartingaleStrategy,
            sizer_params=None,
            strategy_params=None,
            config: RunConfig = RunConfig()
            ):
    """
    Runs backtests for multiple coin dataframes and aggregates results.

    Args:
        csv_files (list): A list of paths to your CSV files.
        strategy_class: The Backtrader strategy class to use.

    Returns:
        tuple: (pd.DataFrame of all results, dict of {'coin_name': cerebro_object}, dict of {'coin_name': portfolio_history_series})
    """
    all_results = []
    all_cerebros = {}
    all_portfolio_histories = {}

    for i, csv_file in enumerate(csv_files):
        print(f"\n{'*' * 20} Running backtest for {os.path.basename(csv_file)} ({i+1}/{len(csv_files)}) {'*' * 20}")
        df = pd.read_csv(csv_file)
        df = ready_df(df, mcap=config.mcap)
        coin_name = os.path.basename(csv_file).split('.')[0][17:27]  # Assuming coin name is the filename without extension
        ath_index = df["close"].idxmax()
        ath = df["close"].max()

        tmp_start_marg = calculate_starting_index_time(df, after_ath=config.after_ath, randomize=config.randomize_start_margin, min_random_start_margin=config.min_start_margin, max_random_start_margin=config.max_start_margin, end_margin=config.df_end_margin, min_start_minutes_to_wait=config.min_start_minutes_to_wait)
        print("Start margin:", tmp_start_marg)
        analysis_result, cerebro_obj, portfolio_history_series = run_backtest_for_df(
            df[tmp_start_marg:config.df_end_margin],
            coin_name=coin_name,
            strategy_class=strategy_class,
            cash=config.cash,
            sizer_class=sizer_class,
            strategy_params=strategy_params,
            mcap=config.mcap,
            commission_class=CustomSolanaCommission,
            sizer_params=sizer_params,
            runonce=config.cerebro_runonce)

        analysis_result["ath"] = ath
        analysis_result["time_token"] = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]) / 1000
        analysis_result["time_to_ath"] = (df["timestamp"].iloc[ath_index + 1] - df["timestamp"].iloc[0]) / 1000
        analysis_result["time_after_ath"] = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[ath_index + 1]) / 1000
        analysis_result["len_index_token"] = len(df)
        analysis_result["index_ath"] = ath_index

        all_results.append(analysis_result)
        all_cerebros[coin_name] = cerebro_obj
        all_portfolio_histories[coin_name] = portfolio_history_series

        # try:
        #     analysis_result, cerebro_obj, portfolio_history_series = run_backtest_for_df(
        #         df[df_start_margin:df_end_margin],
        #         coin_name=coin_name,
        #         strategy_class=strategy_class,
        #         cash=cash,
        #         sizer_class=sizer_class,
        #         strategy_params=strategy_params,
        #         mcap=mcap,
        #         commission_class=CustomSolanaCommission,
        #         sizer_params=sizer_params)
        #     all_results.append(analysis_result)
        #     all_cerebros[coin_name] = cerebro_obj
        #     all_portfolio_histories[coin_name] = portfolio_history_series
        # except Exception as e:
        #     print(f"Error running backtest for {coin_name}: {e}")
        #     # Optionally add a placeholder result for failed backtests
        #     all_results.append({'coin': coin_name, 'final_value': 'Error', 'sharpe_ratio': 'Error',
        #                         'max_drawdown': 'Error', 'total_trades': 'Error',
        #                         'winning_trades': 'Error', 'losing_trades': 'Error',
        #                         'annualized_return': 'Error'})

    results_df = pd.DataFrame(all_results)
    return results_df, all_cerebros, all_portfolio_histories


def run_and_save(file_to_run, sizer_class, strategy_class, strategy_params, sizer_params, config: RunConfig):
    name, detail = get_name(strategy_class, strategy_params, sizer_class, sizer_params, len(file_to_run), config=config)
    results_folder = config.results_folder
    full_save_name = name + "_memes.csv"
    full_detail_name = "details_" + name + "_details.txt"
    print(name, detail)
    all_results_df, all_cerebros_objects, all_portfolio_histories = run_all(file_to_run,
                                                                            sizer_class=sizer_class,
                                                                            strategy_class=strategy_class,
                                                                            strategy_params=strategy_params,
                                                                            sizer_params=sizer_params,
                                                                            config=config,
                                                                            )

    df_save_path = results_folder + full_save_name

    # Save details
    with open(os.path.join(results_folder, full_detail_name), "w") as f:
        f.write(json.dumps(detail, indent=4))

    all_results_df.to_csv(df_save_path)
    portfolio_histories_save_path = results_folder + "all_portfolio_histories" + name
    print("df saved to ", df_save_path)
    try:
        with open(portfolio_histories_save_path, 'wb') as f:  # 'wb' for write binary
            pickle.dump(all_portfolio_histories, f)
        print("\nDictionary successfully saved to ", portfolio_histories_save_path)
    except Exception as e:
        print(f"Error saving dictionary: {e}")
