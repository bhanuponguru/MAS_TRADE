"""H4, short-term residual reversal (Jegadeesh 1990; Gunther, Fieberg, Poddig on crypto characteristics): a coin that fell more than
the market over the last days tends to rebound, because price pressure from liquidity demand is temporary.

Hypothesis card
- claim: a coin's trailing 7-day return in excess of its BTC beta (the residual), in units of its own volatility, predicts the
  OPPOSITE sign of its next residual return; the book is long the recent losers and short the recent winners within the cross-section;
- mechanism: liquidity provision: price moves caused by demand for immediacy partly reverse; stronger in less liquid coins;
- universe: the tradable coins (the $1M daily-volume floor of the engine); neutral book (dollar and beta);
- sign +1 on the negated signal; magnitude `ic_prior_mean` = 0.02, the same as carry. It is an ASSUMPTION fixed before any run of this
  agent in the new engine, and deliberately below the 0.025 / 0.039 / 0.049 rank ICs measured for the legacy implementation on the same
  development data (1d / 4h / 1h, experiment 006): those numbers come from the data we decide on, so they are not independent evidence;
- horizon: the holding period of the bar size; lookback 7 days (the legacy default, not tuned);
- kill criterion: t-statistic of the mean rank IC below -2 after 20 periods (the base-class rule);
- diagnostic, not gate: rank IC by liquidity tercile (does it concentrate in the less liquid coins?).
"""
import numpy as np

from ..diagnostics import ic_summary, rank_ic
from .base import RankAgent


class RankReversal(RankAgent):
    name = "RankReversal"
    ic_prior_mean = 0.02

    def __init__(self, days=7.0):
        super().__init__()
        self.days = days
        self.ics_by_liquidity = [[], [], []]

    def signal(self, ctx):
        rb, R = ctx.btc, ctx.R
        beta = ((R - R.mean(0)) * (rb - rb.mean())[:, None]).sum(0) / max(((rb - rb.mean()) ** 2).sum(), 1e-12)
        resid = R - rb[:, None] * beta
        n = ctx.bars(self.days)
        return -resid[-n:].sum(0) / (np.maximum(resid.std(0), 1e-12) * np.sqrt(n))     # long the losers

    def belief(self, ctx):
        mu = super().belief(ctx)
        v = ctx.V.mean(0)
        self._tercile = np.digitize(v, np.quantile(v, [1 / 3, 2 / 3]))          # 0 = least liquid third of the tradable coins
        return mu

    def record(self, z, f):
        super().record(z, f)
        for k in range(3):
            ic = rank_ic(z[self._tercile == k], f[self._tercile == k])
            if np.isfinite(ic):
                self.ics_by_liquidity[k].append(ic)

    def liquidity_summary(self):
        """Diagnostic, not a gate: the rank IC within each liquidity tercile of the tradable coins (0 = least liquid)."""
        return {f"IC tercile {k} (0 = least liquid)": ic_summary(self.ics_by_liquidity[k])["IC"] for k in range(3)}
