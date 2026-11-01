"""Walk-forward backtest of the multi-agent consensus portfolio system.

At every rebalance date t (every H days), using only returns before t:
  1. each agent forecasts mu_i and forms its portfolio w_i = mu_i / sum|mu_i|   (+ long, - short)
  2. trust s_i = forecast probability that agent i is profitable, from its standalone track record
  3. consensus matrix W_ij ~ a_ij * s_j; agents run W-MSR consensus on their portfolios
  4. agents' capital is reallocated through W^T (conserves total), then each agent trades its
     post-consensus portfolio with its own capital until the next rebalance
  With cfg.hierarchical, each agent's capital is split over per-asset subagents G[i, k] (row sums
  = agent capital) and is reallocated between them by a second, subagent-level consensus.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .agents import weights_from_mu
from .capital import apply_pnl, reallocate_capital
from .consensus import (admm_consensus, complete_graph, er_graph, run_consensus,
                        spectral_gap, trust_matrix, wmsr_trust_matrix)
from .forecasting import trust_scores
from .hierarchy import auto_eta, reallocate_budgets, sub_graph, sub_trust


@dataclass
class BacktestResult:
    returns: pd.DataFrame      # daily net returns per strategy over the trading period
    capital: pd.DataFrame      # daily capital controlled by each agent ($)
    trust: pd.DataFrame        # trust score of each agent at each rebalance
    weights: pd.DataFrame      # system weights (long +, short -) at each rebalance
    agent_weights: dict        # rebalance date -> (A x N) post-consensus agent portfolios
    W_hist: dict               # rebalance date -> consensus matrix
    disagreement: np.ndarray   # (n_rebalances x K+1) sum of squared portfolio differences per round
    spectral_gaps: pd.Series
    turnover: dict             # annualised turnover per strategy
    sub_capital: dict = None   # hierarchical only: rebalance date -> (A x N) $ run by each asset subagent
    sub_trust: dict = None     # hierarchical only: rebalance date -> (A x N) subagent trust


def _cost(w_new, w_old, bps):
    return bps / 1e4 * np.abs(w_new - w_old).sum()


def run_backtest(returns, cfg, agents, benchmark=None, eligible=None, funding=None):
    """returns: per-bar simple returns (NaN where an asset does not trade). eligible: optional
    boolean frame, eligible[t] = asset may be traded from bar t (must be known before t, e.g. a
    point-in-time liquidity rank). An asset is also dropped while its lookback window has gaps.
    funding: optional per-bar funding paid by longs and received by shorts (perps)."""
    raw = returns.values
    valid = ~np.isnan(raw)
    R = np.where(valid, raw, 0.0)
    E = np.ones_like(valid) if eligible is None else eligible.reindex_like(returns).fillna(False).values.astype(bool)
    Rn = R if funding is None else R - np.nan_to_num(funding.reindex_like(returns).values)  # P&L per $ long
    dates, tickers = returns.index, list(returns.columns)
    n_days, N = R.shape
    A = len(agents)
    names = [a.name for a in agents]
    frozen = np.array([a.adversarial for a in agents])
    T, H = cfg.lookback, cfg.rebalance_days
    t0 = T + cfg.warmup
    rebal = list(range(T, n_days - 1, H))
    adj = complete_graph(A) if cfg.graph == "complete" else er_graph(A, cfg.er_p, cfg.seed)

    big = n_days * A * N > 5e7                 # ~400 MB in float64: halve it on long intraday panels
    sub_standalone = np.zeros((n_days, A, N), np.float32 if big else float)  # daily reward sign(mu_ik) * r_k of each asset subagent
    standalone = np.zeros((n_days, A))   # daily return of each agent's own (pre-consensus) portfolio
    naive = np.zeros(n_days)
    ew = np.zeros(n_days)
    sys_ret = np.zeros(n_days)
    cap_hist = np.full((n_days, A), np.nan)
    prev_w, prev_naive, prev_ew = np.zeros((A, N)), np.zeros(N), np.zeros(N)
    turn = {n: 0.0 for n in names + ["Naive avg", "EW long-only", "MAS"]}

    c = None
    avail_since = None
    G = side_prev = None
    sub_cap, sub_tr = {}, {}
    x_prev = None
    start_idx = None
    trust_rows, weight_rows, dis_rows, gap_rows = [], [], [], []
    agent_w, W_hist, trade_dates = {}, {}, []

    for t in rebal:
        e = min(t + H, n_days)
        win = R[t - T:t]
        el = E[t] & valid[t - T:t].all(0)        # tradable assets at t, from information before t
        enough = el.sum() >= 4
        if enough and avail_since is None:
            avail_since = t                      # warmup is counted from when assets first became tradable
        trading = avail_since is not None and t >= max(t0, avail_since + cfg.warmup)
        if not enough:
            if trading:
                raise ValueError(f"only {el.sum()} tradable assets at {dates[t]}")
            el = np.zeros(N, bool)               # before trading starts with too few assets: stay flat
        mu = np.zeros((A, N))
        for i, a in enumerate(agents if el.any() else []):  # forecasts see only the tradable assets
            mu[i, el] = a.forecast(win[:, el])
        w = np.vstack([weights_from_mu(m) for m in mu])

        # ---- standalone agents, naive average, equal weight (comparators, with costs)
        w_naive, w_ew = w.mean(0), el / max(el.sum(), 1)
        standalone[t:e] = Rn[t:e] @ w.T
        sub_standalone[t:e] = np.sign(w)[None] * Rn[t:e, None, :]
        naive[t:e], ew[t:e] = Rn[t:e] @ w_naive, Rn[t:e] @ w_ew
        standalone[t] -= np.array([_cost(w[i], prev_w[i], cfg.cost_bps) for i in range(A)])
        naive[t] -= _cost(w_naive, prev_naive, cfg.cost_bps)
        ew[t] -= _cost(w_ew, prev_ew, cfg.cost_bps)
        if trading:
            for i, n in enumerate(names):
                turn[n] += np.abs(w[i] - prev_w[i]).sum()
            turn["Naive avg"] += np.abs(w_naive - prev_naive).sum()
            turn["EW long-only"] += np.abs(w_ew - prev_ew).sum()
        prev_w, prev_naive, prev_ew = w, w_naive, w_ew

        # ---- trust from standalone track record strictly before t (no lookahead)
        hist = standalone[max(T, t - cfg.trust_window):t]
        s = trust_scores(hist, H, cfg.trust_halflife, cfg.trust_power)

        if not trading:
            continue

        # ---- consensus on portfolios
        W = trust_matrix(adj, s)
        if cfg.mode == "admm":
            Sig = np.cov(win[:, el].T)
            Sig = Sig / np.mean(np.diag(Sig)) + 1e-3 * np.eye(el.sum())
            xe, dis = admm_consensus(w[:, el], Sig, s, cfg.admm_gamma, cfg.admm_rho, cfg.K)
            x = np.zeros((A, N))
            x[:, el] = xe / np.maximum(np.abs(xe).sum(1, keepdims=True), 1e-12)
            x[frozen] = w[frozen]
        else:
            x, dis = run_consensus(w, W, adj, cfg.K, cfg.F, cfg.pin, frozen)

        # ---- capital: price in this period's P&L, then reallocate through W^T
        eta1 = cfg.eta
        if eta1 == "auto":                       # per-strategy speed from its own standalone risk
            eta1 = auto_eta(hist.var(0), H, cfg.risk_aversion, cfg.cost_bps)
        if cfg.hierarchical:
            side = np.sign(x)
            if G is None:
                c = np.full(A, cfg.init_capital / A)
                G = c[:, None] * np.abs(x) / np.maximum(np.abs(x).sum(1, keepdims=True), 1e-12)
                start_idx, h_prev, total_prev = t, np.zeros(N), cfg.init_capital
            else:
                h_prev = (side_prev * G).sum(0)
                total_prev = G.sum()
            c_new = reallocate_capital(G.sum(1), wmsr_trust_matrix(adj, s, cfg.F_capital), eta1, cfg.c_min)
            S2 = np.full((A, N), 1e-6)
            S2[:, el] = sub_trust(mu[:, el], side[:, el], win[:, el],
                                  sub_standalone[max(T, t - cfg.trust_window):t][:, :, el],
                                  H, cfg.trust_halflife, cfg.trust_power)
            adj2 = sub_graph(win[:, el], cfg.sub_graph, cfg.corr_threshold)
            eta2 = cfg.eta_sub
            if eta2 == "auto":
                eta2 = np.ones(N)
                eta2[el] = auto_eta(win[:, el].var(0), H, cfg.risk_aversion, cfg.cost_bps)
            G = reallocate_budgets(G, c_new, S2, adj2, eta2, cfg.g_min, cfg.F_sub, frozen, x, el)
            sub_cap[dates[t]], sub_tr[dates[t]] = G.copy(), S2
            h = (side * G).sum(0)                # $ position per stock (negative = short)
            cost = cfg.cost_bps / 1e4 * np.abs(h - h_prev).sum()
            total_at_rebalance = G.sum()         # pre-cost, so sum|h| / total <= 1
            G = G * (1 - cost / total_at_rebalance)
            turn["MAS"] += np.abs(h - h_prev).sum() / total_prev
            side_prev = side

            fee = cfg.short_fee_bps / 1e4 / cfg.periods_per_year * (side < 0)
            for d in range(t, e):
                G = G * (1.0 + side * Rn[d][None, :] - fee)
                cap_hist[d] = G.sum(1)
                prev_total = total_prev if d == t else cap_hist[d - 1].sum()
                sys_ret[d] = cap_hist[d].sum() / prev_total - 1.0
            sys_ret[t] = cap_hist[t].sum() / total_prev - 1.0  # day-t return includes the trading cost
        else:
            if c is None:
                c = np.full(A, cfg.init_capital / A)
                start_idx, h_prev, total_prev = t, np.zeros(N), cfg.init_capital
            else:
                h_prev = x_prev.T @ c            # $ positions held at end of previous period
                total_prev = c.sum()
            c = reallocate_capital(c, wmsr_trust_matrix(adj, s, cfg.F_capital), eta1, cfg.c_min)
            h = x.T @ c                          # $ position per stock (negative = short)
            cost = cfg.cost_bps / 1e4 * np.abs(h - h_prev).sum()
            total_at_rebalance = c.sum()         # pre-cost, so sum|h| / total <= 1
            c = c * (1 - cost / total_at_rebalance)
            turn["MAS"] += np.abs(h - h_prev).sum() / total_prev
            x_prev = x

            short_fee = cfg.short_fee_bps / 1e4 / cfg.periods_per_year * np.clip(-x, 0, None).sum(1)
            for d in range(t, e):
                c = apply_pnl(c, x @ Rn[d] - short_fee)
                cap_hist[d] = c
                prev_total = total_prev if d == t else cap_hist[d - 1].sum()
                sys_ret[d] = cap_hist[d].sum() / prev_total - 1.0
            sys_ret[t] = cap_hist[t].sum() / total_prev - 1.0  # day-t return includes the trading cost

        trade_dates.append(dates[t])
        trust_rows.append(s / s.sum())
        weight_rows.append(h / total_at_rebalance)
        dis_rows.append(dis)
        gap_rows.append(spectral_gap(W))
        agent_w[dates[t]], W_hist[dates[t]] = x, W

    idx = dates[start_idx:]
    out = pd.DataFrame(
        {"MAS": sys_ret[start_idx:], "Naive avg": naive[start_idx:], "EW long-only": ew[start_idx:],
         **{n: standalone[start_idx:, i] for i, n in enumerate(names)}}, index=idx)
    if benchmark is not None:
        out.insert(0, benchmark.name, benchmark.reindex(idx).values)
    years = len(idx) / cfg.periods_per_year
    return BacktestResult(
        returns=out,
        capital=pd.DataFrame(cap_hist[start_idx:], index=idx, columns=names),
        trust=pd.DataFrame(trust_rows, index=trade_dates, columns=names),
        weights=pd.DataFrame(weight_rows, index=trade_dates, columns=tickers),
        agent_weights=agent_w, W_hist=W_hist,
        disagreement=np.array(dis_rows),
        spectral_gaps=pd.Series(gap_rows, index=trade_dates),
        turnover={k: v / years for k, v in turn.items()},
        sub_capital=sub_cap if cfg.hierarchical else None,
        sub_trust=sub_tr if cfg.hierarchical else None,
    )
