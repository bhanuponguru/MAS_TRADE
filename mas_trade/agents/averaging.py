"""Model averaging inside an agent: several estimators of the SAME hypothesis are combined into one belief.

Members estimate one quantity (the hypothesis's expected return per coin) with different errors, so averaging them is
estimation fusion. Weights come from a regression of realised returns on the members' beliefs (stacking): its optimum
is the precision weighting, and it is far less noisy than comparing mean squared errors against returns, whose common
noise (the idiosyncratic part of the return) swamps the members' error differences. The weights are made non-negative,
normalised and shrunk toward equal weights.
"""
import numpy as np


def stacking_weights(beliefs, returns, ridge=1e-3, shrink=0.5):
    """beliefs (n, M): members' beliefs over past (period, coin) observations; returns (n,): the realised returns that
    followed. Returns M weights >= 0 summing to 1: (1 - shrink) * normalised non-negative ridge regression + shrink / M."""
    n, M = beliefs.shape
    G = beliefs.T @ beliefs / n
    G = G + ridge * np.trace(G) / M * np.eye(M)
    beta = np.linalg.solve(G, beliefs.T @ returns / n)
    beta = np.maximum(beta, 0.0)
    w = beta / beta.sum() if beta.sum() > 0 else np.full(M, 1.0 / M)
    return (1.0 - shrink) * w + shrink / M


def inverse_mse_weights(beliefs, returns, shrink=0.5):
    """The naive alternative: weights proportional to 1 / MSE of each member against realised returns."""
    mse = ((returns[:, None] - beliefs) ** 2).mean(0)
    w = (1.0 / mse) / (1.0 / mse).sum()
    return (1.0 - shrink) * w + shrink / len(w)


def fuse(beliefs, weights=None, trim=0, bound=None, max_bad_share=0.05):
    """beliefs (M, N) -> (N,). Weighted mean of the members. Two guards against a faulty member:
    bound: beliefs that are non-finite or beyond +-bound are excluded coin by coin (the sanity spec, see
    stl.belief_bound), and a member with more than max_bad_share of its coins violating is excluded altogether (a corrupt
    member is corrupt everywhere, including where its values happen to look plausible);
    trim = k: the k highest and k lowest members of every coin are dropped (a trimmed mean)."""
    M = beliefs.shape[0]
    w = np.full(M, 1.0 / M) if weights is None else np.asarray(weights, float)
    keep = np.ones_like(beliefs, dtype=bool)
    if bound is not None:
        keep &= np.isfinite(beliefs) & (np.abs(beliefs) <= bound)
        keep &= ((~keep).mean(1) <= max_bad_share)[:, None] | np.zeros_like(keep)
    if trim:
        masked = np.where(keep, beliefs, np.nan)
        order = np.argsort(np.where(keep, beliefs, np.inf), axis=0)       # invalid members sort last, never trimmed as "low"
        n_ok = keep.sum(0)
        rank = np.empty_like(order)
        np.put_along_axis(rank, order, np.arange(M)[:, None] * np.ones_like(order), axis=0)
        keep &= (rank >= trim) & (rank < n_ok[None, :] - trim)
        del masked
    ww = w[:, None] * keep
    num = (ww * np.where(keep, beliefs, 0.0)).sum(0)
    den = ww.sum(0)
    return np.divide(num, den, out=np.zeros_like(num), where=den > 0)
