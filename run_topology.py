"""Experiment 020, part A: topology and communication budget of the decentralised optimiser on simulated problems.

python run_topology.py [--workers 10]

Writes docs/experiments/data/020/partA_runs.csv (one row per topology x agents x gossip rounds x seed), partA_budget.csv
(error after K iterations), partA_vol.csv (the priced-volatility check) and prints the gates A1 and A2 (rules in
docs/experiments/020-topology-and-communication-budget.md). No market data is used.
"""
import argparse
import os
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from mas_trade.cells_admm import CellProblem, solve_cells
from mas_trade.graph_admm import TOPOLOGIES, adjacency, metropolis, mixing_rate, solve_cells_graph

N = 8
MS = (4, 8, 16)
ROUNDS = (1, 3, 10)
SEEDS = range(5)
BUDGETS = (25, 50, 100, 200, 400)
CAP, TOL = 4000, 1e-8


def problem(seed, M, vol=False):
    """The random problem of tests/test_cells_admm.py (make) with every limit binding ('all'), for M agents."""
    r = np.random.default_rng(seed)
    B = r.uniform(0.5, 1.5, (N, 1))
    A = [np.column_stack([np.ones(N), B[:, 0]]) for _ in range(M)]
    return CellProblem(mu=r.normal(0, 0.004, (M, N)), gamma=r.uniform(0.8, 1.5, M) * 100, d=r.uniform(0.02, 0.06, N) ** 2,
                       H=r.normal(0, 0.2, N), kappa=r.uniform(0.01, 0.05, N), B=B, F=np.array([[0.05 ** 2]]), A=A,
                       fee=5e-4, cap=np.full((M, N), 0.04), margin=np.linspace(0.2, 0.3, M), gross=0.2,
                       beta=np.linspace(0.5, 1.5, N), beta_band=0.03, vol_penalty=150.0 if vol else 0.0)


def graph_stats(kind, M, seed):
    A = adjacency(kind, M, seed=seed)
    L = np.diag(A.sum(1)) - A.astype(float)
    return A, metropolis(A), int(A.sum() // 2), float(np.sort(np.linalg.eigvalsh(L))[1])


def one(job):
    kind, M, r, seed, vol = job
    p = problem(seed, M, vol)
    opt = solve_cells(p, tol=1e-10, iters=50000).X
    hub = solve_cells(p, tol=TOL, iters=CAP, relax=1.0)
    A, W, edges, alg = graph_stats(kind, M, seed)
    tr = []
    g = solve_cells_graph(p, W, rounds=r, tol=TOL, iters=CAP, trace=tr)
    typ = np.abs(opt).mean()
    row = {"topology": kind, "M": M, "rounds": r, "seed": seed, "vol": vol, "edges": edges, "lambda2_W": mixing_rate(W),
           "algebraic_connectivity": alg, "iterations": g.iters, "converged": g.converged, "hub_iterations": hub.iters,
           "messages": g.iters * r * 2 * edges, "net_error": float(np.abs(g.X - opt).max() / typ)}
    budget = [{"topology": kind, "M": M, "rounds": r, "seed": seed, "K": K,
               "net_error": float(np.abs(tr[min(K, len(tr)) - 1][0] - opt).max() / typ),
               "disagreement": float(tr[min(K, len(tr)) - 1][1])} for K in BUDGETS]
    return row, budget


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    grid = [(k, M, r, s, False) for M in (4, 8) for k in TOPOLOGIES for r in ROUNDS for s in SEEDS] + \
           [(k, 16, 3, s, False) for k in TOPOLOGIES for s in range(3)]          # amendment 1: M = 16 at r = 3, 3 seeds
    vol = [(k, 8, 3, s, True) for k in ("ring", "line") for s in range(3)]
    with Pool(args.workers) as pool:
        out = pool.map(one, grid + vol, chunksize=1)
    runs = pd.DataFrame([o[0] for o in out])
    budget = pd.DataFrame([b for o in out[:len(grid)] for b in o[1]])
    grid_runs, vol_runs = runs[~runs.vol], runs[runs.vol]
    pd.options.display.width = 220
    print("A1: Spearman(|lambda_2(W)|, iterations) at r = 3, over topology x seed")
    a1 = {}
    for M in MS:
        d = grid_runs[(grid_runs.M == M) & (grid_runs.rounds == 3)]
        a1[M] = spearmanr(d.lambda2_W, d.iterations)[0]
        print(f"  M = {M}: {a1[M]:.3f}")
    print("A1 " + ("PASS" if all(v >= 0.7 for v in a1.values()) else "FAIL"))
    comp = grid_runs[grid_runs.topology == "complete"]
    a2 = bool((comp.iterations == comp.hub_iterations).all())
    print(f"A2 complete graph = hub iterations in every case: {'PASS' if a2 else 'FAIL'}")
    summ = grid_runs.groupby(["M", "topology", "rounds"]).agg(edges=("edges", "first"), lambda2=("lambda2_W", "first"),
                                                              alg_conn=("algebraic_connectivity", "mean"), iters=("iterations", "median"),
                                                              converged=("converged", "mean"), messages=("messages", "median"),
                                                              net_error=("net_error", "max"))
    print(summ.round(4).to_string())
    print("\nA3: gossip rounds with the fewest median messages, per (M, topology):")
    best = summ.reset_index().loc[lambda d: d.groupby(["M", "topology"]).messages.idxmin()][["M", "topology", "rounds", "messages", "converged"]]
    print(best.to_string(index=False))
    print("\nA4: median net-position error after K iterations (r = 3):")
    print(budget[budget.rounds == 3].pivot_table(index=["M", "topology"], columns="K", values="net_error", aggfunc="median").round(4).to_string())
    print("\npriced-volatility check (M = 8, r = 3):")
    print(vol_runs[["topology", "seed", "iterations", "converged", "hub_iterations", "net_error"]].to_string(index=False))
    out_dir = Path("docs/experiments/data/020")
    out_dir.mkdir(parents=True, exist_ok=True)
    grid_runs.round(6).to_csv(out_dir / "partA_runs.csv", index=False)
    budget.round(6).to_csv(out_dir / "partA_budget.csv", index=False)
    vol_runs.round(6).to_csv(out_dir / "partA_vol.csv", index=False)
    summ.round(6).to_csv(out_dir / "partA_summary.csv")
