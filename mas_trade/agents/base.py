"""The agent interface and a rank-signal agent calibrated by its own realised IC.

An agent sees only information before the decision bar (a Ctx for the tradable coins) and returns a belief: the expected
net return of a unit position in each coin over the holding period. A belief is mu = IC_hat x sigma_H x z (Grinold).
IC_hat is the posterior mean of the agent's rank-IC: the EWMA of its own realised ICs, shrunk toward the PRIOR OF ITS
HYPOTHESIS CARD (a small IC of the card's sign, `ic_prior_mean`, worth `ic_prior` pseudo-observations), and clipped to the
card's sign: a hypothesis does not silently flip into its opposite on a bad stretch (a sustained wrong sign is a kill
criterion for the card, handled by permission and wealth), it goes quiet. Nothing is initialised randomly.
"""
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from ..diagnostics import rank_ic


@dataclass
class Ctx:
    """Past windows (no NaN) of the tradable coins; row -1 is the last bar before the decision."""
    R: np.ndarray        # (T, n) per-bar returns
    F: np.ndarray        # (T, n) funding paid by longs
    V: np.ndarray        # (T, n) dollar volume per bar
    btc: np.ndarray      # (T,) BTC returns
    tickers: list
    bpd: int
    sigma_h: np.ndarray  # (n,) std of the return over one holding period

    def bars(self, days):
        return max(1, int(round(days * self.bpd)))


def rank_gauss(s):
    r = np.argsort(np.argsort(s, kind="stable"), kind="stable")
    return norm.ppf((r + 0.5) / len(s))


class RankAgent:
    """Subclasses implement signal(ctx) -> (n,) with higher = expected to do better."""
    name = "rank"

    sign = 1                      # predicted sign of the IC (hypothesis card)
    ic_prior_mean = 0.02          # magnitude of the card's prior IC

    def __init__(self, ic_halflife=12.0, ic_prior=50.0):
        self.lam = 0.5 ** (1.0 / ic_halflife)
        self.prior = ic_prior
        self.ics = []
        self.last = None            # (tickers, z) of the previous decision

    def signal(self, ctx):
        raise NotImplementedError

    def ic_hat(self):
        x = np.array(self.ics)
        w = self.lam ** np.arange(len(x) - 1, -1, -1)
        post = ((x * w).sum() + self.prior * self.sign * self.ic_prior_mean) / (w.sum() + self.prior)
        return float(max(self.sign * post, 0.0) * self.sign)

    def belief(self, ctx):
        z = rank_gauss(self.signal(ctx))
        self.last = (list(ctx.tickers), z)
        return self.ic_hat() * ctx.sigma_h * z

    def observe(self, fwd):
        """fwd: {ticker: realised return over the period that followed the last decision}. Updates the IC history."""
        if self.last is None:
            return
        tick, z = self.last
        f = np.array([fwd.get(t, np.nan) for t in tick])
        ic = rank_ic(z, f)
        if np.isfinite(ic):
            self.ics.append(ic)
        self.last = None
