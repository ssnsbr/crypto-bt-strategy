import pandas as pd
import numpy as np

# Define the start and end time for the data, covering 120 seconds.
start_time = pd.to_datetime('2025-06-10 21:16:00')
end_time = start_time + pd.Timedelta(seconds=119)

# Create a full range of 1-second timestamps.
date_range = pd.date_range(start=start_time, end=end_time, freq='S')

# Create a linear price path from 5000 to 100000 over 120 seconds.
price_path = np.linspace(5000, 100000, len(date_range)) + np.random.randn(len(date_range)) * 10

# Create the DataFrame with OHLCV data.
df = pd.DataFrame(index=date_range)
df['open'] = price_path
df['close'] = df['open'] + np.random.randn(len(df)) * 50
df['high'] = df[['open', 'close']].max(axis=1) + np.abs(np.random.randn(len(df)) * 10)
df['low'] = df[['open', 'close']].min(axis=1) - np.abs(np.random.randn(len(df)) * 10)
df['volume'] = np.random.randint(10, 500, len(df))

# Randomly drop a few rows to simulate missing data points.
rows_to_drop = np.random.choice(df.index, size=np.random.randint(5, 10), replace=False)
df = df.drop(rows_to_drop)

# Reset the index and rename the column for MT5 compatibility.
df.reset_index(inplace=True)
df.rename(columns={'index': 'datetime'}, inplace=True)

# Reorder the columns to match the MT5 import format.
df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]

# Save the DataFrame to a CSV file.
output_filename = 'test.csv'
df.to_csv(output_filename, index=False)

print(f"Test data successfully created and saved to '{output_filename}'")
