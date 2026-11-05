"""Safety layer: Signal Temporal Logic (STL) monitor + supervisory shield.

Quantitative STL semantics on discrete traces (robustness rho > 0 <=> spec satisfied, |rho| = margin):
  predicate  x <= c  ->  rho = c - x            x >= c  ->  rho = x - c
  not phi -> -rho     phi and psi -> min     phi or psi -> max     phi -> psi  ==  (not phi) or psi
  G[a,b] phi (always)      rho(t) = min rho_phi(t'),  t' in [t+a, t+b]
  F[a,b] phi (eventually)  rho(t) = max rho_phi(t'),  t' in [t+a, t+b]
  H[a,b] / O[a,b]          past-time versions over t' in [t-b, t-a] (computable online at t)
Finite traces are truncated: a window running past the end of the trace uses only what exists.

Portfolio specifications (thresholds in Config.safety_*), each normalised by its threshold so that
robustness values of different specs are comparable (rho = 0.5 means 50% of the limit left):
  phi_dd    G (rolling drawdown >= -max_dd)                     drawdown over the last dd_window bars
  phi_vol   G (rolling vol <= max_vol)                           annualised, over vol_window bars
  phi_rec   G (vol > max_vol -> F[0,R] vol <= max_vol)           a vol breach must end within R bars
  phi_conc  G (max_k |w_k| <= max_weight  and  sum_k |w_k| <= 1) at every rebalance
  phi_cons  G (consensus disagreement after K rounds <= max_disagreement)   (monitor only)

The supervisor (shield) runs at each rebalance t on information before t only. It checks the
proposed system portfolio against the specs it can act on and scales it toward cash:
  * per-stock cap:  m_k = min(1, max_weight / |w_k|)                      -> phi_conc holds by construction
  * ex-ante vol:    lam_vol = min(1, max_vol / sigma_ex),  sigma_ex^2 = w' Sigma w * ppy  (Sigma from the lookback)
  * drawdown:       lam_dd falls linearly from 1 to min_scale as the drawdown margin rho_dd goes
                    from buffer to 0 (de-risk before the limit, not after it)
  scale_k = min(lam_vol, lam_dd) * m_k ; the remainder sits in cash (earns 0).
With cfg.safety_daily (decision 0028, on by default) the backtest also calls the shield every bar
between rebalances and only ever lowers exposure until the next rebalance. The scale applies to every
agent alike (decision 0029: cutting by risk contribution spared a compromised agent, so it was removed).
phi_cons is only defined for mode="wmsr" (in ADMM mode the logged disagreement is a primal residual).
"""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view


# ------------------------------------------------------------ STL operators
def _future(rho, a, b, fn, pad):
    rho = np.asarray(rho, float)
    n = len(rho)
    x = np.concatenate([rho, np.full(b + 1, pad)])
    v = sliding_window_view(x, b - a + 1)              # v[i] = x[i : i + b - a + 1]
    return fn(v[a:a + n], axis=1)


def _past(rho, a, b, fn, pad):
    rho = np.asarray(rho, float)
    n = len(rho)
    x = np.concatenate([np.full(b + 1, pad), rho])
    v = sliding_window_view(x, b - a + 1)              # v[i] = x[i : i + b - a + 1] = rho[i-b-1 .. i-a-1]
    return fn(v[1:n + 1], axis=1)


def always(rho, a, b):
    """G[a,b]: min over [t+a, t+b] (truncated at the end of the trace)."""
    return _future(rho, a, b, np.min, np.inf)


def eventually(rho, a, b):
    """F[a,b]: max over [t+a, t+b] (truncated: pessimistic near the end of the trace)."""
    return _future(rho, a, b, np.max, -np.inf)


def historically(rho, a, b):
    """H[a,b]: min over [t-b, t-a]; uses only the past, so a monitor can evaluate it at t."""
    return _past(rho, a, b, np.min, np.inf)


def once(rho, a, b):
    """O[a,b]: max over [t-b, t-a]."""
    return _past(rho, a, b, np.max, -np.inf)


def and_(*rhos):
    return np.minimum.reduce([np.asarray(r, float) for r in rhos])


def or_(*rhos):
    return np.maximum.reduce([np.asarray(r, float) for r in rhos])


def not_(rho):
    return -np.asarray(rho, float)


def implies(rho_a, rho_b):
    return or_(not_(rho_a), rho_b)


def le(x, c):
    """Predicate x <= c, normalised by |c|."""
    return (c - np.asarray(x, float)) / abs(c)


def ge(x, c):
    """Predicate x >= c, normalised by |c|."""
    return (np.asarray(x, float) - c) / abs(c)


# ------------------------------------------------------------ signals
def rolling_drawdown(r, window):
    """Drawdown of the equity curve from its peak over the last `window` bars (<= 0)."""
    eq = (1 + pd.Series(r).fillna(0.0)).cumprod()
    return (eq / eq.rolling(window, min_periods=1).max() - 1).values


def rolling_vol(r, window, ppy):
    return (pd.Series(r).rolling(window, min_periods=2).std() * np.sqrt(ppy)).values


