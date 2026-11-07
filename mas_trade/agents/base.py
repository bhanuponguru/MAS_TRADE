"""The agent interface and a rank-signal agent whose belief scale comes from its hypothesis card.

An agent sees only information before the decision bar (a Ctx for the tradable coins) and returns a belief: the expected
net return of a unit position in each coin over the holding period, mu = IC x sigma_H x z (Grinold). For an established
hypothesis the IC is the CARD's: a small number of the card's predicted sign (`ic_prior_mean`). Evidence does not rescale it
(a trailing IC is too noisy to size bets by: its sign flipped half the time on carry); it can only switch the agent off, by a
separate pre-registered kill rule: when the expanding-window mean IC, in the card's sign, has a t-statistic below
`kill_t` (after `kill_min_obs` periods) the agent goes quiet (belief 0), it never bets the opposite. Relative stakes between
agents are then set by wealth, not by noisy IC estimates. Nothing is initialised randomly.
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
    ic_prior_mean = 0.02          # magnitude of the card's IC
    kill_t = -2.0                 # kill rule: t-stat of the expanding mean IC (in the card's sign) below this
    kill_min_obs = 20             # ... after this many periods

    def __init__(self):
        self.ics = []
        self.last = None            # (tickers, z) of the previous decision

    def signal(self, ctx):
        raise NotImplementedError

    def killed(self):
        x = self.sign * np.array(self.ics)
        if len(x) < self.kill_min_obs or x.std(ddof=1) == 0:
            return False
        return bool(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) < self.kill_t)

    def ic_hat(self):
        return 0.0 if self.killed() else self.sign * self.ic_prior_mean

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
