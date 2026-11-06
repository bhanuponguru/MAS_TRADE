"""Primitives for the cell ADMM (Level 2): the separable trading-cost prox and the neutral quadratic solve.

The cost of trading d in one coin is C(d) = fee |d| + kappa |d|^1.5 (see costs.py). It is separable per coin, so
each cell's update is a 1-D prox that has a closed form.
"""
import numpy as np


def prox_cost(v, t, fee, kappa):
    """argmin_y t (fee|y| + kappa|y|^1.5) + (y - v)^2 / 2, elementwise. With q = sqrt|y|: q^2 + 1.5 t kappa q = |v| - t fee."""
    m = np.maximum(np.abs(v) - t * fee, 0.0)
    b = 1.5 * t * kappa
    q = (-b + np.sqrt(b * b + 4.0 * m)) / 2.0
    return np.sign(v) * q * q


def cost_fn(d, fee, kappa):
    a = np.abs(d)
    return float((fee * a + kappa * a ** 1.5).sum())


def neutral_solve(Dinv, lin, A):
    """argmin 1/2 x'Dx + lin'x s.t. A'x = 0 for diagonal D, batched over rows: x = Dinv (c - A nu), c = -lin."""
    c = -lin
    AtDA = np.einsum("nj,mn,nk->mjk", A, Dinv, A)
    nu = np.linalg.solve(AtDA, np.einsum("mn,nk->mk", Dinv * c, A)[..., None])[..., 0]
    return Dinv * (c - nu @ A.T)
