"""Consensus machinery from the MAS course: trust matrix, W-MSR, Laplacian, ADMM, robustness.

Conventions: adj is an (A x A) 0/1 matrix WITH self-loops on the diagonal; x is (A x N):
row i = agent i's portfolio over N stocks.
"""
from itertools import product

import numpy as np


# ----------------------------------------------------------------- graphs
def complete_graph(n):
    return np.ones((n, n))


def is_connected(adj):
    n = len(adj)
    seen, stack = {0}, [0]
    while stack:
        for j in np.flatnonzero(adj[stack.pop()]):
            if j not in seen:
                seen.add(j)
                stack.append(j)
    return len(seen) == n


def er_graph(n, p, seed=0):
    """Erdos-Renyi G(n,p): each edge present with prob p (resampled until connected)."""
    rng = np.random.default_rng(seed)
    while True:
        upper = np.triu(rng.random((n, n)) <= p, 1)
        adj = (upper | upper.T).astype(float)
        np.fill_diagonal(adj, 1.0)
        if is_connected(adj):
            return adj


def laplacian(adj):
    a = adj - np.diag(np.diag(adj))
    return np.diag(a.sum(1)) - a


def laplacian_step(x, adj, eps):
    """x[k+1] = (I - eps L) x[k]; converges iff 0 < eps < 2 / lambda_max(L)."""
    return x - eps * laplacian(adj) @ x


def disagreement(x, adj):
    """x^T L x summed over stocks = sum over edges of squared differences."""
    d = ((x[:, None, :] - x[None, :, :]) ** 2).sum(2)
    return 0.5 * float((adj * d).sum())


# ----------------------------------------------------------- trust matrix
def trust_matrix(adj, s):
    """W_ij = a_ij s_j / sum_l a_il s_l  (row-stochastic: listen more to high-trust agents)."""
    W = adj * np.asarray(s)[None, :]
    return W / W.sum(1, keepdims=True)


def wmsr_trust_matrix(adj, s, F):
    """Trust matrix where each agent first drops the F most- and F least-trusted neighbours
    relative to itself (W-MSR on the scalar trust values). Rows still sum to 1, so W.T
    conserves total capital."""
    if F == 0:
        return trust_matrix(adj, s)
    A = len(adj)
    keep = adj.astype(bool).copy()
    for i in range(A):
        nb = [j for j in np.flatnonzero(adj[i]) if j != i]
        hi = sorted((j for j in nb if s[j] > s[i]), key=lambda j: -s[j])[:F]
        lo = sorted((j for j in nb if s[j] < s[i]), key=lambda j: s[j])[:F]
        keep[i, hi + lo] = False
    return trust_matrix(keep.astype(float), s)


def spectral_gap(W):
    """1 - |lambda_2(W)|: larger = faster consensus."""
    ev = np.sort(np.abs(np.linalg.eigvals(W)))[::-1]
    return float(1.0 - ev[1]) if len(ev) > 1 else 1.0


# ------------------------------------------------------------------ W-MSR
def wmsr_step(x, W, adj, F, frozen=None):
    """One W-MSR round, per stock: each agent discards the F largest neighbour values above its
    own and the F smallest below its own, then takes the W-weighted average of what remains
    (own value included). F=0 gives ordinary consensus x <- W x. Frozen agents (adversaries)
    ignore the protocol and keep broadcasting their value."""
    A, N = x.shape
    new = x.copy()
    cols = np.arange(N)
    for i in range(A):
        if frozen is not None and frozen[i]:
            continue
        nb = np.array([j for j in np.flatnonzero(adj[i]) if j != i], dtype=int)
        if len(nb) == 0:
            continue
        V, own = x[nb], x[i]
        keep = np.ones(V.shape, bool)
        if F > 0:
            Fm = min(F, len(nb))
            Vg = np.where(V > own, V, -np.inf)
            for r in np.argsort(-Vg, axis=0)[:Fm]:
                sel = Vg[r, cols] > -np.inf
                keep[r[sel], cols[sel]] = False
            Vl = np.where(V < own, V, np.inf)
            for r in np.argsort(Vl, axis=0)[:Fm]:
                sel = Vl[r, cols] < np.inf
                keep[r[sel], cols[sel]] = False
        wts = W[i, nb][:, None] * keep
        new[i] = (W[i, i] * own + (wts * V).sum(0)) / (W[i, i] + wts.sum(0))
    return new


def _gross_normalize(x):
    g = np.abs(x).sum(1, keepdims=True)
    return np.where(g > 0, x / np.where(g > 0, g, 1.0), x)


def run_consensus(w0, W, adj, K, F, b, frozen=None, normalize=True):
    """K rounds of x <- (1-b) * WMSR(x) + b * w0 (pinning keeps each agent anchored to its own
    strategy, cf. leader-follower pinning). Returns final x and the disagreement history."""
    x = w0.copy()
    hist = [disagreement(x, adj)]
    for _ in range(K):
        y = (1 - b) * wmsr_step(x, W, adj, F, frozen) + b * w0
        if frozen is not None:
            y[frozen] = w0[frozen]
        if normalize:
            y = _gross_normalize(y)
        x = y
        hist.append(disagreement(x, adj))
    return x, np.array(hist)


# ------------------------------------------------------------------- ADMM
def admm_consensus(w0, Sigma, s, gamma, rho, iters):
    """Scaled-form consensus ADMM (lecture slide 73). Agent i's local cost is
    f_i(x) = -w0_i^T x + gamma/2 x^T Sigma x, with a trust-weighted consensus variable z.
    Sigma should be scaled to unit average variance. Returns local x (A x N) and history."""
    A, N = w0.shape
    M = np.linalg.inv(gamma * Sigma + rho * np.eye(N))
    x, u, z = np.zeros_like(w0), np.zeros_like(w0), np.zeros(N)
    s = np.asarray(s, float)
    hist = []
    for _ in range(iters):
        x = (w0 + rho * (z - u)) @ M          # x_i = argmin f_i + rho/2 ||x - z + u_i||^2
        z = (s[:, None] * (x + u)).sum(0) / s.sum()
        u = u + x - z
        hist.append(float(((x - z) ** 2).sum()))
    return x, np.array([hist[0]] + hist)


# ------------------------------------------------------------- robustness
def is_r_s_robust(adj, r, s=1):
    """Brute-force (r,s)-robustness (Resilient Consensus lecture). For every pair of disjoint
    nonempty subsets S1,S2 at least one must hold: all of S1 is r-reachable, all of S2 is, or
    together >= s nodes are. (F+1,F+1)-robust <=> W-MSR resilient to F total adversaries.
    Exponential: only for small graphs."""
    a = adj - np.diag(np.diag(adj))
    n = len(a)
    for assign in product((0, 1, 2), repeat=n):
        assign = np.array(assign)
        S1, S2 = assign == 1, assign == 2
        if not S1.any() or not S2.any():
            continue
        ok = True
        counts = []
        for S in (S1, S2):
            outside = a[:, ~S].sum(1)
            counts.append(int(((outside >= r) & S).sum()))
        if not (counts[0] == S1.sum() or counts[1] == S2.sum() or counts[0] + counts[1] >= s):
            return False
    return True
