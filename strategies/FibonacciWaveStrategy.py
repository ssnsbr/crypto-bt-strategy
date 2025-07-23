import backtrader as bt
import pandas as pd
# from utils.data_utils import ready_df
import os


class FibonacciOverlay(bt.Indicator):
    lines = ('last_high_line', 'last_low_line',
             'fib_0_up', 'fib_236_up', 'fib_382_up', 'fib_50_up',
             'fib_618_up', 'fib_786_up', 'fib_100_up')

    plotinfo = dict(subplot=False)

    plotlines = dict(
        last_high_line=dict(color='orange', linewidth=2),
        last_low_line=dict(color='purple', linewidth=2),
        fib_0_up=dict(color='green', linestyle='-', linewidth=1),
        fib_236_up=dict(color='blue', linestyle='-', linewidth=1),
        fib_382_up=dict(color='red', linestyle='-', linewidth=1),
        fib_50_up=dict(color='cyan', linestyle='-', linewidth=1),
        fib_618_up=dict(color='magenta', linestyle='-', linewidth=1),
        fib_786_up=dict(color='red', linestyle='-', linewidth=1),
        fib_100_up=dict(color='black', linestyle='-', linewidth=1),
    )

    params = (('lookback', 200),)

    def __init__(self):
        high = self.data.high
        low = self.data.low
        lookback = self.p.lookback

        self.highest = bt.ind.Highest(high, period=lookback)
        self.lowest = bt.ind.Lowest(low, period=lookback)

    def next(self):
        hh = self.highest[0]
        ll = self.lowest[0]
        rng = hh - ll

        if rng == 0:
            for l in self.lines:
                getattr(self.lines, l)[0] = float('nan')
            return

        self.lines.last_high_line[0] = hh
        self.lines.last_low_line[0] = ll

        self.lines.fib_0_up[0] = hh
        self.lines.fib_236_up[0] = hh - rng * 0.236
        self.lines.fib_382_up[0] = hh - rng * 0.382
        self.lines.fib_50_up[0] = hh - rng * 0.5
        self.lines.fib_618_up[0] = hh - rng * 0.618
        self.lines.fib_786_up[0] = hh - rng * 0.786
        self.lines.fib_100_up[0] = ll


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


