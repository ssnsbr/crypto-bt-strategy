import pandas as pd
import numpy as np
import os

import backtrader as bt
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


def run_backtest_for_df(df, coin_name,
                        sizer_class=FiboMartingaleSizer,
                        strategy_class=FiboMartingaleStrategy,
                        cash=1000,
                        commission=0.001,
                        strategy_params=None,
                        sizer_params=None,
                        mcap=False
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
    if strategy_params is None:
        strategy_params = {}

    cerebro = bt.Cerebro()

    # Pass the strategy_params dictionary using **kwargs
    cerebro.addstrategy(strategy_class, **strategy_params)
    print("strategy_class.params:", strategy_params)

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
    # cerebro.addsizer(DynamicTrendHybridSizer,stake=0.1)
    # cerebro.addsizer(bt.sizers.FixedSize, stake=10) # Example of adding a sizer
    print("sizer_params.params:", sizer_params)
    cerebro.addsizer(sizer_class, **sizer_params)

    if mcap:
        cerebro.broker.setcash(cash * 1_000_000_000)
    else:
        cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission)

    # Add analyzers
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
    if mcap:
        print(f'Starting backtest for {coin_name} - Initial Portfolio Value: {cerebro.broker.getvalue()/1_000_000_000:.2f}')
    else:
        print(f'Starting backtest for {coin_name} - Initial Portfolio Value: {cerebro.broker.getvalue():.2f}')

    results = cerebro.run()
    strategy = results[0]

    final_portfolio_value = cerebro.broker.getvalue()

    if mcap:
        final_portfolio_value = final_portfolio_value / 1_000_000_000
    print(f'Final Portfolio Value for {coin_name}: {final_portfolio_value:.2f}')

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
        print(k, v)
    # Extract portfolio history for plotting
    # The PositionsValue analyzer can give us the portfolio value over time.
    # We need to iterate through the cerebro's data to get the dates
    # And the analyzer to get the corresponding values.
    # Note: bt.observers.Value also provides portfolio history, but it's simpler to
    # extract from an analyzer if you're already using them.

    # Extract portfolio history
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
    # print(portfolio_history_series.tolist())

    # Extract CASH history
    cash_history = {}
    for dt, value in strategy.analyzers.mycashvalue.get_analysis().items():
        cash_history[dt] = value  # dt is already a datetime object
    cash_history_series = pd.Series(cash_history).sort_index()

    if mcap:
        cash_history_series = cash_history_series / 1_000_000_000

    print("Cash History:", cash_history_series.tolist())

    combined_array = np.column_stack((cash_history_series.values, portfolio_history_series.values))
    result_list_of_lists = combined_array.tolist()
    print("Full History:", result_list_of_lists)

    return analysis_results, cerebro, cash_history_series


def run_all(csv_files,
            sizer_class=FiboMartingaleSizer,
            strategy_class=FiboMartingaleStrategy,
            cash=1000,
            commission=0.001,
            sizer_params=None,
            strategy_params=None,
            mcap=False,
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

        try:
            analysis_result, cerebro_obj, portfolio_history_series = run_backtest_for_df(
                df,
                coin_name=coin_name,
                strategy_class=strategy_class,
                cash=cash,
                commission=commission,
                sizer_class=sizer_class,
                strategy_params=strategy_params,
                mcap=mcap,
                sizer_params=sizer_params)
            all_results.append(analysis_result)
            all_cerebros[coin_name] = cerebro_obj
            all_portfolio_histories[coin_name] = portfolio_history_series
        except Exception as e:
            print(f"Error running backtest for {coin_name}: {e}")
            # Optionally add a placeholder result for failed backtests
            all_results.append({'coin': coin_name, 'final_value': 'Error', 'sharpe_ratio': 'Error',
                                'max_drawdown': 'Error', 'total_trades': 'Error',
                                'winning_trades': 'Error', 'losing_trades': 'Error',
                                'annualized_return': 'Error'})

    results_df = pd.DataFrame(all_results)
    return results_df, all_cerebros, all_portfolio_histories
