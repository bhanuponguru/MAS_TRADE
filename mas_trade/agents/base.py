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


class SignalAgent:
    """A hypothesis whose belief is mu = sign x ic_prior_mean x sigma_H x z, z a standardised signal (see the module docstring).
    Subclasses define signal(ctx), transform(raw) -> z, and the kill rule's statistic."""
    name = "signal"
    sign = 1                      # predicted sign of the skill (hypothesis card)
    ic_prior_mean = 0.02          # magnitude of the card's skill, with its source recorded in the card
    kill_t = -2.0                 # kill rule: t-statistic below this (in the card's sign) switches the agent off
    kill_min_obs = 20             # ... after this many periods
    neutral = True                # dollar- and beta-neutral book (False for an agent that owns net exposure)

    def __init__(self):
        self.last = None            # (tickers, z) of the previous decision

    def signal(self, ctx):
        raise NotImplementedError

    def transform(self, raw):
        raise NotImplementedError

    def killed(self):
        raise NotImplementedError

    def ic_hat(self):
        return 0.0 if self.killed() else self.sign * self.ic_prior_mean

    def belief(self, ctx):
        z = self.transform(self.signal(ctx))
        self.last = (list(ctx.tickers), z)
        return self.ic_hat() * ctx.sigma_h * z

    def record(self, z, f):
        raise NotImplementedError

    def observe(self, fwd):
        """fwd: {ticker: realised return over the period that followed the last decision}."""
        if self.last is None:
            return
        tick, z = self.last
        self.record(z, np.array([fwd.get(t, np.nan) for t in tick]))
        self.last = None


class RankAgent(SignalAgent):
    """Cross-sectional hypothesis: z is the rank-gauss of the signal; skill is the per-period rank IC, and the kill rule uses
    the t-statistic of its expanding mean."""
    name = "rank"

    def __init__(self):
        super().__init__()
        self.ics = []

    def transform(self, raw):
        return rank_gauss(raw)

    def record(self, z, f):
        ic = rank_ic(z, f)
        if np.isfinite(ic):
            self.ics.append(ic)

    def skill_summary(self):
        from ..diagnostics import ic_summary
        return ic_summary(self.ics)

    def killed(self):
        x = self.sign * np.array(self.ics)
        if len(x) < self.kill_min_obs or x.std(ddof=1) == 0:
            return False
        return bool(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) < self.kill_t)


class TimeSeriesAgent(SignalAgent):
    """Time-series hypothesis on a fixed set of coins: z is the clipped standardised own-trend of each coin, zero elsewhere;
    skill is the pooled slope of realised returns on z (uncentred, it includes the common market component that a
    cross-sectional IC removes), and the kill rule uses the t-statistic of that slope over the expanding window."""
    name = "timeseries"
    neutral = False
    coins = ()
    clip = 2.0

    def __init__(self):
        super().__init__()
        self.sss = self.szr = self.srr = 0.0
        self.n = 0                  # coin-period observations
        self.periods = 0

    def belief(self, ctx):
        raw = np.zeros(len(ctx.tickers))
        pick = [j for j, t in enumerate(ctx.tickers) if t in self.coins]
        if pick:
            raw[pick] = self.signal_of(ctx, pick)
        z = np.clip(raw, -self.clip, self.clip)
        self.last = (list(ctx.tickers), z)
        return self.ic_hat() * ctx.sigma_h * z

    def record(self, z, f):
        ok = np.isfinite(f) & (z != 0)
        if not ok.any():
            return
        self.sss += float((z[ok] ** 2).sum())
        self.szr += float((z[ok] * f[ok]).sum())
        self.srr += float((f[ok] ** 2).sum())
        self.n += int(ok.sum())
        self.periods += 1

    def _slope_t(self):
        if self.sss == 0 or self.n < 3:
            return np.nan, np.nan
        b = self.szr / self.sss
        resid = (self.srr - b * self.szr) / (self.n - 1)
        return b, (b * np.sqrt(self.sss) / np.sqrt(resid) if resid > 0 else np.nan)

    def skill_summary(self):
        b, t = self._slope_t()
        return {"slope": b, "t": t, "n": self.n}

    def killed(self):
        if self.periods < self.kill_min_obs:
            return False
        t = self._slope_t()[1]
        return bool(np.isfinite(t) and self.sign * t < self.kill_t)
