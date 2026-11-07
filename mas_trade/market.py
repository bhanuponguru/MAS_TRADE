"""Level 1: a market of agents that stake capital on their own beliefs.

Every period each agent i, with wealth W_i, stakes Kelly on its belief: risk aversion gamma_i = 1 / (f_i W_i), so an
uncoupled agent holds f_i W_i Sigma^-1 (mu_i - A nu). The system trades the NET of the stakes; each agent's account earns
the P&L of its own stake minus its share of the cost of the net trade, so the accounts add up to the real P&L; wealth
compounds, with limited liability (a loss beyond an agent's wealth is borne by the others) and an optional floor on every
agent's share (a virtual transfer from the larger accounts). The floor is also a rebalancing rule that keeps a failing agent
alive and gives it a persistent share, so it blunts selection (experiment 012).
With coupling (cost on the net trade, capacities, margin, system limits) the stakes come from the joint ADMM of
cells_admm.py; without it they are the closed form.
"""
from dataclasses import dataclass

import numpy as np

from .attribution import allocate_cost
from . import stl
from .cells_admm import CellProblem, solve_cells, solve_uncoupled


@dataclass
class MarketConfig:
    kelly: np.ndarray                  # (M,) fraction of full Kelly of each agent
    floor: float = 0.02                # minimum wealth share of every agent
    fee: float = 0.0
    kappa: np.ndarray = None           # (N,) impact coefficients (None = no cost)
    coupled: bool = False              # use the joint ADMM (needed for cost, capacity, margin, system limits)
    neutral: bool = True               # agents are dollar- and factor-neutral
    leverage: float = np.inf           # margin: sum_a |x_ia| <= leverage x wealth
    cap: float = np.inf                # per-coin capacity as a multiple of wealth
    gross: float = np.inf              # system gross cap as a multiple of total equity
    beta_band: float = np.inf          # |beta'X| <= beta_band x total equity
    calibration_floor: float = None    # agent spec: slope of returns on its beliefs must stay above this; scales its Kelly fraction
    calibration_window: int = 250      # periods of past beliefs and returns behind the slope
    calibration_min_obs: int = 2000    # (period, coin) observations needed before the spec acts


@dataclass
class MarketResult:
    wealth: np.ndarray                 # (T+1, M)
    stakes: np.ndarray                 # (T, M, N) cell positions after trading
    net: np.ndarray                    # (T, N) system position
    pnl: np.ndarray                    # (T, M) account P&L after cost
    cost: np.ndarray                   # (T, M) allocated cost
    real_pnl: np.ndarray               # (T,) P&L of the real net position, before cost
    real_cost: np.ndarray              # (T,)
    equity: np.ndarray                 # (T+1,) real equity

    @property
    def share(self):
        tot = self.wealth.sum(1, keepdims=True)
        return np.divide(self.wealth, tot, out=np.zeros_like(self.wealth), where=tot > 0)


def limited_liability(w):
    """An account cannot hold less than nothing: a negative wealth is set to zero and the shortfall is a real loss borne
    by the other accounts, pro rata. The total is unchanged."""
    if w.sum() <= 0:                                   # the whole system is wiped out
        return np.zeros_like(w)
    neg = w < 0
    if not neg.any():
        return w
    out = np.where(neg, 0.0, w)
    return out * (w.sum() / out.sum())


def apply_floor(w, floor):
    """Lift every wealth below floor x total up to it, paid pro rata by the others; the total is unchanged."""
    tot = w.sum()
    low = w < floor * tot
    if tot <= 0 or not low.any() or low.all():
        return w
    out = w.copy()
    out[low] = floor * tot
    out[~low] = w[~low] * (tot - out[low].sum()) / w[~low].sum()
    return out


def _calibration_scale(beliefs, R, t, cfg):
    """Per-agent Kelly multiplier from the calibration spec (the upper confidence bound of the slope of past returns on the
    agent's past beliefs stays above the floor)."""
    M = beliefs.shape[0]
    if cfg.calibration_floor is None:
        return np.ones(M)
    lo = max(0, t - cfg.calibration_window)
    if (t - lo) * R.shape[1] < cfg.calibration_min_obs:
        return np.ones(M)
    ucb = np.array([stl.calibration_ucb(beliefs[i, lo:t], R[lo:t])[2] for i in range(M)])
    return stl.kelly_scale(stl.ge(ucb, cfg.calibration_floor))


def run_market(R, beliefs, d, B, F, cfg, w0=None, funding=None):
    """Simulate the market. R (T, N) returns, beliefs (M, T, N); d, B, F the risk model (see CellProblem)."""
    M, T, N = beliefs.shape
    wealth = np.zeros((T + 1, M))
    wealth[0] = np.full(M, 1.0 / M) if w0 is None else w0
    stakes, net = np.zeros((T, M, N)), np.zeros((T, N))
    pnl, cost = np.zeros((T, M)), np.zeros((T, M))
    real_pnl, real_cost = np.zeros(T), np.zeros(T)
    equity = np.zeros(T + 1)
    equity[0] = wealth[0].sum()
    held = np.zeros((M, N))
    A = [np.column_stack([np.ones(N), B[:, 0]]) if cfg.neutral else None for _ in range(M)]
    kappa = np.zeros(N) if cfg.kappa is None else cfg.kappa
    for t in range(T):
        if wealth[t].sum() <= 0:                                    # the system is wiped out: nothing trades any more
            equity[t + 1] = equity[t]
            continue
        W = np.maximum(wealth[t], 1e-9 * wealth[t].sum())          # an extinct agent stakes (almost) nothing
        kelly = cfg.kelly * _calibration_scale(beliefs, R, t, cfg)
        p = CellProblem(mu=beliefs[:, t], gamma=1.0 / (kelly * W), d=d, H=held.sum(0), fee=cfg.fee, kappa=kappa,
                        B=B, F=F, A=A)
        if cfg.coupled:
            p.cap = np.full((M, N), cfg.cap) * W[:, None] if np.isfinite(cfg.cap) else p.cap
            p.margin = cfg.leverage * W if np.isfinite(cfg.leverage) else p.margin
            p.gross = cfg.gross * equity[t]
            if np.isfinite(cfg.beta_band):
                p.beta, p.beta_band = B[:, 0], cfg.beta_band * equity[t]
            x = solve_cells(p).x
        else:
            x = solve_uncoupled(p)
        c_agent, c_total = allocate_cost(held, x, cfg.fee, kappa)
        r = R[t] if funding is None else R[t] - funding[t]
        gain = x @ r
        stakes[t], net[t] = x, x.sum(0)
        pnl[t], cost[t] = gain - c_agent, c_agent
        real_pnl[t], real_cost[t] = net[t] @ r, c_total
        w_new = wealth[t] + pnl[t]
        wealth[t + 1] = apply_floor(limited_liability(w_new), cfg.floor)
        equity[t + 1] = equity[t] + real_pnl[t] - c_total
        held = x * (1.0 + R[t])
    return MarketResult(wealth, stakes, net, pnl, cost, real_pnl, real_cost, equity)
