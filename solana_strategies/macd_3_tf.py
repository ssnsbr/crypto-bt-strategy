import backtrader as bt


class SOL_MTF_MACD_Trend(BaseCryptoTradingStrategy):
    """
    Multi-Timeframe MACD Trend Strategy (1m base)
    - Big TF (1h): MACD line > 0 → long bias, < 0 → short bias
    - Mid TF (15m): MACD crossover far from 0 confirms trend direction
    - Small TF (1m): MACD histogram turns green/red → entry trigger
    """

    params = (
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        ('hist_thr', 0.0),     # 1m histogram threshold for entry
        ('mid_cross_thr', 0.05),
        ('tp_percent', 0.02),
        ('sl_percent', 0.02),
        ('log', True),
    )

    def __init__(self):
        super().__init__()

        # === MACD on 1m (base TF) ===
        self.macd_small = bt.indicators.MACD(self.datas[0],
                                             period_me1=self.p.macd_fast,
                                             period_me2=self.p.macd_slow,
                                             period_signal=self.p.macd_signal)
        # === Approximate 15m MACD ===
        self.macd_mid = bt.indicators.MACD(self.datas[0],
                                           period_me1=self.p.macd_fast * 15,
                                           period_me2=self.p.macd_slow * 15,
                                           period_signal=self.p.macd_signal * 15)
        # === Approximate 1h MACD ===
        self.macd_big = bt.indicators.MACD(self.datas[0],
                                           period_me1=self.p.macd_fast * 60,
                                           period_me2=self.p.macd_slow * 60,
                                           period_signal=self.p.macd_signal * 60)

        self.order = None
        self.last_mid_sign = 0

    def _execute_trading_logic(self):
        if self.order:
            return

        pos = self.getposition(self.datas[0])
        price = self.dataclose[0]

        macd_big = self.macd_big.macd[0]
        macd_mid = self.macd_mid.macd[0]
        macd_mid_sig = self.macd_mid.signal[0]
        macd_small_hist = self.macd_small.macd[0] - self.macd_small.signal[0]

        # --- Big TF filter ---
        long_bias = macd_big > 0
        short_bias = macd_big < 0

        # --- Mid TF crossover detection ---
        mid_cross_up = macd_mid > macd_mid_sig and self.last_mid_sign <= 0
        mid_cross_down = macd_mid < macd_mid_sig and self.last_mid_sign >= 0
        self.last_mid_sign = macd_mid - macd_mid_sig

        # --- Entry logic ---
        if not pos:
            # Long setup
            if long_bias and mid_cross_up and abs(macd_mid) > self.p.mid_cross_thr and macd_small_hist > self.p.hist_thr:
                self.order = self.buy()
                if self.p.log:
                    self.log(f"BUY: big>0, mid cross up, hist green @ {price:.2f}")

            # Short setup
            elif short_bias and mid_cross_down and abs(macd_mid) > self.p.mid_cross_thr and macd_small_hist < -self.p.hist_thr:
                self.order = self.sell()
                if self.p.log:
                    self.log(f"SELL: big<0, mid cross down, hist red @ {price:.2f}")

        # --- Exit logic ---
        else:
            # For longs, exit on opposite histogram color
            if pos.size > 0 and macd_small_hist < -self.p.hist_thr:
                self.close()
                if self.p.log:
                    self.log(f"Exit LONG @ {price:.2f}")

            # For shorts, exit on opposite histogram color
            elif pos.size < 0 and macd_small_hist > self.p.hist_thr:
                self.close()
                if self.p.log:
                    self.log(f"Exit SHORT @ {price:.2f}")

    def stop(self):
        pos = self.getposition(self.datas[0])
        if pos.size != 0:
            self.log(f"END OF BACKTEST: Closing position {pos.size} @ {self.dataclose[0]:.2f}")
            self.close()
        super().stop()
