"""Who pays for what when agents' trades are netted: cost allocation and the accounting invariants."""
import numpy as np


def allocate_cost(prev, new, fee, kappa):
    """Per-agent share of the trading cost of the NET trade. prev, new: (M, N) cell positions before and after.
    The cost of coin a is C_a(D_a), D_a = sum_i (new - prev)_ia; it is charged to the agents whose trade has the same
    sign as D_a, pro rata to the size of their trade. Agents trading against the net cross internally and pay
    nothing. Returns (per-agent cost (M,), total cost)."""
    d = new - prev
    D = d.sum(0)
    c = fee * np.abs(D) + kappa * np.abs(D) ** 1.5
    w = np.abs(d) * ((np.sign(d) == np.sign(D)) & (d != 0))
    ws = w.sum(0)
    share = np.divide(w, ws, out=np.zeros_like(w), where=ws > 0)
    return (share * c).sum(1), float(c.sum())
