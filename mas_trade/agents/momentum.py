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
    ic_prior_mean = 0.05

    def __init__(self, days=30.0):
        super().__init__()
        self.days = days

    def signal_of(self, ctx, pick):
        L = ctx.bars(self.days)
        r = ctx.R[-L:, pick]
        return r.sum(0) / (np.maximum(r.std(0), 1e-12) * np.sqrt(L))      # the t-statistic of the trailing return
