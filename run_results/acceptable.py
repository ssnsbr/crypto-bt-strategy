import numpy as np
import pandas as pd


class AcceptableStrategy:
    def __init__(self, metrics: dict):
        """
        metrics example:
        {
            "profitable_tokens%": 58,
            "total_pnl%": 35,
            "risk_reward_avg": 1.3,
            "geo_mean_return": 0.02,
            "max_drawdown": 45,
            "mean_depth": 4,
            "mean_hold_time": 1200
        }
        """
        self.m = metrics
        self.score = 0
        self.label = "❌ Reject"
        self.tag = "reject-0.0"

    def evaluate(self):
        m = self.m
        for k, v in m.items():
            if v is None or v is np.nan or v is pd.NA or v == "nan":
                m[k] = 0
        # --- Conservative profile ---
        conservative = (
            m["profitable_tokens%"] >= 60 and
            m["total_pnl%"] >= 20 and
            m["risk_reward_avg"] >= 1.4 and
            m["geo_mean_return"] > 0 and
            m["max_drawdown"] <= 40 and
            m["mean_depth"] <= 2
        )

        # --- Aggressive profile ---
        aggressive = (
            m["profitable_tokens%"] >= 50 and
            m["total_pnl%"] >= 50 and
            m["risk_reward_avg"] >= 1.2 and
            m["geo_mean_return"] > -0.05 and
            m["max_drawdown"] <= 70 and
            m["mean_depth"] <= 4
        )

        # --- Scalp profile ---
        scalp = (
            m["profitable_tokens%"] >= 65 and
            m["total_pnl%"] >= 10 and
            m["risk_reward_avg"] >= 1.1 and
            m["geo_mean_return"] > 0 and
            m["max_drawdown"] <= 30 and
            m["mean_hold_time"] <= 1800
        )

        # --- Base score system ---
        self.score += (m["profitable_tokens%"] - 50) / 10 * 0.2     # 10% = +0.2
        self.score += (m["total_pnl%"] / 100) * 0.5
        self.score += (m["risk_reward_avg"] - 1.0) * 0.3
        self.score -= (m["max_drawdown"] / 100) * 0.4
        self.score += (1 if m["geo_mean_return"] > 0 else -0.1)

        # Normalize score
        self.score = round(max(min(self.score, 1.0), -0.5), 2)
        if self.score is np.nan or self.score is pd.NA:
            self.score = -1
        # --- Label mapping ---
        if self.score < 0:
            self.label = "❌ Reject"
            self.tag = "reject"
        elif self.score < 0.3:
            self.label = "⚠️ Risky"
            self.tag = "risky"
        elif self.score < 0.7:
            self.label = "✅ Good"
            self.tag = "ok"
        elif self.score < 1.1:
            self.label = "🏆 Amazing"
            self.tag = "amazing"
        else:
            self.label = "Error!"
            self.tag = "error"

        # Override if profile matches stronger label
        if scalp or conservative or aggressive:
            if self.score < 0.7:
                self.score = 0.7
                self.label = "🏆 Amazing"
                self.tag = "amazing"

        return self.tag, self.score

    def print_result(self):
        print(f"Result: {self.label} | Score: {self.score:.2f}")
        for k, v in self.m.items():
            print(f"  {k:25s}: {v}")
        print(f"  Tag for DataFrame: {self.tag}")
