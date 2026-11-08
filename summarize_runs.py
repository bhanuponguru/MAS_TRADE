"""Summary tables of saved engine runs (no new engine run): one row per (bar, run) from results/<tag>/bars.csv and run.log.

python summarize_runs.py [--out docs/experiments/data/018]

Writes runs.csv (Sharpe with its 90% block-bootstrap interval, CAGR, volatility, drawdown, annualised P&L components,
turnover) and yearly.csv (compounded return per calendar year). Dev period only: the runs themselves are sealed.
"""
import argparse
import re
from pathlib import Path

import pandas as pd

from mas_trade.metrics import block_bootstrap_sharpe, extended_stats, yearly_returns

RUNS = {"carry": "RankCarry", "H2": "TSMomentum_restricted", "reversal": "RankReversal",
        "carry+H2": "RankCarry+TSMomentum_restricted", "carry+H2+reversal": "RankCarry+TSMomentum+RankReversal"}
BPD = {"1d": 1, "4h": 6, "1h": 24}

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="docs/experiments/data/018")
args = ap.parse_args()
rows, years = [], []
for bar, bpd in BPD.items():
    ppy = 365.0 * bpd
    for name, tag in RUNS.items():
        d = Path("results") / f"{bar}_broad_{tag}"
        if not (d / "bars.csv").exists():
            print(f"missing: {d}")
            continue
        b = pd.read_csv(d / "bars.csv", index_col=0, parse_dates=True)
        st = extended_stats(b["net"], ppy)
        sh, lo, hi = block_bootstrap_sharpe(b["net"], ppy, 7 * bpd, n_boot=500)
        log = (d / "run.log").read_text() if (d / "run.log").exists() else ""
        m = re.search(r"^Turnover\s+(-?[\d.]+)", log, re.M)
        ann = b[["market", "selection", "funding", "cost"]].mean() * ppy
        rows.append({"bar": bar, "run": name, "Sharpe": sh, "Sharpe 5%": lo, "Sharpe 95%": hi, "CAGR": st["CAGR"], "Vol": st["Vol"],
                     "MaxDD": st["MaxDD"], "Calmar": st["Calmar"], **{f"ann_{k}": v for k, v in ann.items()},
                     "turnover": float(m.group(1)) if m else float("nan")})
        y = yearly_returns(b[["net"]])["net"]
        years.append(pd.Series(y.values, index=[f"y{i}" for i in y.index], name=(bar, name)))
res = pd.DataFrame(rows).set_index(["bar", "run"])
yr = pd.DataFrame(years)
pd.options.display.float_format = "{:.3f}".format
pd.options.display.width = 250
print(res.to_string(), "\n\nyearly returns:\n", yr.to_string(), sep="")
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
res.round(4).to_csv(out / "runs.csv")
yr.round(4).to_csv(out / "yearly.csv")
