# ------------------------------------------------------------
# Unified Regime Engine
# ------------------------------------------------------------
class RegimeEngine:
    def __init__(self, detectors=None):
        if detectors is None:
            detectors = [
                VolatilityRegime(),
                SqueezeRegime(),
                TrendStrengthRegime(),
                LiquidityRegime(),
                StructuralRegime(),
                HurstRegime(),
                NoiseRegime(),
                HMMRegime(),
            ]
        self.detectors = detectors

    def compute_all(self, df):
        results = {}
        for det in self.detectors:
            res = det.compute(df)

            # If detector returns a dict, store whole dict
            # If detector returns a number, wrap it
            if isinstance(res, dict):
                results[det.name] = res
            else:
                results[det.name] = {"score": float(res)}

        return results

    def combined_score(self, df, weights=None):
        results = self.compute_all(df)

        # Default equal weights
        if weights is None:
            weights = {name: 1 for name in results.keys()}

        total_weight = sum(weights.values())

        combined = 0
        for name, res in results.items():
            score = res["score"]  # <--- the key fix
            combined += score * weights[name]

        combined /= total_weight

        return combined, results
