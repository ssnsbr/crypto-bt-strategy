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
