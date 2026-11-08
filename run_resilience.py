"""Experiment 021, part A: resilience of the decentralised optimiser on simulated problems.

python run_resilience.py [--workers 4]

Link failures, a misbehaving agent (constant lie or noise) with and without detect-and-isolate, and trimmed (W-MSR) mixing
with no attacker, on the eight-agent problems of experiment 020 (fresh seeds 10-12). Writes docs/experiments/data/021/partA.csv
and prints the gates A1 and A2 (rules in docs/experiments/021-resilience.md). No market data is used.
"""
import argparse
import os
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
import pandas as pd

from mas_trade.cells_admm import solve_cells
from mas_trade.graph_admm import adjacency, metropolis, solve_cells_graph, solve_cells_resilient
from run_topology import problem

M, LIAR, SEEDS, CAP, TOL = 8, 3, (10, 11, 12), 4000, 1e-8
GRAPHS = (("complete", 1), ("ring2", 3), ("ring", 3))


def attack_fn(kind, size):
    if kind == "noise":
        return lambda v, k: v + np.random.default_rng(k).normal(0.0, size, v.shape)
    return lambda v, k: v + size


def one(job):
    case, graph, r, seed, q, liar, size, defence = job
    p = problem(seed, M)
    if liar:
        p.cap = p.cap.copy()
        p.cap[LIAR] = 0.0                                    # the misbehaving agent holds nothing: the optimum is without it
    opt = solve_cells(p, tol=1e-10, iters=50000).X
    A = adjacency(graph, M)
    kw = dict(rounds=r, tol=TOL, link_fail=q, seed=seed, faulty=[LIAR] if liar else [],
              attack=attack_fn(liar, size) if liar else None)
    isolated, err_msg = [], ""
    try:
        if defence == "detect":
            g = solve_cells_resilient(p, A, detect=50, iters=CAP, **kw)
            isolated = g.state["isolated"]
        else:
            g = solve_cells_graph(p, metropolis(A), trim=1 if defence == "trim" else 0,
                                  iters=1000 if (liar and defence == "none") else CAP, **kw)
        err, it, conv = float(np.abs(g.X - opt).max() / np.abs(opt).mean()), g.iters, g.converged
    except RuntimeError as ex:                               # isolation disconnected the graph
        err, it, conv, err_msg = np.nan, np.nan, False, str(ex)
    return {"case": case, "graph": graph, "rounds": r, "seed": seed, "link_fail": q, "liar": liar or "", "size": size,
            "defence": defence, "iterations": it, "converged": conv, "net_error": err,
            "isolated": " ".join(map(str, isolated)), "liar_isolated": bool(liar) and isolated == [LIAR],
            "honest_isolated": any(i != LIAR for i in isolated), "failure": err_msg}


def jobs():
    out = []
    for s in SEEDS:
        for g, r in GRAPHS:
            out += [("links", g, r, s, q, None, 0.0, "none") for q in (0.0, 0.1, 0.3, 0.5)]
            out += [("detect_clean", g, r, s, 0.0, None, 0.0, "detect")]
            out += [("liar", g, r, s, 0.0, "constant", d, "detect") for d in (0.001, 0.01, 1.0)]
            out += [("liar", g, r, s, 0.0, "constant", 0.01, "none")]
        for g, r in GRAPHS[:2]:
            out += [("liar", g, r, s, 0.0, "noise", 0.01, "detect"), ("trim_clean", g, r, s, 0.0, None, 0.0, "trim")]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    with Pool(args.workers) as pool:
        d = pd.DataFrame(pool.map(one, jobs(), chunksize=1))
    pd.options.display.width = 220
    lk = d[d.case == "links"]
    a1 = lk[lk.link_fail <= 0.3]
    ok1 = bool(a1.converged.all() and (a1.net_error <= 1e-4).all())
    print("A1 link failures (q <= 0.3 converge, error <= 1e-4): " + ("PASS" if ok1 else "FAIL"))
    print(lk.pivot_table(index=["graph", "link_fail"], values=["iterations", "net_error", "converged"],
                         aggfunc={"iterations": "median", "net_error": "max", "converged": "mean"}).to_string())
    robust = d[d.graph.isin(["complete", "ring2"]) & (d.defence == "detect")]
    clean, const = robust[robust.case == "detect_clean"], robust[robust.liar == "constant"]
    ok2 = bool((clean.isolated == "").all() and clean.converged.all() and const.liar_isolated.all()
               and not const.honest_isolated.any() and const.converged.all() and (const.net_error <= 1e-4).all())
    print("A2 detect-and-isolate on robust graphs (complete, ring2): " + ("PASS" if ok2 else "FAIL"))
    cols = ["case", "graph", "seed", "liar", "size", "defence", "iterations", "converged", "net_error", "isolated", "failure"]
    print(d[d.case != "links"].sort_values(["case", "graph", "liar", "size", "defence", "seed"])[cols].to_string(index=False))
    out = Path("docs/experiments/data/021")
    out.mkdir(parents=True, exist_ok=True)
    d.round(8).to_csv(out / "partA.csv", index=False)
