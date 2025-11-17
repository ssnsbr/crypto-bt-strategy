import json
import pickle
import os

import numpy as np
import pandas as pd

from run_results.analys_results import read_analysers
from run_results.custom_analyzers import BACounterAnalyzer, CashHistoryAnalyzer, SafeVWR, TradeDurationAnalyzer
from run_results.runner_config import RunConfig
from sizers.FiboMartingaleSizer import FiboMartingaleSizer
from strategies import FiboMartingaleStrategy
from utils.utils import get_name
import backtrader as bt


def _configure_cerebro(
    cerebro: bt.Cerebro,
    df: pd.DataFrame,
    strategy_class: type,
    strategy_params: dict,
    sizer_class: type,
    sizer_params: dict,
    commission_class: type,
    initial_cash: float,
    is_mcap: bool,
    multi_tf: list
):
    """
    Helper function to configure a Backtrader Cerebro object.
    """
    print(f"[RUN] Strategy: {strategy_class.__name__}, Params: {strategy_params}")
    cerebro.addstrategy(strategy_class, **strategy_params)

    def add_compression(df, c):
        data_Xm = bt.feeds.PandasData(
            dataname=df,
            datetime='datetime',
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            timeframe=bt.TimeFrame.Minutes,
            compression=c
        )

        cerebro.adddata(data_Xm)
    for mtf in multi_tf:
        if mtf == "1m":
            add_compression(df, 1)
        elif mtf == "3m":
            add_compression(df, 3)
        elif mtf == "5m":
            add_compression(df, 5)
        elif mtf == "15m":
            add_compression(df, 15)
        elif mtf == "30m":
            add_compression(df, 30)
        elif mtf == "1h":
            add_compression(df, 60)
        elif mtf == "4h":
            add_compression(df, 240)

        # cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=15)
        # cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=60)

    # REGISTER YOUR SIZER
    print(f"[RUN] Sizer: {sizer_class.__name__}, Params: {sizer_params}")
    cerebro.addsizer(sizer_class, **sizer_params)

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
    cerebro.addanalyzer(SafeVWR, _name='myvwr')
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
                        runonce=True,
                        multi_tf=["1m"]
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
        is_mcap=mcap,
        multi_tf=multi_tf
    )

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
        portfolio_history[dt] = value_list

        # portfolio_history[dt] = value # dt is already a datetime object
    portfolio_history_series = pd.Series(portfolio_history).sort_index()

    # Extract CASH history , dt is already a datetime object
    cash_history = {dt: value for dt, value in strategy.analyzers.mycashvalue.get_analysis().items()}
    cash_history_series = pd.Series(cash_history).sort_index()

    if print_cash_history:
        print("[RUN] Cash History:", cash_history_series.tolist())
        combined_array = np.column_stack((cash_history_series.values, portfolio_history_series.values))
        result_list_of_lists = combined_array.tolist()
        print("[RUN] Full History:", result_list_of_lists)

    return analysis_results, cerebro, cash_history_series


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

    tmp_start_marg = 0
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
        runonce=config.cerebro_runonce,
        multi_tf=config.multi_tf)

    analysis_result["time_token"] = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]) / 1000
    analysis_result["len_index_token"] = len(df)

    return analysis_result, cerebro_obj, portfolio_history_series


def run_and_save_crypto(dataframe, coin_name, sizer_class, strategy_class, strategy_params, sizer_params, config: RunConfig, commission_class=None):
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
                                                                                  coin_name,
                                                                                  sizer_class=sizer_class,
                                                                                  strategy_class=strategy_class,
                                                                                  strategy_params=strategy_params,
                                                                                  sizer_params=sizer_params,
                                                                                  config=config,
                                                                                  commission_class=commission_class,
                                                                                  )

    df_save_path = results_folder + full_save_name
    print(all_results_df)
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
