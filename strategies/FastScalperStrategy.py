
from riskmanagers.BaseRiskManagement import BaseRiskManagement
from strategies.Base import BaseTradingStrategy


class FastScalperStrategy(BaseTradingStrategy):
    params = (
        ('rsi_buy_threshold', 40),
        ("martingale_loss_trigger", 0.1)
    )

    def __init__(self):
        super().__init__()  # Call the base class constructor

        self.has_done_initial_buy = False           # Flag to ensure initial buy happens only once per cycle
        self.current_fibo_buy_level_idx = 0         # Index to track which Fibo level is next for a buy
        self.next_buy_amount_quantity = 0.0         # Calculated quantity for the next martingale buy

        self.current_fibo_buy_level_idx = 0
        self.next_buy_amount_quantity = 0.0
        # Access position dynamically via self.getposition() when needed.
        # Instantiate the RiskManagement class
        self.risk_manager = BaseRiskManagement(self)

    def _execute_trading_logic(self):

        # # ------------------------ Part 1: Take Profit Check ------------------------
        # # Check for TP (this is handled by the risk_manager)
        # if self.risk_manager.check_and_execute_take_profit(self.current_price):
        #     return  # Exit after placing TP order

        # # ------------------------ Part 2: Entry and Martingale ------------------------
        # Check if we are in a position
        current_position_size = self.getposition(self.datas[0]).size

        # --- Calculate current PnL percentage (required for -10% loss trigger) ---
        pnl_percent = 0.0
        if current_position_size > 0:
            # Calculate PnL percentage based on average buy price and current price
            # Note: Backtrader's position object's .price is the average entry price.
            pnl_percent = (self.current_price / self.portfolio_avg_buy_price) - 1.0

        # --- Execution Logic ---
        # Scenario 1: Initial Buy (No open position, RSI < 40)
        if current_position_size == 0 and self.rsi[0] < self.p.rsi_buy_threshold:
            if self.broker.getcash() > 0:
                self.log(f'INITIAL BUY (RSI < 40): Attempting to buy at {self._format_value_for_log_mcap(self.current_price)} price.')
                self.buy()  # Sizer defines the buy size.
                # After the buy, _update_portfolio_stats and has_done_initial_buy flags will be set via notify_order.
            else:
                self.log("Martingale Buy Skipped: Not enough cash.")

        # Scenario 2: Martingale Buy (Open position, PnL < -10%, RSI < 40)
        # We will add if PnL is -10% or lower and RSI < 40 (optional, but safer).
        elif current_position_size > 0 and pnl_percent <= self.p.martingale_loss_trigger and self.rsi[0] < 40:
            if self.broker.getcash() > 0:
                self.log(f'MARTINGALE BUY (PnL {pnl_percent*100:.2f}%): Adding position at {self._format_value_for_log_mcap(self.current_price)} price.')
                self.buy()
            else:
                self.log("Martingale Buy Skipped: Not enough cash.")
