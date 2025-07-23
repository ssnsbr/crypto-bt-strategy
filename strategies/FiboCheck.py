
from riskmanagers.BaseRiskManagement import BaseRiskManagement
from strategies.Base import BaseTradingStrategy


class FiboChecker(BaseTradingStrategy):
    # Fibonacci_Retracement_important = [0.236, 0.382, 0.500, 0.618, 0.786, 1]
    # Fibonacci_Levels = [0.146, 0.236, 0.382, 0.500, 0.618, 0.786, 1.000, 1.272, 1.382, 1.500, 1.618, 2, 2.618, 3.33, 4.236]
    Fibonacci_Retracement_important = [0.013, 0.021, 0.027, 0.034, 0.044, 0.056, 0.071, 0.09, 0.115, 0.146, 0.236, 0.382, 0.500, 0.618, 0.786, 1.000, 1.272, 1.382, 1.500, 1.618, 2, 2.618, 3.33, 4.236]
    # Fibonacci_Retracement_important = [0.013, 0.021, 0.027, 0.034, 0.044, 0.056, 0.071, 0.09, 0.115, 0.146, 0.236, 0.382, 0.500, 0.618, 0.786, 1.000, 1.272, 1.382, 1.500, 1.618, 2]

    def __init__(self):
        super().__init__()  # Call the base class constructor
        # Instantiate the RiskManagement class
        self.risk_manager = BaseRiskManagement(self)
        self.buying = False
        self.tp = 0
        self.current_fibo = 0
        self.Fibonacci_Buy_MCAP = {k: 0 for k in self.Fibonacci_Retracement_important}
        self.fibo_touched_state = {k: False for k in self.Fibonacci_Retracement_important}  # Track per-level entry state
        self.current_fibo_index = -1
        self.fibo_ath = 0
        self.use_fib_ath = True
        # self.use_fib_ath = False
        self.up_counter = {k: 0 for k in self.Fibonacci_Retracement_important}
        self.down_counter = {k: 0 for k in self.Fibonacci_Retracement_important}
        self.counter_updated = False
        self.use_fib_ath_updater_value = 1.272  # one of 1.000, 1.272, 1.382, 1.500, 1.618, 2, 2.618, 3.33, 4.236

    def update_fibo(self):
        self.Fibonacci_Buy_MCAP = {k: k * self.ath for k in self.Fibonacci_Retracement_important}
        self.fibo_touched_state = {k: False for k in self.Fibonacci_Retracement_important}  # Reset states on ATH update
        print("Updating Fibo", {k: self._format_value_for_log_mcap(v) for k, v in self.Fibonacci_Buy_MCAP.items()})
        self.current_fibo_index = self.Fibonacci_Retracement_important.index(1)  # index of 1
        self.current_fibo = 1

    def update_fibo_ath(self):
        """ 
        When self.use_fib_ath, we will update ATH when the price reaches 2 * past_ATH
        """
        if self.current_fibo_index == self.Fibonacci_Retracement_important.index(self.use_fib_ath_updater_value):  # index of 2
            self.fibo_ath = self.current_price
            self.update_fibo()

    def update_ath(self):
        if super().update_ath():
            if self.fibo_ath == 0:
                self.fibo_ath = self.ath
                self.update_fibo()

            if not self.use_fib_ath:
                self.update_fibo()

    def check_fibo_touch(self, jump_counter=0, jump_direction=None):
        """
        Tracks and logs when price crosses into the next higher or lower Fibonacci level.
        Updates current_fibo_index accordingly.
        """
        tolerance = 0.02  # 2% buffer
        if jump_counter > 10:
            10 / 0
        # Check downward touch
        if 0 < self.current_fibo_index and (jump_direction is None or jump_direction == 'down'):
            below_index = self.current_fibo_index - 1
            below_fibo = self.Fibonacci_Retracement_important[below_index]
            below_level = self.Fibonacci_Buy_MCAP[below_fibo]
            upper_bound = below_level * (1 + tolerance)
            # print(f"Current Level is {self.current_fibo_index}:{self.current_fibo}, Checking with Below which is {below_index}:{below_fibo}")

            if self.current_price <= upper_bound:
                if jump_counter:
                    print(" " + "↓" * (jump_counter + 1) + f"  Price touched Fibonacci Level {below_fibo} at {self._format_value_for_log_mcap(self.current_price)} ({self._format_value_for_log_mcap(below_level)})")

                else:
                    print(f" ↓  Price touched Fibonacci Level {below_fibo} at {self._format_value_for_log_mcap(self.current_price)} ({self._format_value_for_log_mcap(below_level)})")
                self.down_counter[self.current_fibo] = self.down_counter[self.current_fibo] + 1
                self.counter_updated = True
                self.current_fibo_index = below_index
                self.current_fibo = below_fibo
                self.check_fibo_touch(jump_counter + 1, jump_direction="down")
                self.buy()

        # Check upward touch
        if 0 < self.current_fibo_index < len(self.Fibonacci_Retracement_important) - 1 and (jump_direction is None or jump_direction == 'up'):
            above_index = self.current_fibo_index + 1
            above_fibo = self.Fibonacci_Retracement_important[above_index]
            above_level = self.Fibonacci_Buy_MCAP[above_fibo]
            lower_bound = above_level * (1 - tolerance)
            # print(f"Current Level is {self.current_fibo_index}:{self.current_fibo}, Checking with Above which is {above_index}:{above_fibo}")

            if self.current_price >= lower_bound:
                if jump_counter:
                    print(" " + "↑" * (jump_counter + 1) + f"  Price touched Fibonacci Level {above_fibo} at {self._format_value_for_log_mcap(self.current_price)} ({self._format_value_for_log_mcap(above_level)})")
                else:
                    print(f" ↑  Price touched Fibonacci Level {above_fibo} at {self._format_value_for_log_mcap(self.current_price)} ({self._format_value_for_log_mcap(above_level)})")
                self.current_fibo_index = above_index
                self.current_fibo = above_fibo
                self.up_counter[self.current_fibo] = self.up_counter[self.current_fibo] + 1
                self.counter_updated = True
                self.update_fibo_ath()
                self.check_fibo_touch(jump_counter + 1, jump_direction="up")
                self.close()

    def _execute_trading_logic(self):
        if self.ath <= 0.0:
            return

        self.check_fibo_touch(0)  # Log Fibonacci level touch
        if self.current_price < 30_000 and self.counter_updated:
            print(f"# Using Fibo {self.use_fib_ath}, Updater: {self.use_fib_ath_updater_value}, Down: {sum(self.down_counter.values())}, Up: {sum(self.up_counter.values())}")
            print("down_coounter", sum(self.down_counter.values()), self.down_counter)
            print("up_counter", sum(self.up_counter.values()), self.up_counter)

            self.counter_updated = False
        # You can still add other logic here if needed

# Using Fibo True, Updater: 2, Down: 89, Up: 94
# Using Fibo True, Updater: 1.618, Down: 73, Up: 82
# Using Fibo True, Updater: 1.272, Down: 58, Up: 55
# Using Fibo True, Updater: 1, Down: 100, Up: 85

# Using Fibo False, Updater: 1.618, Down: 63, Up: 47
# Using Fibo False, Updater: 1, Down: 63, Up: 47
