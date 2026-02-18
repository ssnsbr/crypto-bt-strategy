import math


# -------------------------------
# Approximate quantile estimator (P² algorithm)
# -------------------------------
class P2Quantile:
    def __init__(self, q):
        self.q = q
        self.n = 0
        self.initial = []
        self.markers = None

    def update(self, x):
        self.n += 1
        if self.n <= 5:
            self.initial.append(x)
            if self.n == 5:
                self.initial.sort()
                self.markers = {
                    'q': self.initial[:],
                    'n': [1, 2, 3, 4, 5],
                    'np': [
                        1,
                        1 + 2 * self.q,
                        1 + 4 * self.q,
                        3 + 2 * self.q,
                        5,
                    ],
                    'dn': [0, self.q / 2, self.q, (1 + self.q) / 2, 1],
                }
            return

        q = self.markers['q']
        n = self.markers['n']
        np = self.markers['np']
        dn = self.markers['dn']

        # find k
        # k = max(i for i in range(5) if x >= q[i])
        k = max((i for i in range(5) if x >= q[i]), default=0)

        if k == 4:
            q[4] = x
        elif k == 0:
            q[0] = x
        else:
            q[k] = x

        for i in range(5):
            np[i] += dn[i]

        for i in range(1, 4):
            d = np[i] - n[i]
            if (d >= 1 and n[i + 1] - n[i] > 1) or (d <= -1 and n[i - 1] - n[i] < -1):
                d = int(math.copysign(1, d))
                q[i] = self._parabolic(i, d) or self._linear(i, d)
                n[i] += d

    def _parabolic(self, i, d):
        q, n = self.markers['q'], self.markers['n']
        try:
            return q[i] + d / (n[i + 1] - n[i - 1]) * (
                (n[i] - n[i - 1] + d) * (q[i + 1] - q[i]) / (n[i + 1] - n[i]) +
                (n[i + 1] - n[i] - d) * (q[i] - q[i - 1]) / (n[i] - n[i - 1])
            )
        except ZeroDivisionError:
            return None

    def _linear(self, i, d):
        q, n = self.markers['q'], self.markers['n']
        return q[i] + d * (q[i + d] - q[i]) / (n[i + d] - n[i])

    def value(self):
        if not self.markers:
            return None
        return self.markers['q'][2]


class StreamingStats:
    """
    Streaming statistics using numerically stable online algorithms.
    No full history stored.
    """

    def __init__(self):
        self.n = 0

        # Welford mean / variance
        self.mean = 0.0
        self.M2 = 0.0

        # Extremes
        self.min = float('inf')
        self.max = float('-inf')

        # Drift / slope
        self.sum_x = 0.0
        self.sum_x2 = 0.0
        self.sum_y = 0.0
        self.sum_xy = 0.0

        # Regime structure
        self.prev = None
        self.sign_prev = None
        self.regime_flips = 0

        # Entry / last
        self.entry = None
        self.last = None

        # Quantiles
        self.q25 = P2Quantile(0.25)
        self.q50 = P2Quantile(0.50)
        self.q75 = P2Quantile(0.75)

    # -------------------------------
    def update(self, value):
        self.n += 1
        x = self.n
        y = value

        # Entry / last
        if self.n == 1:
            self.entry = y
        self.last = y

        # Mean / variance (Welford)
        delta = y - self.mean
        self.mean += delta / self.n
        delta2 = y - self.mean
        self.M2 += delta * delta2

        # Extremes
        self.min = min(self.min, y)
        self.max = max(self.max, y)

        # Linear regression sums
        self.sum_x += x
        self.sum_y += y
        self.sum_x2 += x * x
        self.sum_xy += x * y

        # Regime flip detection
        if self.prev is not None:
            sign = 1 if y > self.prev else -1 if y < self.prev else 0
            if self.sign_prev is not None and sign != self.sign_prev and sign != 0:
                self.regime_flips += 1
            self.sign_prev = sign
        self.prev = y

        # Quantiles
        self.q25.update(y)
        self.q50.update(y)
        self.q75.update(y)

    # -------------------------------
    def variance(self):
        return self.M2 / (self.n - 1) if self.n > 1 else 0.0

    def std(self):
        return math.sqrt(self.variance())

    def slope(self):
        denom = self.n * self.sum_x2 - self.sum_x ** 2
        if denom == 0:
            return 0.0
        return (self.n * self.sum_xy - self.sum_x * self.sum_y) / denom

    def slope_norm(self):
        s = self.slope()
        return s / (self.std() + 1e-9)

    def drift(self):
        if self.entry is None:
            return 0.0
        return self.last - self.entry

    def iqr(self):
        q1 = self.q25.value()
        q3 = self.q75.value()
        if q1 is None or q3 is None:
            return None
        return q3 - q1

    def zscore(self, value=None):
        if self.std() == 0:
            return 0.0
        v = self.last if value is None else value
        return (v - self.mean) / self.std()

    # -------------------------------
    def export(self):
        return {
            'n': self.n,
            'mean': self.mean,
            'std': self.std(),
            'var': self.variance(),
            'min': self.min,
            'max': self.max,
            'range': self.max - self.min,
            'iqr': self.iqr(),
            'median': self.q50.value(),
            'slope': self.slope(),
            'slope_norm': self.slope_norm(),
            'drift': self.drift(),
            'regime_flips': self.regime_flips,
        }


