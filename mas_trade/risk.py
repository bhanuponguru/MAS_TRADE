"""Risk helpers: shrinkage covariance, betas to BTC, neutrality projection."""
import numpy as np


def ledoit_wolf(X):
    """Ledoit-Wolf (2004) shrinkage of the sample covariance of X (T x p) toward m*I."""
    T, p = X.shape
    X = X - X.mean(0)
    S = X.T @ X / T
    m = np.trace(S) / p
    d2 = ((S - m * np.eye(p)) ** 2).sum() / p
    b2 = min(d2, ((X ** 2).sum(1) ** 2).sum() / T ** 2 / p - (S ** 2).sum() / T / p)
    k = 0.0 if d2 <= 0 else max(b2, 0.0) / d2
    return k * m * np.eye(p) + (1 - k) * S


def betas(R, rb):
    """OLS beta of each column of R (T x N) on the benchmark return rb (T,)."""
    rbc = rb - rb.mean()
    return ((R - R.mean(0)) * rbc[:, None]).sum(0) / max((rbc ** 2).sum(), 1e-12)


def neutralise(w, beta):
    """Project w onto {1'w = 0, beta'w = 0}."""
    A = np.column_stack([np.ones(len(w)), beta])
    return w - A @ np.linalg.lstsq(A, w, rcond=None)[0]
