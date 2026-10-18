"""Capital controlled by each agent: earns its own P&L, and is reallocated through W transpose."""
import numpy as np


def apply_pnl(c, r):
    """c_i <- c_i (1 + r_i)."""
    return c * (1.0 + r)


def reallocate_capital(c, W, eta, c_min):
    """c <- (1-eta) c + eta W^T c.

    W is row-stochastic so W^T is column-stochastic: 1^T W^T c = 1^T c, i.e. total capital is
    conserved (same argument as 1^T L = 0 in Consensus Theory). On a complete graph
    W^T c = s * sum(c)/sum(s), so capital drifts toward each agent's forecast trust s.
    A floor of c_min * total keeps every agent alive."""
    total = c.sum()
    new = (1 - eta) * c + eta * (W.T @ c)
    floor = c_min * total
    fixed = np.zeros(len(c), bool)
    for _ in range(len(c)):
        low = (new < floor - 1e-12) & ~fixed
        if not low.any():
            break
        fixed |= low
        new[fixed] = floor
        free = ~fixed
        new[free] *= (total - floor * fixed.sum()) / new[free].sum()
    assert abs(new.sum() - total) <= 1e-8 * total, "capital not conserved"
    return new