# ------------------------------------------------------------ offline evaluation
SPECS = ["phi_dd", "phi_vol", "phi_rec", "phi_conc", "phi_cons"]


def evaluate(returns, cfg, weights=None, disagreement=None):
    """Robustness traces of the portfolio specs on a realised run.

    returns: per-bar system returns (Series); weights: system weights per rebalance (DataFrame);
    disagreement: final-round disagreement per rebalance (Series). Returns (traces, summary):
    traces[name] is the robustness signal of the spec's body (the G is the min over it), summary
    gives per spec: robustness of the whole spec (min), share of time violated, number of
    violation episodes and the longest one (in bars or rebalances)."""
    r = returns.fillna(0.0)
    vol = rolling_vol(r.values, cfg.safety_vol_window, cfg.periods_per_year)
    rho_vol = le(np.nan_to_num(vol, nan=0.0), cfg.safety_max_vol)
    traces = {
        "phi_dd": pd.Series(ge(rolling_drawdown(r.values, cfg.safety_dd_window), -cfg.safety_max_dd), index=r.index),
        "phi_vol": pd.Series(rho_vol, index=r.index),
        # vol > max -> F[0,R] vol <= max   ==  F[0,R] (vol <= max), since the window includes t
        "phi_rec": pd.Series(implies(not_(rho_vol), eventually(rho_vol, 0, cfg.safety_recover)), index=r.index),
    }
    if weights is not None:
        w = weights.abs()
        tol = 1e-9                                       # a weight capped exactly at the limit is not a breach
        traces["phi_conc"] = pd.Series(and_(le(w.max(axis=1) - tol, cfg.safety_max_weight), le(w.sum(axis=1) - tol, 1.0)),
                                       index=weights.index)
    if disagreement is not None and cfg.mode == "wmsr":
        traces["phi_cons"] = pd.Series(le(disagreement, cfg.safety_max_disagreement), index=disagreement.index)
    rows = {}
    for k, tr in traces.items():
        bad = (tr.values < 0).astype(int)
        starts = np.flatnonzero(np.diff(np.concatenate([[0], bad])) == 1)
        ends = np.flatnonzero(np.diff(np.concatenate([bad, [0]])) == -1)
        rows[k] = {"robustness": float(tr.min()), "violated": float(bad.mean()),
                   "episodes": len(starts), "longest": int((ends - starts + 1).max()) if len(starts) else 0}
    return pd.DataFrame(traces), pd.DataFrame(rows).T


# ------------------------------------------------------------ online supervisor
def supervise(w, win, el, past_ret, cfg):
    """Shield at a check date d: a rebalance, or any bar in between with cfg.safety_daily (decision 0028).

    w: (N,) proposed system weights (fractions of total capital); win: (T x N) returns before d;
    el: tradable mask; past_ret: system returns before d since trading started.
    Returns (scale (N,), info). scale multiplies the exposure to each stock for every agent alike
    (decision 0029); the rest sits in cash. cfg.safety False -> scale is all ones and info is the
    monitor reading only."""
    N = len(w)
    ppy = cfg.periods_per_year
    ne = int(el.sum())
    Sig = np.atleast_2d(np.cov(win[:, el].T)) if ne >= 2 else np.zeros((ne, ne))

    def vol(v):
        return float(np.sqrt(max(v[el] @ Sig @ v[el], 0.0) * ppy)) if ne else 0.0

    def conc(v):
        return float(min(le(np.abs(v).max() if N else 0.0, cfg.safety_max_weight), le(np.abs(v).sum(), 1.0 + 1e-9)))

    dd = rolling_drawdown(past_ret, cfg.safety_dd_window)[-1] if len(past_ret) else 0.0
    rho_dd = float(ge(dd, -cfg.safety_max_dd))
    vol_pre = vol(w)
    info = {"drawdown": dd, "rho_dd": rho_dd, "vol_ex_ante": vol_pre, "rho_vol": float(le(vol_pre, cfg.safety_max_vol)),
            "rho_conc": conc(w)}
    scale = np.ones(N)
    if not cfg.safety:
        info.update(lam=1.0, intervened=False, rho_vol_post=info["rho_vol"], rho_conc_post=info["rho_conc"])
        return scale, info

    aw = np.abs(w)
    m = np.where(aw > cfg.safety_max_weight, cfg.safety_max_weight / np.maximum(aw, 1e-300), 1.0)  # per-stock cap
    v = vol(w * m)
    lam_vol = min(1.0, cfg.safety_max_vol / v) if v > 0 else 1.0
    lam_dd = float(np.clip(cfg.safety_min_scale + (1 - cfg.safety_min_scale) * rho_dd / cfg.safety_buffer,
                           cfg.safety_min_scale, 1.0))
    lam = min(lam_vol, lam_dd)
    scale = lam * m
    w_post = w * scale
    info.update(lam=lam, lam_vol=lam_vol, lam_dd=lam_dd, intervened=bool((scale < 1 - 1e-12).any()),
                rho_vol_post=float(le(vol(w_post), cfg.safety_max_vol)), rho_conc_post=conc(w_post))
    return scale, info
