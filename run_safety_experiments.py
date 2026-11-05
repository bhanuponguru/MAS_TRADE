"""Safety-layer experiments (docs/experiments/): python run_safety_experiments.py [--exp d028|all]

The `risk` allocation variants of experiment 010 were removed with decision 0029 (source kept in that doc).

Every variant is one Config change from the same base run, on the same data, so rows are comparable.
Results are split into a development period (<= DEV_END) and a later test period: decide on dev,
use test only to check the decision holds.
"""
import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from mas_trade import safety
from mas_trade.agents import AdversarialAgent, default_agents
from mas_trade.backtest import run_backtest
from mas_trade.config import Config
from mas_trade.data import load_returns
from mas_trade.metrics import perf_stats

DEV_END = "2022-12-31"
STRESS = {"COVID 2020": ("2020-02-15", "2020-04-30"), "2022": ("2022-01-01", "2022-12-31"),
          "Apr 2025": ("2025-03-15", "2025-05-15")}

ap = argparse.ArgumentParser()
ap.add_argument("--exp", default="all", choices=["d028", "all"])
args = ap.parse_args()

base = Config()
rets, bench = load_returns(base)
out = Path("results/experiments/safety")
out.mkdir(parents=True, exist_ok=True)


def period_row(r, w, dis, cfg):
    st = perf_stats(r, cfg.periods_per_year)
    _, summ = safety.evaluate(r, cfg, w, dis)
    return {"Sharpe": st["Sharpe"], "CAGR": st["CAGR"], "Vol": st["Vol"], "MaxDD": st["MaxDD"],
            **{f"viol_{k[4:]}": summ.loc[k, "violated"] for k in ("phi_dd", "phi_vol", "phi_rec", "phi_conc")},
            "worst_rho_vol": summ.loc["phi_vol", "robustness"]}


def evaluate_run(name, res, cfg):
    r = res.returns["MAS"]
    dis = pd.Series(res.disagreement[:, -1], index=res.weights.index)
    rows = []
    for period, sl in (("dev", slice(None, DEV_END)), ("test", slice(DEV_END, None))):
        row = period_row(r.loc[sl], res.weights.loc[sl], dis.loc[sl], cfg)
        sf = res.safety.loc[sl]
        row.update(period=period, variant=name, interventions=int(sf["intervened"].sum()),
                   daily_cuts=int(sf.get("daily_cuts", pd.Series(0)).sum()), mean_lam=float(sf["lam"].mean()))
        rows.append(row)
    stress = {k: {"ret": float((1 + r.loc[a:b]).prod() - 1), "maxDD": perf_stats(r.loc[a:b])["MaxDD"]}
              for k, (a, b) in STRESS.items()}
    return rows, {"variant": name, "turnover": res.turnover["MAS"],
                  **{f"{k} {m}": v for k, d in stress.items() for m, v in d.items()}}


def run(variants, agents_fn, tag):
    rows, extra, results = [], [], {}
    for name, cfg in variants.items():
        res = run_backtest(rets, cfg, agents_fn(), benchmark=bench)
        results[name] = res
        r, x = evaluate_run(name, res, cfg)
        rows += r
        extra.append(x)
        print(f"  done {name}")
    tab = pd.DataFrame(rows).set_index(["period", "variant"])
    ex = pd.DataFrame(extra).set_index("variant")
    tab.to_csv(out / f"{tag}_periods.csv")
    ex.to_csv(out / f"{tag}_stress.csv")
    pd.options.display.float_format = "{:.3f}".format
    for p in ("dev", "test"):
        print(f"\n[{tag}] {p}\n" + tab.loc[p].to_string())
    print(f"\n[{tag}] turnover and stress windows\n" + ex.to_string())
    return results


def variants(hier=False):
    on = replace(base, safety=True, hierarchical=hier)
    return {"no shield": replace(base, hierarchical=hier),
            "rebalance only": replace(on, safety_daily=False),
            "daily (default)": on}


if args.exp in ("d028", "all"):
    print("== flat MAS, default agents")
    run(variants(), default_agents, "flat")
    print("== hierarchical MAS-H, default agents")
    run(variants(hier=True), default_agents, "hier")
if args.exp == "all":
    print("== flat MAS with one compromised agent (adversary frozen in consensus)")
    agents_fn = lambda: default_agents() + [AdversarialAgent(seed=0)]
    res = run(variants(), agents_fn, "adversary")
    names = [a.name for a in agents_fn()]
    cap = {k: r.capital.div(r.capital.sum(axis=1), axis=0)[names[-1]].mean() for k, r in res.items()}
    print("\nadversary's mean capital share: " + ", ".join(f"{k} {v:.3f}" for k, v in cap.items()))
print(f"\ncsv written to {out}/")
