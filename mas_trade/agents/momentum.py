"""H2, time-series momentum (Moskowitz, Ooi, Pedersen 2012; Liu and Tsyvinski, Review of Financial Studies, on BTC, ETH and XRP):
an asset's own trailing return predicts its next return, at daily to weekly horizons in crypto.

Hypothesis card
- claim: a coin's trailing 30-day return, in units of its own volatility, predicts the sign and size of its return over the
  next holding period; the book is long a coin in an uptrend and short in a downtrend;
- mechanism: slow diffusion of information and overreaction/liquidation dynamics (Han, Kang, Ryu), concentrated in bull markets;
- universe: BTCUSDT and ETHUSDT only (the literature's per-asset version; on ~60 coins that move together a per-coin trend book
  would be a market bet plus a cross-sectional momentum tilt, whose IC measured about 0 on our data);
- sign +1; magnitude: ic_prior_mean = 0.05, a time-series predictive correlation (R^2 about 0.25%). This is an ASSUMPTION, chosen
  by a mechanical check without P&L (experiment 015): at the first value tried, 0.10, the agent's ex-ante annual Sharpe at its
  own belief was 1.17 on 1d, more than an out-of-sample time-series momentum Sharpe on BTC and ETH can be expected to deliver;
  at 0.05 it is about 0.6. No figure from the papers was verified;
- horizon: the holding period of the bar size; lookback 30 days (within the 1 to 8 weeks where Liu and Tsyvinski find
  predictability), not tuned;
- kill criterion: t-statistic of the pooled slope of returns on the signal below -2 after 20 periods;
- not neutral: it owns net market exposure, limited by the system beta band.
"""
import numpy as np

from .base import TimeSeriesAgent


class TimeSeriesMomentum(TimeSeriesAgent):
    name = "TSMomentum"
    coins = ("BTCUSDT", "ETHUSDT")
    universe = coins                    # enforced: the book holds BTC and ETH only, no hedges in other coins
    ic_prior_mean = 0.05

    def __init__(self, days=30.0):
        super().__init__()
        self.days = days

    def signal_of(self, ctx, pick):
        L = ctx.bars(self.days)
        r = ctx.R[-L:, pick]
        return r.sum(0) / (np.maximum(r.std(0), 1e-12) * np.sqrt(L))      # the t-statistic of the trailing return


class TimedMomentum(TimeSeriesMomentum):
    """H2 with timing inside the belief (decision 0039): the card's IC moves with two mechanism-based states, estimated walk-forward.

    IC(state) = IC0 + c . s, clipped to [0, 2 IC0]; s = (bull, panic), standardised on past states only:
    - bull: t-statistic of BTC's return over the history window (momentum is concentrated in bull markets: Han, Kang, Ryu);
      predicted coefficient >= 0;
    - panic: log of BTC's 30-day volatility over its window volatility (momentum crashes follow high-volatility rebounds:
      Daniel and Moskowitz); predicted coefficient <= 0.
    c is a ridge regression of each past period's skill y_t (the slope of the
    volatility-standardised returns on z) on the standardised states, with the Bayesian prior c ~ N(0, tau^2), tau = IC0 / 2 (a one
    standard deviation move of a state shifts the skill by at most about half the card): lam = var(y) / tau^2 pseudo-periods.
    A coefficient of the wrong predicted sign is set to zero. Until
    `min_obs` periods have been seen the belief is the untimed card's. The kill rule is unchanged."""
    name = "TSMomentumTimed"
    min_obs = 30

    def __init__(self, days=30.0):
        super().__init__(days)
        self.ys, self.ss, self._pending = [], [], None

    def state(self, ctx):
        b = ctx.btc
        L = len(b)
        bull = b.sum() / (max(b.std(), 1e-12) * np.sqrt(L))
        panic = np.log(max(b[-ctx.bars(self.days):].std(), 1e-12) / max(b.std(), 1e-12))
        return np.array([bull, panic])

    def timed_ic(self, s_now):
        ic0 = self.sign * self.ic_prior_mean
        if len(self.ys) < self.min_obs:
            return ic0
        S, y = np.array(self.ss), np.array(self.ys)
        m, sd = S.mean(0), np.maximum(S.std(0), 1e-12)
        Z = (S - m) / sd
        lam = y.var() / (0.5 * ic0) ** 2
        c = np.linalg.solve(Z.T @ Z + lam * np.eye(2), Z.T @ (y - y.mean()))
        c = np.array([max(c[0], 0.0), min(c[1], 0.0)])
        return float(np.clip(ic0 + c @ ((s_now - m) / sd), 0.0, 2.0 * ic0))

    def belief(self, ctx):
        mu = super().belief(ctx)                       # untimed card belief (sets self.last = (tickers, z))
        s = self.state(ctx)
        self._pending = (ctx.sigma_h.copy(), s)
        return mu * (0.0 if self.killed() else self.timed_ic(s) / self.ic_prior_mean)

    def record(self, z, f):
        sig, s = self._pending
        ok = np.isfinite(f) & (z != 0)
        if ok.any():
            self.ys.append(float((z[ok] * f[ok] / sig[ok]).sum() / (z[ok] ** 2).sum()))
            self.ss.append(s)
        super().record(z, f)
