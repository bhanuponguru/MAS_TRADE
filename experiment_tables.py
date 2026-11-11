"""Result tables of experiments 020 (part B), 021 (part B) and 022 from saved runs (no engine run).

python experiment_tables.py 020|021|022 [--out DIR]     default DIR: docs/experiments/data/<exp>

These tables were first computed by hand in a notebook session; this script reproduces them from `results/<tag>/`
(bars.csv, rebal.csv, safety.csv, run.log) so that the committed CSVs can be regenerated. Dev period only: the saved runs
never contain the sealed final 12 months.
  020  partB_runs.csv  eight agents on 1d: hub against the graph optimiser per topology and iteration cap
  021  partB_runs.csv  link failures, an offline agent, a liar with and without detect-and-isolate
  022  runs.csv, windows.csv  safety supervisor off / derisk / hold, and the noise liar under hold
"""
import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

from mas_trade.graph_admm import adjacency
from mas_trade.metrics import extended_stats
from mas_trade.supervisor import WINDOWS, window_summary

R = Path("results")
BPD = {"1d": 1, "4h": 6, "1h": 24}
CAP = 3000                                            # the solver's default iteration cap (cells_admm.solve_cells)
M8 = 8                                                # agents in the eight-agent roster of 020 and 021


def bars(tag):
    return pd.read_csv(R / tag / "bars.csv", index_col=0, parse_dates=True)


def log_value(tag, key):
    """A number from the summary table that run_benchmark.py prints into run.log (e.g. 'cells not converged')."""
    m = re.search(rf"^{re.escape(key)}\s+(-?[\d.]+)", (R / tag / "run.log").read_text(), re.M)
    return float(m.group(1)) if m else np.nan


def money(tag, ppy=365.0):
    st = extended_stats(bars(tag)["net"], ppy)
    return {"sharpe": st["Sharpe"], "cagr": st["CAGR"], "vol": st["Vol"], "maxdd": st["MaxDD"],
            "final_equity": float((1 + bars(tag)["net"]).prod())}


def isolated_at_end(tag):
    m = re.search(r"isolated at the end \[(.*?)\]", (R / tag / "run.log").read_text())
    return ", ".join(s.strip(" '") for s in m.group(1).split(",")) if m and m.group(1) else ""


def max_exante_vol(tag):
    f = R / tag / "rebal.csv"
    return float(pd.read_csv(f)["sys_vol"].max()) if f.exists() else np.nan


def t020():
    runs = [("hub", "hub", "", "", CAP), ("complete_r1", "graph", "complete", 1, CAP), ("ring_r1", "graph", "ring", 1, CAP),
            ("ring_r3", "graph", "ring", 3, CAP), ("line_r3", "graph", "line", 3, CAP), ("star_r3", "graph", "star", 3, CAP),
            ("hub_cap200", "hub", "", "", 200), ("ring_r3_cap200", "graph", "ring", 3, 200)]
    hub = bars("020_eight_hub")["net"]
    rows = []
    for name, cons, topo, rounds, cap in runs:
        tag = f"020_eight_{name}"
        m, net = money(tag), bars(tag)["net"]
        it = log_value(tag, "solver iterations (mean)")
        diff = (net - hub).abs()
        rows.append({"run": name, "consensus": cons, "topology": topo, "rounds": rounds, "iter_cap": cap,
                     "sharpe": round(m["sharpe"], 3), "cagr": round(m["cagr"], 3), "vol": round(m["vol"], 3), "maxdd": round(m["maxdd"], 3),
                     "final_equity": round(m["final_equity"], 4),
                     "equity_vs_hub": round(m["final_equity"] / float((1 + hub).prod()) - 1, 5),
                     "capped_rebalances": int(log_value(tag, "cells not converged")), "mean_iterations": round(it, 3),
                     # one message per directed edge per gossip round per iteration
                     "messages_per_rebalance": int(round(it * int(adjacency(topo, M8).sum()) * rounds)) if cons == "graph" else "",
                     "max_abs_daily_diff": f"{diff.max():.1e}", "mean_abs_daily_diff": f"{diff.mean():.1e}"})
    return {"partB_runs.csv": pd.DataFrame(rows)}