class EWStreamingStats:
    """
    Exponentially-weighted streaming stats
    Reacts fast to regime changes
    """

    def __init__(self, alpha=0.1):
        self.alpha = alpha
        self.mean = None
        self.var = 0.0
        self.last = None
        self.entry = None
        self.n = 0

    def update(self, x):
        self.n += 1

        if self.mean is None:
            self.mean = x
            self.entry = x
            self.last = x
            return

        diff = x - self.mean
        self.mean += self.alpha * diff
        self.var = (1 - self.alpha) * (self.var + self.alpha * diff * diff)
        self.last = x

    def std(self):
        return math.sqrt(self.var)

    def drift(self):
        return self.last - self.entry if self.entry is not None else 0.0

    def zscore(self):
        s = self.std()
        if s == 0:
            return 0.0
        return (self.last - self.mean) / s

    def export(self):
        return {
            'ew_mean': self.mean,
            'ew_std': self.std(),
            'ew_drift': self.drift(),
            'ew_z': self.zscore(),
        }


class ReturnStats:
    """
    Streaming log-return statistics
    """

    def __init__(self):
        self.prev = None
        self.stats = StreamingStats()
        self.sign_changes = 0
        self.prev_sign = None

    def update(self, price):
        if self.prev is None:
            self.prev = price
            return

        r = math.log(price / self.prev)
        self.stats.update(r)

        sign = 1 if r > 0 else -1 if r < 0 else 0
        if self.prev_sign is not None and sign != self.prev_sign:
            self.sign_changes += 1
        self.prev_sign = sign

        self.prev = price

    def entropy(self):
        # Shannon entropy approximation from sign balance
        p = abs(self.stats.mean) / (self.stats.std() + 1e-9)
        p = max(min(p, 1), 0)
        return -p * math.log(p + 1e-9) - (1 - p) * math.log(1 - p + 1e-9)

    def export(self):
        d = self.stats.export()
        d.update({
            'ret_entropy': self.entropy(),
            'ret_sign_flips': self.sign_changes,
        })
        return d


class TradePathStats:
    """
    MAE / MFE streaming stats
    """

    def __init__(self, entry_price, direction):
        self.entry = entry_price
        self.dir = direction  # +1 long, -1 short
        self.mae = 0.0
        self.mfe = 0.0
        self.t_mae = 0
        self.t_mfe = 0
        self.t = 0

    def update(self, price):
        self.t += 1
        pnl = self.dir * (price - self.entry)

        if pnl < self.mae:
            self.mae = pnl
            self.t_mae = self.t

        if pnl > self.mfe:
            self.mfe = pnl
            self.t_mfe = self.t

    def export(self):
        return {
            'mae': self.mae,
            'mfe': self.mfe,
            't_mae': self.t_mae,
            't_mfe': self.t_mfe,
            'mae_to_mfe_time_ratio':
                self.t_mae / max(self.t_mfe, 1),
        }


class TimeframeAlignment:
    """
    HTF / LTF regime alignment metrics
    """

    def __init__(self):
        self.ltf = StreamingStats()
        self.htf = StreamingStats()

    def update(self, ltf_val, htf_val):
        self.ltf.update(ltf_val)
        self.htf.update(htf_val)

    def alignment_score(self):
        # cosine-like directional agreement
        return math.copysign(
            min(abs(self.ltf.slope()), abs(self.htf.slope())),
            self.ltf.slope() * self.htf.slope()
        )

    def divergence(self):
        return abs(self.ltf.mean - self.htf.mean)

    def export(self):
        return {
            'ltf_slope': self.ltf.slope(),
            'htf_slope': self.htf.slope(),
            'tf_alignment': self.alignment_score(),
            'tf_divergence': self.divergence(),
        }
