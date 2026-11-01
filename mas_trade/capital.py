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
    A floor of c_min * total keeps every agent alive.

    eta may be a vector (one speed per agent). Then the update is the solution of
    min sum_k [a_k/2 (g_k - target_k)^2 + lam/2 (g_k - c_k)^2]  s.t. sum g = sum c, with
    eta_k = a_k/(a_k+lam); the budget multiplier adds a shift proportional to (1 - eta_k)."""
    total = c.sum()
    new = (1 - eta) * c + eta * (W.T @ c)
    if np.ndim(eta) and (1 - eta).sum() > 1e-12:  # all eta = 1: new = W^T c, already conserves the total
        new += (1 - eta) * (total - new.sum()) / (1 - eta).sum()
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
