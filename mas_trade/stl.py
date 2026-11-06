"""Signal Temporal Logic (STL): quantitative semantics and signals.

Robustness rho > 0 <=> spec satisfied, |rho| = margin, on discrete traces:
  predicate  x <= c  ->  rho = (c - x)/|c|        x >= c  ->  rho = (x - c)/|c|     (normalised by the limit)
  not phi -> -rho     phi and psi -> min     phi or psi -> max     phi -> psi  ==  (not phi) or psi
  G[a,b] phi (always)      rho(t) = min rho_phi(t'),  t' in [t+a, t+b]
  F[a,b] phi (eventually)  rho(t) = max rho_phi(t'),  t' in [t+a, t+b]
  H[a,b] / O[a,b]          past-time versions over t' in [t-b, t-a] (computable online at t)
Finite traces are truncated: a window running past the end of the trace uses only what exists.

Normalising by the limit makes margins of different specs comparable (rho = 0.5 means half the limit is left),
which is what lets a margin act as a continuous scaling signal for an agent's Kelly fraction.
"""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view


# ------------------------------------------------------------ STL operators
def _future(rho, a, b, fn, pad):
    rho = np.asarray(rho, float)
    n = len(rho)
    x = np.concatenate([rho, np.full(b + 1, pad)])
    v = sliding_window_view(x, b - a + 1)              # v[i] = x[i : i + b - a + 1]
    return fn(v[a:a + n], axis=1)


def _past(rho, a, b, fn, pad):
    rho = np.asarray(rho, float)
    n = len(rho)
    x = np.concatenate([np.full(b + 1, pad), rho])
    v = sliding_window_view(x, b - a + 1)              # v[i] = x[i : i + b - a + 1] = rho[i-b-1 .. i-a-1]
    return fn(v[1:n + 1], axis=1)


def always(rho, a, b):
    """G[a,b]: min over [t+a, t+b] (truncated at the end of the trace)."""
    return _future(rho, a, b, np.min, np.inf)


def eventually(rho, a, b):
    """F[a,b]: max over [t+a, t+b] (truncated: pessimistic near the end of the trace)."""
    return _future(rho, a, b, np.max, -np.inf)


def historically(rho, a, b):
    """H[a,b]: min over [t-b, t-a]; uses only the past, so a monitor can evaluate it at t."""
    return _past(rho, a, b, np.min, np.inf)


def once(rho, a, b):
    """O[a,b]: max over [t-b, t-a]."""
    return _past(rho, a, b, np.max, -np.inf)


def and_(*rhos):
    return np.minimum.reduce([np.asarray(r, float) for r in rhos])


def or_(*rhos):
    return np.maximum.reduce([np.asarray(r, float) for r in rhos])


def not_(rho):
    return -np.asarray(rho, float)


def implies(rho_a, rho_b):
    return or_(not_(rho_a), rho_b)


def le(x, c):
    """Predicate x <= c, normalised by |c|."""
    return (c - np.asarray(x, float)) / abs(c)


def ge(x, c):
    """Predicate x >= c, normalised by |c|."""
    return (np.asarray(x, float) - c) / abs(c)


# ------------------------------------------------------------ signals
def rolling_drawdown(r, window):
    """Drawdown of the equity curve from its peak over the last `window` bars (<= 0)."""
    eq = (1 + pd.Series(r).fillna(0.0)).cumprod()
    return (eq / eq.rolling(window, min_periods=1).max() - 1).values


def rolling_vol(r, window, ppy):
    return (pd.Series(r).rolling(window, min_periods=2).std() * np.sqrt(ppy)).values
