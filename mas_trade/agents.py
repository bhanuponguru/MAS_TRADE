"""Strategy agents. Each forecasts expected returns mu (one per stock) from a past window.

Portfolio rule: w = mu / sum|mu|  ->  positive = long, negative = short, gross exposure = 1.
"""
import numpy as np

from .forecasting import ar1_forecast, ewma_mean_std, james_stein_mean


def weights_from_mu(mu):
    g = np.abs(mu).sum()
    return mu / g if g > 0 else np.zeros_like(mu)


class Agent:
    name = "agent"
    adversarial = False

    def forecast(self, window):  # window: (T x N) past daily returns
        raise NotImplementedError


class Momentum(Agent):
    name = "Momentum"

    def forecast(self, window):  # mean return of months t-12..t-1, skipping the latest month
        return window[:-21].mean(0)


class MeanReversion(Agent):
    name = "MeanReversion"

    def forecast(self, window):  # recent winners expected to fall, losers to rise
        return -window[-5:].mean(0)


class ShrinkageMean(Agent):
    name = "ShrinkageMean"

    def forecast(self, window):
        return james_stein_mean(window)


class AR1(Agent):
    name = "AR1"

    def forecast(self, window):
        return ar1_forecast(window)


class EWMATrend(Agent):
    name = "EWMATrend"

    def __init__(self, halflife=63):
        self.halflife = halflife

    def forecast(self, window):
        return ewma_mean_std(window, self.halflife)[0]


class LowVolTilt(Agent):
    name = "LowVolTilt"

    def __init__(self, lam=1.0):
        self.lam = lam

    def forecast(self, window):  # risk-penalized expected return
        return window.mean(0) - self.lam * window.var(0)


class AdversarialAgent(Agent):
    """Compromised agent: bets everything on one random stock, random side."""
    name = "Adversary"
    adversarial = True

    def __init__(self, seed=0):
        self.rng = np.random.default_rng(seed)

    def forecast(self, window):
        mu = np.zeros(window.shape[1])
        mu[self.rng.integers(window.shape[1])] = self.rng.choice([-1.0, 1.0])
        return mu


def default_agents():
    return [Momentum(), MeanReversion(), ShrinkageMean(), AR1(), EWMATrend(), LowVolTilt()]
