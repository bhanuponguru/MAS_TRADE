"""Data and simulation behind the dashboard (dashboard.py, decision 0045). No Streamlit here, so it is tested on its own.

simulate() runs the real decentralised optimiser (graph_admm) on a simulated problem of experiments 020-021 and returns what the
dashboard draws: the communication graph, the error of the agreed position against the central optimum and the agents'
disagreement after every iteration, and who was isolated. load_run() reads a saved engine run from results/<tag>/.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from .cells_admm import solve_cells
from .graph_admm import adjacency, is_connected, metropolis, solve_cells_graph, solve_cells_resilient

RESULTS = Path("results")
DOCS_DATA = Path("docs/experiments/data")
STRESS = {"May-Jul 2021": ("2021-05-01", "2021-07-31"), "LUNA 2022": ("2022-05-01", "2022-07-31"),
          "FTX 2022-23": ("2022-11-01", "2023-01-31")}
PPY = {"1d": 365.0, "4h": 365.0 * 6, "1h": 365.0 * 24}


def sim_problem(seed, M):
    """The simulated problem of experiments 020-021 (every limit binding)."""
    from run_topology import problem
    return problem(seed, M)


def circle_layout(M):
    a = np.pi / 2 - 2 * np.pi * np.arange(M) / M
    return np.column_stack([np.cos(a), np.sin(a)])


def attack_fn(kind, size):
    if kind == "noise":
        return lambda v, k: v + np.random.default_rng(k).normal(0.0, size, v.shape)
    return lambda v, k: v + size


def simulate(M=8, topology="complete", rounds=1, link_fail=0.0, liar=None, size=0.01, detect=0, seed=0, iters=2000, tol=1e-6):
    """One decentralised solve. liar: None, "constant" or "noise" (agent 3 misbehaves: holds nothing, sends lies).
    Returns a dict; 'error' and 'disagreement' are per iteration (error = max |X_k - X*| / mean |X*| on the net position)."""
    p = sim_problem(seed, M)
    faulty = [3 % M] if liar else []
    if liar:
        p.cap = p.cap.copy()
        p.cap[faulty[0]] = 0.0                                 # the right answer is the optimum without the liar
    opt = solve_cells(p, tol=1e-10, iters=50000).X
    A = adjacency(topology, M, seed=seed)
    kw = dict(rounds=rounds, tol=tol, link_fail=link_fail, seed=seed, faulty=faulty,
              attack=attack_fn(liar, size) if liar else None)
    trace, isolated, failure = [], [], ""
    try:
        if detect:
            g = solve_cells_resilient(p, A, detect=detect, iters=iters, trace=trace, **kw)
            isolated = g.state["isolated"]
        else:
            g = solve_cells_graph(p, metropolis(A), iters=iters, trace=trace, **kw)
        conv, its = bool(g.converged), int(g.iters)
    except RuntimeError as ex:                                 # isolation disconnected the graph
        conv, its, failure = False, len(trace), str(ex)
    typ = float(np.abs(opt).mean())
    err = np.array([np.abs(x - opt).max() / typ for x, _ in trace])
    dis = np.array([d for _, d in trace])
    edges = int(A.sum() // 2)
    return {"A": A, "edges": edges, "iterations": its, "converged": conv, "error": err, "disagreement": dis,
            "final_error": float(err[-1]) if len(err) else np.nan, "messages": its * rounds * 2 * edges,
            "isolated": isolated, "faulty": faulty, "failure": failure, "connected": bool(is_connected(A))}


def saved_runs():
    """Tags of saved engine runs (folders of results/ with a bars.csv)."""
    return sorted(d.name for d in RESULTS.glob("*") if (d / "bars.csv").exists()) if RESULTS.exists() else []


def bar_of(tag):
    for b in ("1h", "4h", "1d"):
        if tag.startswith(b + "_") or f"_{b}_" in tag:
            return b
    return "1d"


def load_run(tag):
    d = RESULTS / tag
    read = lambda f, **kw: pd.read_csv(d / f, **kw) if (d / f).exists() else None
    bars = read("bars.csv", index_col=0, parse_dates=True)
    rebal = read("rebal.csv", parse_dates=["date"])
    safety = read("safety.csv", index_col=0, parse_dates=True)
    return bars, rebal, safety


def equity(bars):
    return (1.0 + bars["net"]).cumprod()


def agent_wealth(bars):
    """Each agent's wealth in units of the initial equity: an equal start plus its own account P&L (acc_* columns)."""
    acc = bars[[c for c in bars.columns if c.startswith("acc_")]]
    acc.columns = [c[4:] for c in acc.columns]
    return 1.0 / acc.shape[1] + acc.cumsum()


def stats(net, ppy):
    eq = (1.0 + net).cumprod()
    yrs = len(net) / ppy
    return {"Sharpe": float(net.mean() / net.std() * np.sqrt(ppy)), "CAGR": float(eq.iloc[-1] ** (1 / yrs) - 1),
            "Vol": float(net.std() * np.sqrt(ppy)), "MaxDD": float((eq / eq.cummax() - 1).min()), "Final equity": float(eq.iloc[-1])}


def committed(exp, name):
    f = DOCS_DATA / exp / name
    return pd.read_csv(f) if f.exists() else None
