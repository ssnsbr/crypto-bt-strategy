import backtrader as bt


class CustomSolanaCommission(bt.CommissionInfo):
    params = (
        ('commission', 0.0095),  # 0.95% as a decimal
        ('sol_bribe_fee', 0.0001),
        ('sol_priority_fee', 0.0001),
        ('sol_price_usd', 150.0),
        ('percabs', True),
        ('stocklike', True),
        ('commtype', bt.CommInfoBase.COMM_PERC),
    )

    def _getcommission(self, size, price, pseudoexec=None):
        # Percentage-based commission
        perc_commission = abs(size) * price * self.p.commission

        # Fixed SOL fee in USD
        fixed_sol_fee_usd = (self.p.sol_bribe_fee + self.p.sol_priority_fee) * self.p.sol_price_usd
        # fixed_sol_fee_usd = self.p.sol_fixed_fee * self.p.sol_price_usd

        total_commission = perc_commission + fixed_sol_fee_usd
        return total_commission
