import pandas as pd
import numpy as np
import os

import backtrader as bt
from commissions.CustomSolanaCommission import CustomSolanaCommission
from sizers.FiboMartingaleSizer import FiboMartingaleSizer
from strategies import FiboMartingaleStrategy
from utils.data_utils import ready_df


class CashHistoryAnalyzer(bt.Analyzer):
    """
    An analyzer to record the cash balance at each bar.
    """

    def __init__(self):
        self.cash_history = {}

    def next(self):
        # Record cash at the end of each bar
        # self.data.datetime[0] gives the date of the current bar (as a float)
        # self.strategy.broker.getcash() gives the current cash balance
        dt = self.strategy.data.datetime.datetime(0)  # Get the current bar's datetime object
        self.cash_history[dt] = self.strategy.broker.getcash()

    def get_analysis(self):
        # Return the dictionary of cash history
        return self.cash_history


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
                        print_cash_history=False
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

    cerebro = bt.Cerebro()

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

    results = cerebro.run()
    strategy = results[0]
    print("[RUN] Cerebro Ended.")

    final_portfolio_value = cerebro.broker.getvalue()
    if mcap:
        final_portfolio_value = final_portfolio_value / 1_000_000_000
    print(f'[RUN] Final Portfolio Value for {coin_name}: {final_portfolio_value:.2f}')

    # Extract analysis results
    analysis_results = {
        'coin': coin_name,
        'start_value': cash,
        'final_value': final_portfolio_value,
        'sharpe_ratio': strategy.analyzers.mysharpe.get_analysis().get('sharperatio', 'N/A'),
        'max_drawdown': strategy.analyzers.mydrawdown.get_analysis().get('max', {}).get('drawdown', 'N/A'),
        'total_trades': strategy.analyzers.mytradeanalyzer.get_analysis().get('total', {}).get('closed', 0),
        'winning_trades': strategy.analyzers.mytradeanalyzer.get_analysis().get('won', {}).get('total', 0),
        'losing_trades': strategy.analyzers.mytradeanalyzer.get_analysis().get('lost', {}).get('total', 0),
        'annualized_return': strategy.analyzers.myreturns.get_analysis().get('rnorm100', 'N/A')
    }
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


def run_all(csv_files,
            sizer_class=FiboMartingaleSizer,
            strategy_class=FiboMartingaleStrategy,
            cash=1,
            sizer_params=None,
            strategy_params=None,
            mcap=False,
            df_start_margin=0,
            df_end_margin=-1
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
        df = ready_df(df, mcap=mcap)
        coin_name = os.path.basename(csv_file).split('.')[0][17:27]  # Assuming coin name is the filename without extension

        analysis_result, cerebro_obj, portfolio_history_series = run_backtest_for_df(
                df[df_start_margin:df_end_margin],
                coin_name=coin_name,
                strategy_class=strategy_class,
                cash=cash,
                sizer_class=sizer_class,
                strategy_params=strategy_params,
                mcap=mcap,
                commission_class=CustomSolanaCommission,
                sizer_params=sizer_params)
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
