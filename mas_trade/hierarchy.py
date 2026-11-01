"""Level 2 of the hierarchy: inside each strategy, one subagent per asset runs part of the
strategy's capital. G[i, k] = $ run by subagent (strategy i, asset k); row sums are the strategy
capitals c_i, so level 1 is always the sum of level 2."""
import numpy as np

from .capital import reallocate_capital
from .consensus import complete_graph, wmsr_trust_matrix
from .forecasting import prob_positive, trust_scores


def sub_graph(win, kind="complete", tau=0.3):
    """Communication graph between the asset subagents of one strategy (self-loops included)."""
    N = win.shape[1]
    if kind == "complete":
        return complete_graph(N)
    corr = np.nan_to_num(np.corrcoef(win.T))
    return ((np.abs(corr) >= tau) | np.eye(N, dtype=bool)).astype(float)


def auto_eta(var, H, gamma, cost_bps):
    """Risk- and cost-aware reallocation speed, one per agent (strategy or asset subagent).
    Minimising  gamma var H/2 (g - target)^2 + lam/2 (g - g_prev)^2  gives
    eta = a / (a + lam),  a = gamma var H  (risk of being off target; var = daily variance of
    what the agent earns), lam = cost_bps/1e4 * n  (quadratic stand-in for the linear cost at a
    typical move of 1/n of the capital being split among n agents)."""
    a = gamma * np.asarray(var) * H
    den = a + cost_bps / 1e4 * len(a)
    return np.where(den > 0, a / np.where(den > 0, den, 1.0), 1.0)  # no risk and no cost: nothing to wait for


def sub_trust(mu, side, win, sub_hist, H, halflife, power=1.0):
    """Forecast reward of every subagent -> trust s_ik (M x N), the product of
      p_fore  = Phi(side * mu * sqrt(H) / sigma_k)  : the current bet on asset k pays off
      p_track = Phi(m sqrt(H) / sd)                 : the subagent's own past P&L sign(mu)*r_k was profitable
    mu: (M x N) forecasts, side: (M x N) +-1 position side, win: (T x N) returns, sub_hist: (T' x M x N)."""
    M, N = mu.shape
    p_fore = prob_positive(side * mu, win.std(0)[None, :], H)
    p_track = trust_scores(sub_hist.reshape(len(sub_hist), M * N), H, halflife, 1.0).reshape(M, N)
    return np.maximum(p_fore * p_track, 1e-6) ** power


def reallocate_budgets(G, c_new, S, adj2, eta, g_min, F_sub=0, frozen=None, x=None, el=None):
    """Pass the level-1 capital change down (row i of G is rescaled to sum to c'_i), then inside
    each strategy move capital between its subagents: g <- (1-eta) g + eta W^T g with
    W_kl ~ a_kl S_il. Row sums stay equal to c_new. Frozen (adversarial) strategies skip level 2
    and spread their capital as |x_i|.
    el: boolean mask of tradable assets. Only those subagents exist; adj2 is their (n_el x n_el)
    graph and a vector eta is the full-length one. Capital of an asset that stopped being
    tradable is passed on to the others."""
    G = np.array(G, dtype=float)
    el = np.ones(G.shape[1], bool) if el is None else el
    eta_el = eta[el] if np.ndim(eta) else eta
    for i in range(len(G)):
        if frozen is not None and frozen[i]:
            G[i] = c_new[i] * np.abs(x[i]) / max(np.abs(x[i]).sum(), 1e-12)
            continue
        g = G[i, el]
        g = g * (c_new[i] / g.sum()) if g.sum() > 1e-12 else np.full(len(g), c_new[i] / len(g))
        G[i] = 0.0
        G[i, el] = reallocate_capital(g, wmsr_trust_matrix(adj2, S[i, el], F_sub), eta_el, g_min)
    return G
