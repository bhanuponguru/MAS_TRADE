"""Simple statistical forecasts: all use only past returns."""
import numpy as np
from scipy.special import ndtr  # standard normal CDF


def ewma_weights(n, halflife):
    w = 0.5 ** (np.arange(n)[::-1] / halflife)  # newest observation has weight 1
    return w / w.sum()


def ewma_mean_std(x, halflife):
    """Exponentially weighted mean and std along axis 0 of x (T x A)."""
    w = ewma_weights(len(x), halflife)
    m = w @ x
    return m, np.sqrt(w @ (x - m) ** 2)


def prob_positive(m, sd, H):
    """P(sum of next H daily returns > 0) = Phi(m * sqrt(H) / sd), normal approximation."""
    return ndtr(m * np.sqrt(H) / np.maximum(sd, 1e-12))


def ar1_forecast(window):
    """Per-stock OLS fit r[t+1] = a + b r[t]; returns the one-step-ahead prediction."""
    x, y = window[:-1], window[1:]
    xm, ym = x.mean(0), y.mean(0)
    b = ((x - xm) * (y - ym)).sum(0) / np.maximum(((x - xm) ** 2).sum(0), 1e-18)
    return ym + b * (window[-1] - xm)


def james_stein_mean(window):
    """Sample means shrunk toward their cross-sectional average (James-Stein)."""
    T, N = window.shape
    xbar = window.mean(0)
    grand = xbar.mean()
    var_of_mean = window.var(0, ddof=1).mean() / T
    shrink = max(0.0, 1.0 - (N - 3) * var_of_mean / max(((xbar - grand) ** 2).sum(), 1e-18))
    return grand + shrink * (xbar - grand)


def trust_scores(history, H, halflife, power=1.0, min_obs=20):
    """Forecast reward of each agent -> trust s_i = P(agent profitable next period).

    history: (T x A) realized daily returns of each agent's standalone portfolio.
    """
    A = history.shape[1]
    if len(history) < min_obs:
        return np.ones(A)
    m, sd = ewma_mean_std(history, halflife)
    return np.maximum(prob_positive(m, sd, H), 1e-6) ** power
