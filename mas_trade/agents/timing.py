"""Timing inside the belief: skill that depends on an observable state, estimated walk-forward and shrunk.

Each period the realised calibration slope of the agent's raw signal is b_t = sum(s r) / sum(s^2) over coins, which is the
skill rho of that period. Untimed: the belief is mean(b) x signal. Timed: rho_hat(z) = a + c z with (a, c) from a ridge
regression of b on the state z, c shrunk toward zero, then belief = rho_hat(z_t) x signal. Information before t only.
"""
import numpy as np


def period_slopes(signals, returns):
    """(T, N), (T, N) -> (T,) slope of returns on signals in each period."""
    return (signals * returns).sum(1) / np.maximum((signals ** 2).sum(1), 1e-18)


def untimed_skill(slopes):
    return float(np.mean(slopes)) if len(slopes) else 0.0


def timed_skill(slopes, states, z_now, ridge=5.0):
    """rho_hat at the current state z_now from past (slope, state) pairs; the state coefficient is ridge-shrunk
    (ridge in units of observations of the state's variance)."""
    n = len(slopes)
    if n < 5:
        return untimed_skill(slopes)
    zc = states - states.mean()
    # ridge: `ridge` pseudo-observations of zero dependence, each carrying the state's variance
    c = (zc @ (slopes - slopes.mean())) / (zc @ zc + ridge * max(states.var(), 1e-12) + 1e-18)
    return float(slopes.mean() + c * (z_now - states.mean()))
