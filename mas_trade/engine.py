"""The engine: agents form beliefs, the joint ADMM turns them into cell positions, accounts earn their own P&L.

Per rebalance bar t (information before t only): tradable coins are those in the point-in-time universe with a full
valid window and enough dollar volume; every agent's belief is mu = IC_hat x sigma_H x z; the cells (agent, coin) are solved
jointly (cells_admm: Kelly stake with neutrality, capacity, margin, gross cap and the cost of the NET trade); the system trades
the net, costs are charged to the accounts that trade with it, and positions then drift bar by bar earning price
returns minus funding. Units: multiples of the initial equity; the impact cost uses a constant AUM (as the legacy executor).
"""
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from . import stl, supervisor
from .agents.base import Ctx
from .attribution import allocate_cost
from .cells_admm import CellProblem, CellSolution, solve_cells
from .graph_admm import adjacency, is_connected, metropolis, solve_cells_graph, solve_cells_resilient, subproblem
from .market import apply_floor, limited_liability
from .risk import betas


@dataclass
class EngineResult:
    dates: object                       # DatetimeIndex of the traded bars
    net: np.ndarray                     # (n,) per-bar net return of the system
    price: np.ndarray                   # (n,) price P&L / equity
    funding: np.ndarray                 # (n,) funding P&L / equity (negative when longs pay)
    cost: np.ndarray                    # (n,) trading cost / equity
    exposure: np.ndarray                # (n,) net beta exposure / equity
    gross: np.ndarray                   # (n,) gross exposure / equity
    account: np.ndarray                 # (n, M) per-bar P&L of each agent's account (absolute units)
    wealth: np.ndarray                  # (K+1, M) wealth at the rebalances (before the floor of the next one)
    rebal: np.ndarray                   # (K,) rebalance bars
    targets: list = field(default_factory=list)   # per rebalance: (coin indices, (M, n_k) positions)
    iters: list = field(default_factory=list)
    unconverged: int = 0
    residuals: list = field(default_factory=list)   # max(primal, dual) residual of every unconverged solve
    sanitized: int = 0                  # coin beliefs zeroed by the sanity spec
    kelly_scales: list = field(default_factory=list)  # per rebalance: the calibration spec's multiplier of each agent's Kelly fraction
    exante: list = field(default_factory=list)        # per rebalance: each agent's ex-ante annual Sharpe at its belief
    agent_gross: list = field(default_factory=list)   # per rebalance: each agent's gross position
    vol_price: list = field(default_factory=list)     # per rebalance: price of the system variance (0 = limit slack)
    sys_vol: list = field(default_factory=list)       # per rebalance: ex-ante annual volatility of the system / equity
    isolated: list = field(default_factory=list)      # per solved rebalance: agents isolated by the detector so far (experiment 021)
    solved: list = field(default_factory=list)        # bars of the rebalances that were solved (iters, sys_vol, isolated align with it)
    solve_dates: list = field(default_factory=list)   # their dates
    rel_res: list = field(default_factory=list)       # relative residual of each solve
    converged: list = field(default_factory=list)
    dd_scale: list = field(default_factory=list)      # multiplier of the volatility target from the drawdown spec (1 = none)
    held: list = field(default_factory=list)          # True when the supervisor held positions (unsafe solve)
    turnover: float = 0.0               # annual sum |trade| / equity
    names: list = field(default_factory=list)


def tradable(P, cfg, t):
    """Tradable coins at rebalance bar t (information before t only): in the point-in-time universe, a full valid history
    window and enough trailing dollar volume. Returns (indices, trailing daily dollar volume of every coin)."""
    bpd = P.bpd
    Tb, adv_b = int(round(cfg.hist_days * bpd)), int(round(cfg.adv_days * bpd))
    adv = np.median(P.V[t - adv_b:t], axis=0) * bpd
    el = P.E[t] & P.valid[t - Tb:t].all(0) & (adv >= cfg.min_adv)
    return np.flatnonzero(el), adv


