class SwingDetector(bt.Indicator):
    lines = ('swing_high', 'swing_low',)
    params = (
        ('bars_left', 5),  # Number of bars to the left that must be lower/higher
        ('bars_right', 5),  # Number of bars to the right that must be lower/higher
    )

    def __init__(self):
        # Initialize lines with nan to indicate no swing point yet
        self.lines.swing_high.set_value_with_nan()
        self.lines.swing_low.set_value_with_nan()

    def next(self):
        # Need enough data for the lookback period
        if len(self.data) < self.p.bars_left + self.p.bars_right + 1:
            return

        # Check for Swing High
        # Current bar's high
        current_high = self.data.high[0]

        # Check if current high is the highest in the defined window
        is_swing_high = True
        for i in range(1, self.p.bars_left + 1):
            if self.data.high[-i] >= current_high:
                is_swing_high = False
                break
        if is_swing_high:
            for i in range(1, self.p.bars_right + 1):
                if self.data.high[i] >= current_high:  # Accessing future data for detection
                    is_swing_high = False
                    break

        if is_swing_high:
            self.lines.swing_high[0] = current_high
        else:
            self.lines.swing_high[0] = float('nan')

        # Check for Swing Low (similar logic)
        current_low = self.data.low[0]

        is_swing_low = True
        for i in range(1, self.p.bars_left + 1):
            if self.data.low[-i] <= current_low:
                is_swing_low = False
                break
        if is_swing_low:
            for i in range(1, self.p.bars_right + 1):
                if self.data.low[i] <= current_low:  # Accessing future data for detection
                    is_swing_low = False
                    break

        if is_swing_low:
            self.lines.swing_low[0] = current_low
        else:
            self.lines.swing_low[0] = float('nan')

# Then in your strategy, you'd use:
# self.swing_points = SwingDetector(self.datas[0], bars_left=5, bars_right=5)
# And then iterate through self.swing_points.swing_high.array to find the last valid swing high, etc.


# def zigzag_percent_changes(df, threshold_percent=30):
#     close = df['close'].values
#     threshold = threshold_percent / 100

#     # Find local maxima and minima
#     peaks, _ = find_peaks(close)
#     troughs, _ = find_peaks(-close)
#     pivots = np.sort(np.concatenate([peaks, troughs]))
#     pivots = pivots[np.argsort(pivots)]  # ensure sorted

#     # Filter insignificant moves (threshold filtering)
#     filtered_pivots = [pivots[0]]
#     for i in range(1, len(pivots)):
#         prev_idx = filtered_pivots[-1]
#         curr_idx = pivots[i]
#         change = abs(close[curr_idx] - close[prev_idx]) / close[prev_idx]
#         if change >= threshold:
#             filtered_pivots.append(curr_idx)

#     # Calculate % change from previous pivot and % relative to last wave
#     percent_changes = []
#     relative_to_last_wave = []

#     for i in range(1, len(filtered_pivots)):
#         prev = filtered_pivots[i - 1]
#         curr = filtered_pivots[i]
#         change = (close[curr] - close[prev]) / close[prev] * 100
#         percent_changes.append(change)

#         if i > 1:
#             last_wave_change = percent_changes[-2]
#             relative = change / abs(last_wave_change) * 100
#             relative_to_last_wave.append(relative)
#         else:
#             relative_to_last_wave.append(np.nan)

#     # Build result DataFrame
#     pivot_times = df.iloc[filtered_pivots]['time'].values
#     pivot_prices = close[filtered_pivots]

#     result_df = pd.DataFrame({
#         'time': pivot_times,
#         'price': pivot_prices,
#         'change_from_prev': [np.nan] + percent_changes,
#         'change_vs_last_wave': [np.nan] + relative_to_last_wave,
#     })

#     return result_df, filtered_pivots


# def zigzag_percent_changes(prices, percent_threshold=0.3):
#     prices = np.array(prices)
#     pivots = [0]  # first index always a pivot
#     last_pivot = 0
#     direction = 0  # 0 = unknown, 1 = up, -1 = down

#     for i in range(1, len(prices)):
#         change = (prices[i] - prices[last_pivot]) / prices[last_pivot]
#         if direction == 0:
#             if abs(change) >= percent_threshold:
#                 direction = np.sign(change)
#                 pivots.append(i)
#                 last_pivot = i
#         elif direction == 1:  # up
#             if prices[i] > prices[last_pivot]:
#                 pivots[-1] = i
#                 last_pivot = i
#             elif prices[i] < prices[last_pivot] * (1 - percent_threshold):
#                 direction = -1
#                 pivots.append(i)
#                 last_pivot = i
#         elif direction == -1:  # down
#             if prices[i] < prices[last_pivot]:
#                 pivots[-1] = i
#                 last_pivot = i
#             elif prices[i] > prices[last_pivot] * (1 + percent_threshold):
#                 direction = 1
#                 pivots.append(i)
#                 last_pivot = i

#     pivot_idxs = np.array(pivots)
#     pivot_prices = prices[pivot_idxs]

#     # Calculate percent changes
#     pct_changes = np.diff(pivot_prices) / pivot_prices[:-1] * 100

#     # Relative to previous wave
#     relative_changes = [np.nan]  # first one has no prior wave
#     for i in range(1, len(pct_changes)):
#         prev = abs(pct_changes[i - 1])
#         curr = abs(pct_changes[i])
#         relative_changes.append(curr / prev if prev != 0 else np.nan)

#     return pivot_idxs, pivot_prices, pct_changes, relative_changes