def t021():
    tags = ["020_eight_hub", "020_eight_complete_r1", "020_eight_ring_r3", "021_links_complete_r1", "021_links_ring_r3",
            "021_offline_hub", "021_offline_complete_r1", "021_offline_ring_r3", "021_detect_clean", "021_liar_detect", "021_liar_hub"]
    rows = []
    for tag in tags:
        m = money(tag)
        v = max_exante_vol(tag)
        rows.append({"run": tag, "sharpe": round(m["sharpe"], 3), "cagr": round(m["cagr"], 3), "vol": round(m["vol"], 3),
                     "maxdd": round(m["maxdd"], 3), "final_equity": round(m["final_equity"], 4),
                     "capped_rebalances": int(log_value(tag, "cells not converged")),
                     "mean_iterations": round(log_value(tag, "solver iterations (mean)"), 3),
                     "isolated_at_end": isolated_at_end(tag), "max_exante_vol": "" if np.isnan(v) else round(v, 4)})
    return {"partB_runs.csv": pd.DataFrame(rows)}


def t022():
    tags = ["022_1d_off", "022_1d_derisk", "022_1d_hold", "022_4h_off", "022_4h_derisk", "022_1h_off", "022_1h_derisk",
            "022_three_clean", "022_three_liar", "022_three_liar_hold"]
    rows, wins = [], []
    luna = WINDOWS["luna2022"]
    for tag in tags:
        if not (R / tag / "bars.csv").exists():                     # the undefended liar run diverges and never finishes
            print(f"missing (not finished): {tag}")
            continue
        bar = tag.split("_")[1] if tag.split("_")[1] in BPD else "1d"
        ppy = 365.0 * BPD[bar]
        b = bars(tag)
        rec = pd.read_csv(R / tag / "safety.csv", index_col=0, parse_dates=True)
        rb = pd.read_csv(R / tag / "rebal.csv")
        st = extended_stats(b["net"], ppy)
        ws = window_summary(rec, ppy=ppy)
        rows.append({"run": tag, "bar": bar, "sharpe": st["Sharpe"], "cagr": st["CAGR"], "final_equity": float((1 + b["net"]).prod()),
                     "max_dd": st["MaxDD"], "rebalances": len(rb), "unconverged": int((~rb["converged"].astype(bool)).sum()),
                     "unsafe": int((rec["rho_solve"] < 0).sum()), "held": int(rb["held"].astype(bool).sum()),
                     "share_vol_ok": float((rec["rho_vol"].dropna() >= 0).mean()), "worst_rho_vol": float(rec["rho_vol"].min()),
                     "bars_dd_violating": int((rec["rho_dd"] < 0).sum()), "worst_dd365": float(rec["drawdown"].min()),
                     "min_dd_scale": float(rb["dd_scale"].min()), "luna_return": float(ws.loc["luna2022", "return"]),
                     "luna_max_dd": float(ws.loc["luna2022", "max_dd_in_window"]), "luna_cost": float(b.loc[luna[0]:luna[1], "cost"].sum())})
        wins.append(ws.rename_axis("window").reset_index().assign(run=tag))
    w = pd.concat(wins)
    w = w[["window", "run"] + [c for c in w.columns if c not in ("window", "run")]]
    return {"runs.csv": pd.DataFrame(rows).round(5), "windows.csv": w.astype({c: float for c in w.columns[2:]}).round(4)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("exp", choices=["020", "021", "022"])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = Path(args.out or f"docs/experiments/data/{args.exp}")
    out.mkdir(parents=True, exist_ok=True)
    pd.options.display.width = 250
    for name, t in {"020": t020, "021": t021, "022": t022}[args.exp]().items():
        print(f"\n{name}\n{t.to_string(index=False)}")
        t.to_csv(out / name, index=False)
    print(f"\nwritten to {out}/")
