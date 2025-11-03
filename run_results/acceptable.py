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

        # --- Label mapping ---
        if self.score < 0:
            self.label = "❌ Reject"
            self.tag = f"reject{self.score}"
        elif self.score < 0.3:
            self.label = "⚠️ Risky"
            self.tag = f"risky{self.score}"
        elif self.score < 0.7:
            self.label = "✅ Good"
            self.tag = f"ok{self.score}"
        else:
            self.label = "🏆 Amazing"
            self.tag = f"amazing{self.score}"

        # Override if profile matches stronger label
        if scalp or conservative or aggressive:
            if self.score < 0.7:
                self.score = 0.7
                self.label = "🏆 Amazing"
                self.tag = f"amazing{self.score}"

        return self.tag

    def print_result(self):
        print(f"Result: {self.label} | Score: {self.score:.2f}")
        for k, v in self.m.items():
            print(f"  {k:25s}: {v}")
        print(f"  Tag for DataFrame: {self.tag}")
