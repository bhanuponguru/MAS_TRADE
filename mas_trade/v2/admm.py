"""Decentralised consensus ADMM over the agents' local objectives (edge form, Shi et al. 2014; lecture slide 76).

Agent i owns f_i(x) = -pi_i mu_i'x + (gamma/2M) x'Sx + (m/M) C(x - h) + indicator{A'x = 0}, where C(d) = sum_a
fee|d_a| + kappa_a |d_a|^1.5 is the executor's own cost model. Agents must agree (x_i = x_j on every graph edge);
the agreed point minimises sum_i f_i, i.e.  -sum(pi_i mu_i)'x + gamma/2 x'Sx + m C(x - h)  under neutrality.
S is diagonal (the per-asset variance risk model), which keeps every local step closed form.
"""
import numpy as np


def ring_graph(n):
    adj = np.zeros((n, n), bool)
    for i in range(n):
        adj[i, (i + 1) % n] = adj[(i + 1) % n, i] = True
    np.fill_diagonal(adj, False)
    return adj


def prox_cost(v, t, fee, kappa):
    """argmin_y t (fee|y| + kappa|y|^1.5) + (y - v)^2 / 2, elementwise. With q = sqrt|y|: q^2 + 1.5 t kappa q = |v| - t fee."""
    m = np.maximum(np.abs(v) - t * fee, 0.0)
    b = 1.5 * t * kappa
    q = (-b + np.sqrt(b * b + 4.0 * m)) / 2.0
    return np.sign(v) * q * q


def cost_fn(d, fee, kappa):
    a = np.abs(d)
    return float((fee * a + kappa * a ** 1.5).sum())


def _neutral_solve(Dinv, lin, A):
    """argmin 1/2 x'Dx + lin'x s.t. A'x = 0 for diagonal D, batched over rows: x = Dinv (c - A nu), c = -lin."""
    c = -lin
    AtDA = np.einsum("nj,mn,nk->mjk", A, Dinv, A)
    nu = np.linalg.solve(AtDA, np.einsum("mn,nk->mk", Dinv * c, A)[..., None])[..., 0]
    return Dinv * (c - nu @ A.T)


def _init_state(M, n, warm):
    if warm is None:
        return {k: np.zeros((M, n)) for k in ("X", "P", "Y", "W")}
    return {k: v.copy() for k, v in warm.items()}


def decentralised_admm(mu_pi, S, A, kappa, fee, h, adj, gamma, cost_mult, rho, sigma, iters=300, tol=1e-6,
                       inner=3, warm=None):
    """mu_pi (M, n): pi_i * mu_i; S (n,) diagonal of the holding-period covariance; A (n, 2) neutrality constraints;
    kappa (n,), fee: cost model; h (n,): drifted current portfolio; adj (M, M) bool neighbour graph without self-loops.
    rho: consensus penalty, sigma: penalty of the inner split y = x - h that carries the non-smooth cost.
    Returns (X (M, n) local portfolios, info with iterations, final disagreement, history and the warm-start state)."""
    M, n = mu_pi.shape
    deg = adj.sum(1).astype(float)
    Dinv = 1.0 / ((gamma / M) * S[None, :] + (2 * rho * deg + sigma)[:, None])
    st = _init_state(M, n, warm)
    X, P, Y, W = st["X"], st["P"], st["Y"], st["W"]
    t = cost_mult / M / sigma
    hist = []
    for it in range(iters):
        base = -mu_pi + P - rho * (deg[:, None] * X + adj @ X)       # consensus terms use the previous iterate
        Xn = X
        for _ in range(inner):
            Xn = _neutral_solve(Dinv, base - sigma * (h[None, :] + Y - W), A)
            Y = prox_cost(Xn - h[None, :] + W, t, fee, kappa[None, :])
            W = W + Xn - h[None, :] - Y
        step = float(np.abs(Xn - X).max())            # iterates can agree long before they stop moving
        X = Xn
        P = P + rho * (deg[:, None] * X - adj @ X)
        xbar = X.mean(0)
        dis = float(np.abs(X - xbar).max())
        hist.append(dis)
        if max(dis, step) <= tol * max(float(np.abs(xbar).max()), 1e-8):
            break
    return X, {"iters": it + 1, "disagreement": hist[-1], "hist": np.array(hist), "state": {"X": X, "P": P, "Y": Y, "W": W}}


def central_solve(mu_sum, S, A, kappa, fee, h, gamma, cost_mult, sigma, iters=3000, tol=1e-10):
    """The same global objective on one node (reference for the decentralised result): inner ADMM only."""
    n = len(mu_sum)
    Dinv = (1.0 / (gamma * S + sigma))[None, :]
    y, w = np.zeros(n), np.zeros(n)
    x = np.zeros(n)
    for _ in range(iters):
        x = _neutral_solve(Dinv, (-mu_sum - sigma * (h + y - w))[None, :], A)[0]
        yn = prox_cost(x - h + w, cost_mult / sigma, fee, kappa)
        w = w + x - h - yn
        done = np.abs(yn - y).max() < tol
        y = yn
        if done:
            break
    return x


def objective(x, mu_sum, S, kappa, fee, h, gamma, cost_mult):
    return float(-mu_sum @ x + 0.5 * gamma * (S * x * x).sum() + cost_mult * cost_fn(x - h, fee, kappa))