def run_engine(P, agents, cfg, solver=None, end=None):
    n, N = P.R.shape
    n = n if end is None else end
    bpd, H = P.bpd, cfg.rebal_bars
    Tb = int(round(cfg.hist_days * bpd))
    cov_b, beta_b = (int(round(d * bpd)) for d in (cfg.cov_days, cfg.beta_days))
    burn = int(round(cfg.burn_days * bpd))
    M = len(agents)
    rebal = np.arange(Tb, n - 1, H)
    W = np.full(M, 1.0 / M)
    held = np.zeros((M, N))
    out = {k: np.zeros(n) for k in ("net", "price", "funding", "cost", "exposure", "gross")}
    account = np.zeros((n, M))
    wealth = [W.copy()]
    res = EngineResult(None, *[None] * 6, account, None, rebal, names=[a.name for a in agents])
    first = None
    turn = 0.0
    prev_t = None
    prev_bel = None                                             # (coin indices, (M, n) beliefs) of the previous decision
    lam_prev = 0.0                                              # last price of the system variance
    beta_last = np.ones(N)                                      # last known beta of every coin (for coins held but untradable)
    hist_abs = [deque(maxlen=cfg.calibration_window) for _ in agents]    # past non-zero |beliefs|: the sanity spec
    calib = [deque(maxlen=cfg.calibration_window) for _ in agents]       # (belief, realised return) pairs: the calibration spec
    if cfg.consensus not in ("hub", "graph"):
        raise ValueError(f"unknown consensus {cfg.consensus!r}")
    names = [a.name for a in agents]
    faulty_all = [names.index(nm) for nm in cfg.faulty]
    faulty = list(faulty_all)                                   # the agents misbehaving at the current rebalance
    Ag = adjacency(cfg.topology, M, seed=cfg.topology_seed) if cfg.consensus == "graph" else None
    quarantine = set()                                          # agents isolated by the detector: out for the rest of the run
    if cfg.attack_kind == "noise":
        attack = lambda v, it: v + np.random.default_rng(it + 7919 * len(res.iters)).normal(0.0, cfg.attack, v.shape)
    else:
        attack = lambda v, it: v + cfg.attack
    graph_kw = dict(rounds=cfg.gossip_rounds, link_fail=cfg.link_fail, attack=attack)
    hold = cfg.safety in ("hold", "both")
    derisk = cfg.safety in ("derisk", "both")
    if cfg.safety not in ("off", "hold", "derisk", "both"):
        raise ValueError(f"unknown safety mode {cfg.safety!r}")

    def solve(prob, out_):
        """Solve with the agents that are not out (decision 0042 + experiment 021). Out agents hold nothing. In graph mode the
        others use the graph without the out nodes; faulty agents stay on the graph (holding nothing) and send false values.
        In hub mode faulty agents are simply out (a hub has no messages to corrupt)."""
        out_ = out_ | quarantine
        keep = np.array([i for i in range(M) if i not in out_ and (cfg.consensus == "graph" or i not in faulty)])
        sub = prob if len(keep) == M else subproblem(prob, keep)
        if cfg.consensus == "hub":
            sol = solve_cells(sub, **(solver or {}))
        else:
            A = Ag[np.ix_(keep, keep)]
            if not is_connected(A):
                raise RuntimeError(f"the graph without agents {sorted(out_)} is disconnected")
            fk = [q for q, i in enumerate(keep) if i in faulty]
            if cfg.detect:
                sol = solve_cells_resilient(sub, A, faulty=fk, detect=cfg.detect, seed=k, **graph_kw, **(solver or {}))
                quarantine.update(int(keep[q]) for q in sol.state["isolated"])
            else:
                sol = solve_cells_graph(sub, metropolis(A), faulty=fk, seed=k, **graph_kw, **(solver or {}))
        if len(keep) == M:
            return sol
        x = np.zeros((M, prob.mu.shape[1]))
        x[keep] = sol.x
        return CellSolution(x=x, X=x.sum(0), prices=sol.prices, iters=sol.iters, converged=sol.converged,
                            primal_res=sol.primal_res, dual_res=sol.dual_res, state=sol.state)
    for k, t in enumerate(rebal):
        e = rebal[k + 1] if k + 1 < len(rebal) else n
        if prev_t is not None:                                  # the period that just ended: calibrate every agent
            ok = P.valid[prev_t:t].all(0)
            fwd = np.where(ok, np.prod(1.0 + P.R[prev_t:t], axis=0) - 1.0, np.nan)
            for ag in agents:
                ag.observe({P.tickers[j]: fwd[j] for j in range(N)})
            if prev_bel is not None:
                ip, Bp = prev_bel
                for i in range(M):
                    keep = (Bp[i] != 0) & np.isfinite(fwd[ip])
                    calib[i].append((Bp[i][keep], fwd[ip][keep]))
        prev_t = t
        ii, adv = tradable(P, cfg, t)
        if len(ii) < cfg.min_assets:
            trading = False
        else:
            first = t if first is None else first
            trading = t >= first + burn
        R_win = P.R[t - Tb:t]
        if len(ii) >= cfg.min_assets:
            sig_bar = R_win[-cov_b:, ii].std(0)
            ctx = Ctx(R_win[:, ii], P.F[t - Tb:t][:, ii], P.V[t - Tb:t][:, ii], P.btc[t - Tb:t],
                      [P.tickers[j] for j in ii], bpd, sig_bar * np.sqrt(H))
            beliefs = np.stack([ag.belief(ctx) for ag in agents])
            for i in range(M):                                  # sanity spec on the volatility-standardised belief mu / sigma_H
                zb = beliefs[i] / ctx.sigma_h
                h = np.concatenate(list(hist_abs[i])) if hist_abs[i] else np.zeros(0)
                if len(h) >= 200:
                    zb, bad = stl.sanitize_belief(zb, stl.belief_bound(h, cfg.belief_bound_k))
                    beliefs[i] = zb * ctx.sigma_h
                    res.sanitized += int(round(bad * len(ii)))
                nz = np.abs(zb)[zb != 0]
                if len(nz):
                    hist_abs[i].append(nz)
            prev_bel = (ii, beliefs.copy())
        else:
            prev_bel = None
        if not trading:
            held[:] = 0.0
            account[t:e] = 0.0
            wealth.append(W.copy())
            res.targets.append((np.array([], int), np.zeros((M, 0))))
            continue
        # ----- wealth: limited liability and the floor, then Kelly stakes in the joint problem
        W = apply_floor(limited_liability(W), cfg.wealth_floor)
        jj = np.union1d(ii, np.flatnonzero(np.abs(held).sum(0) > 1e-12))      # tradable coins plus anything still held
        pos = {j: q for q, j in enumerate(jj)}
        is_tradable = np.zeros(len(jj), bool)
        is_tradable[[pos[j] for j in ii]] = True
        beta = beta_last[jj].copy()
        beta[is_tradable] = betas(P.R[t - beta_b:t][:, jj[is_tradable]], P.btc[t - beta_b:t])
        beta_last[jj[is_tradable]] = beta[is_tradable]
        var_bar = P.R[t - cov_b:t][:, jj].var(0)
        d = np.maximum(var_bar - beta ** 2 * P.btc[t - cov_b:t].var(), 0.2 * var_bar) * H + 1e-12
        sig_d = P.R[t - cov_b:t][:, jj].std(0) * np.sqrt(bpd)
        adv_j = np.maximum(adv[jj], cfg.min_adv)
        kappa = cfg.impact_k * sig_d * np.sqrt(cfg.aum / adv_j)
        mu = np.zeros((M, len(jj)))
        mu[:, [pos[j] for j in ii]] = beliefs
        cap = np.where(is_tradable, cfg.participation * adv_j / cfg.aum, 0.0)[None, :].repeat(M, 0)
        day = P.dates[t].strftime("%Y-%m-%d")
        out_ = {names.index(nm) for nm, a0, a1 in cfg.offline if a0 <= day <= a1}    # agents that are offline now
        faulty[:] = faulty_all if not cfg.faulty_window or cfg.faulty_window[0] <= day <= cfg.faulty_window[1] else []
        for i in out_ | set(faulty):
            cap[i] = 0.0
        outside = {}                                            # an agent may only hold the coins its card names
        for i, ag in enumerate(agents):
            if getattr(ag, 'universe', None):
                outside[i] = np.array([P.tickers[j] not in ag.universe for j in jj])
                cap[i, outside[i]] = 0.0
        Wn = np.maximum(W, 1e-9 * W.sum())
        scale = np.ones(M)                                      # calibration spec: over-confident agents bet less
        for i in range(M):
            if sum(len(b) for b, _ in calib[i]) >= cfg.calibration_min_obs:
                b = np.concatenate([x for x, _ in calib[i]])
                f = np.concatenate([y for _, y in calib[i]])
                scale[i] = float(stl.kelly_scale(stl.ge(stl.calibration_ucb(b, f)[2], cfg.calibration_floor)))
        res.kelly_scales.append(scale)
        A_neutral = np.column_stack([np.ones(len(jj)), beta])
        Fvar = np.array([[P.btc[t - cov_b:t].var() * H]])
        p = CellProblem(mu=mu, gamma=1.0 / (cfg.kelly * scale * Wn), d=d, H=held[:, jj].sum(0), fee=cfg.fee_bps / 1e4, kappa=kappa,
                        B=beta[:, None], F=Fvar, A=[A_neutral if ag.neutral else None for ag in agents], cap=cap,
                        margin=cfg.leverage * Wn, gross=cfg.gross * W.sum(), beta=beta, beta_band=cfg.beta_band * W.sum())
        exante = lambda X: np.sqrt(X @ (d * X) + (beta @ X) ** 2 * Fvar[0, 0]) * np.sqrt(P.ppy / H)
        g_eff = 1.0 / np.sum(1.0 / p.gamma)                     # curvature of the agents' own risk terms taken together
        dd_scale = supervisor.drawdown_scale(out["net"][:t], cfg) if derisk else 1.0   # bars before t only
        vol_cap = cfg.target_vol * dd_scale * W.sum()           # the limit is a share of CURRENT equity (positions are in initial-equity units)
        p.vol_penalty = lam_prev                                # the volatility limit as a PRICE on system variance; start at last price
        sol = solve(p, out_)
        v = exante(sol.x.sum(0))
        for _ in range(5):
            if hold and supervisor.unsafe(sol, cfg):            # no point searching the price of a solve we will not trade
                break
            if v <= vol_cap * 1.02 and (p.vol_penalty == 0.0 or v >= vol_cap * 0.98):
                break
            p.vol_penalty = max(g_eff * ((1.0 + p.vol_penalty / g_eff) * v / vol_cap - 1.0), 0.0)
            sol = solve(p, out_)
            v = exante(sol.x.sum(0))
        lam_prev = p.vol_penalty
        res.vol_price.append(p.vol_penalty)
        res.sys_vol.append(v / W.sum())
        res.iters.append(sol.iters)
        res.isolated.append(sorted(quarantine))
        res.solved.append(int(t))
        res.solve_dates.append(P.dates[t])
        res.rel_res.append(float(sol.state.get("rel_res", np.nan)))
        res.converged.append(bool(sol.converged))
        res.dd_scale.append(dd_scale)
        held_now = hold and supervisor.unsafe(sol, cfg)
        res.held.append(held_now)
        res.unconverged += not sol.converged
        if not sol.converged:
            res.residuals.append(max(sol.primal_res, sol.dual_res))
        x = held[:, jj].copy() if held_now else sol.x.copy()   # hold: keep the drifted positions, trade nothing
        for i, mask in outside.items():                         # the cell solve respects the cap to its tolerance; make it exact
            x[i, mask] = 0.0
        Sx = np.array([[xi @ (d * xi) + (beta @ xi) ** 2 * Fvar[0, 0] for xi in x]])[0]
        res.exante.append(np.where(Sx > 0, (mu * x).sum(1) / np.sqrt(np.maximum(Sx, 1e-300)), 0.0) * np.sqrt(P.ppy / H))
        res.agent_gross.append(np.abs(x).sum(1))
        c_agent, c_total = allocate_cost(held[:, jj], x, p.fee, kappa)
        eq_pre = W.sum()                                       # equity before this rebalance's cost
        turn += np.abs(x.sum(0) - held[:, jj].sum(0)).sum() / eq_pre
        W = W - c_agent
        account[t] -= c_agent
        out["cost"][t] = c_total / eq_pre
        held[:] = 0.0
        held[:, jj] = x
        res.targets.append((jj.copy(), x.copy()))
        beta_full = np.zeros(N)
        beta_full[jj] = beta
        # ----- hold: positions drift, earn price returns, pay funding
        for b in range(t, e):
            eq = W.sum()
            eq_prev = eq_pre if b == t else eq                 # the bar's return includes the cost paid at its open
            pnl = held @ (P.R[b] - P.F[b])
            out["price"][b] = (held.sum(0) @ P.R[b]) / eq
            out["funding"][b] = -(held.sum(0) @ P.F[b]) / eq
            out["exposure"][b] = (held.sum(0) @ beta_full) / eq
            out["gross"][b] = np.abs(held.sum(0)).sum() / eq
            account[b] += pnl
            W = W + pnl
            out["net"][b] = W.sum() / eq_prev - 1.0
            held = held * (1.0 + P.R[b])[None, :]
        wealth.append(W.copy())
    t0 = rebal[0] if len(rebal) else 0
    res.dates = P.dates[t0:n]
    for kname in out:
        setattr(res, kname, out[kname][t0:n])
    res.account = account[t0:n]
    res.wealth = np.array(wealth)
    res.turnover = turn / max((n - t0) / P.ppy, 1e-9)
    return res