class FibonacciWaveStrategy(bt.Strategy):
    params = (
        ('lookback_period', 200),  # Period to find the last significant high/low
        ('fib_levels', [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]),
    )

    # Define lines for plotting Fibonacci levels and swing points
    # We will draw "Up Wave" retracements (pullbacks in an uptrend)
    # You could add "Down Wave" ones too if you need to visualize both
    lines = (
        'last_high_line',
        'last_low_line',
        'fib_0_up', 'fib_236_up', 'fib_382_up',
        'fib_50_up', 'fib_618_up', 'fib_786_up', 'fib_100_up',
        # 'fib_0_down', 'fib_236_down', 'fib_382_down', # Uncomment to plot down levels
        # 'fib_50_down', 'fib_618_down', 'fib_786_down', 'fib_100_down',
    )

    # Plot info for better visualization
    plotinfo = dict(
        subplot=False,  # Plot on the main price chart
        plotyhlines=False  # Do not plot horizontal lines for all values
    )

    # **REVISED PLOTLINES FOR CLARITY**
    plotlines = dict(
        last_high_line=dict(color='orange', linewidth=2, linestyle='-'),  # Solid, thicker orange
        last_low_line=dict(color='purple', linewidth=2, linestyle='-'),  # Solid, thicker purple
        fib_0_up=dict(color='green', linestyle='-', linewidth=1, plotlabel=True),  # Label for 0%
        fib_236_up=dict(color='blue', linestyle='-', linewidth=1, plotlabel=True),  # Label for 23.6%
        fib_382_up=dict(color='red', linestyle='-', linewidth=1, plotlabel=True),  # Label for 38.2%
        fib_50_up=dict(color='cyan', linestyle='-', linewidth=1, plotlabel=True),  # Label for 50%
        fib_618_up=dict(color='magenta', linestyle='-', linewidth=1, plotlabel=True),  # Label for 61.8%
        fib_786_up=dict(color='yellow', linestyle='-', linewidth=1, plotlabel=True),  # Label for 78.6%
        fib_100_up=dict(color='black', linestyle='-', linewidth=1, plotlabel=True),  # Label for 100%
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low

        # To find the "last high" and "last low" within a lookback period
        self.last_high_indicator = bt.indicators.Highest(self.datahigh, period=self.p.lookback_period)
        self.last_low_indicator = bt.indicators.Lowest(self.datalow, period=self.p.lookback_period)
        self.fib_overlay = FibonacciOverlay(self.data)

        # Map fib_levels to our defined lines for easy assignment
        self.fib_line_map_up = {
            0.0: self.l.fib_0_up,
            0.236: self.l.fib_236_up,
            0.382: self.l.fib_382_up,
            0.5: self.l.fib_50_up,
            0.618: self.l.fib_618_up,
            0.786: self.l.fib_786_up,
            1.0: self.l.fib_100_up,
        }
        # self.fib_line_map_down = { ... similar for down levels ... }

    def next(self):
        # Ensure we have enough data for the lookback period
        if len(self.data) < self.p.lookback_period:
            # Set lines to NaN if not enough data, so they don't plot prematurely
            self.l.last_high_line[0] = float('nan')
            self.l.last_low_line[0] = float('nan')
            for line in self.fib_line_map_up.values():
                line[0] = float('nan')
            # For down levels too
            return

        # Get the current highest high and lowest low from the indicators
        current_highest_high = self.last_high_indicator[0]
        current_lowest_low = self.last_low_indicator[0]

        # Assign these values to our plotting lines
        self.l.last_high_line[0] = current_highest_high
        self.l.last_low_line[0] = current_lowest_low

        price_range = current_highest_high - current_lowest_low

        if price_range > 0:
            # Calculate and assign Fibonacci Retracement Levels for plotting
            for level_ratio in self.p.fib_levels:
                # Retracement levels for an UPWARD move (pullback from the high)
                fib_value_up = current_highest_high - (price_range * level_ratio)
                if level_ratio in self.fib_line_map_up:
                    self.fib_line_map_up[level_ratio][0] = fib_value_up

                # Retracement levels for a DOWNWARD move (bounce from the low)
                # fib_value_down = current_lowest_low + (price_range * level_ratio)
                # If you enabled down levels, assign them here:
                # if level_ratio in self.fib_line_map_down:
                #     self.fib_line_map_down[level_ratio][0] = fib_value_down
        else:
            # If no valid range, set Fib lines to NaN to not draw them
            for line in self.fib_line_map_up.values():
                line[0] = float('nan')
            # For down levels too

        # --- Your existing trading logic based on Fibonacci levels would go here ---
        # Example: Trading logic based on Fibonacci levels
        # You would typically check if the close price hits a specific level
        # For instance, looking for support at 0.618 or 0.50 in an uptrend
        # Or resistance at 0.618 or 0.50 in a downtrend

        # If we are in an "uptrend wave" (current close is closer to high than low)
        if self.dataclose[0] > (current_lowest_low + current_highest_high) / 2:
            # Check for support levels
            fib_618_up = self.fib_line_map_up[0.618][0]  # Get value directly from the line
            if not isinstance(fib_618_up, float) or not fib_618_up == fib_618_up:  # Check for NaN
                # If fib_618_up is a valid number
                if self.dataclose[0] <= fib_618_up and not self.position:
                    self.log(f'BUY CREATE {self.dataclose[0]:.2f} - Approaching Fib 61.8% Support (Up Wave)')
                    self.buy()
        # If we are in a "downtrend wave"
        else:
            # Check for resistance levels (example for down levels - uncomment if used)
            # fib_618_down = self.fib_line_map_down[0.618][0]
            # if not isinstance(fib_618_down, float) or not fib_618_down == fib_618_down: # Check for NaN
            #     if self.dataclose[0] >= fib_618_down and not self.position:
            #         self.log(f'SELL CREATE {self.dataclose[0]:.2f} - Approaching Fib 61.8% Resistance (Down Wave)')
            #         self.sell()
            pass  # No down levels trade logic in this example

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')


# Example usage (setting up cerebro and running the backtest)
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(FibonacciWaveStrategy)

    # Add a data feed
    # Make sure this path points to your actual data file

    folder_path = 'I:\\axiomchart\\'
    file_csv = "15s_axiom_chart_bars_Ekv9HdumWqnXZgq5G6ge6bk1ZRHKXYC2WnSFL94sQmLJ_1752166201266.csv"

    # List all CSV files
    csv_files = [folder_path + f for f in os.listdir(folder_path) if f.endswith('.csv')]
    print(f"Found {len(csv_files)} CSV files.", [len(pd.read_csv(csv_files[df_index])) for df_index in range(len(csv_files))])
    df_index = 2

    df = pd.read_csv(csv_files[df_index])
    df = ready_df(df, mcap=True)
    # data = bt.feeds.YahooFinanceCSVData(
    #     dataname='../../datas/2005-2006-day-001.txt',
    #     fromdate=datetime.datetime(2005, 1, 1),
    #     todate=datetime.datetime(2006, 12, 31),
    #     reverse=False
    # )

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

    cerebro.broker.setcash(100000.0)
    cerebro.addsizer(bt.sizers.FixedSize, stake=10)  # Fixed size for simplicity
    cerebro.broker.setcommission(commission=0.001)

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Plot the results
    cerebro.plot(
        # You can add more plotting options here
        style='candlestick',  # Or 'bar', 'line'
        subplot=False,  # <--- moves indicators to their own subplot

        # Control the figure size (matplotlib default might be small)
        numfigs=1,  # Ensures all data is on one figure if you add more data feeds
        figsize=(12, 8),  # Adjust width and height for better visibility
    )
