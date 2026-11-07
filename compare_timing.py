"""Timed against untimed H2 (experiment 016): paired block-bootstrap Sharpe differences from saved runs. python compare_timing.py"""
from pathlib import Path

import pandas as pd

from mas_trade.metrics import block_bootstrap_sharpe, extended_stats

BPD = {"1d": 1, "4h": 6, "1h": 24}
load = lambda bar, tag: pd.read_csv(Path("results") / f"{bar}_broad_{tag}" / "bars.csv", index_col=0, parse_dates=True)
rows = {}
for bar, bpd in BPD.items():
    ppy, block = 365.0 * bpd, 7 * bpd
    out = {}
    for label, un, ti in (("H2 alone", "TSMomentum_restricted", "TSMomentumTimed"),
                          ("carry+H2", "RankCarry+TSMomentum_restricted", "RankCarry+TSMomentumTimed")):
        a, b = load(bar, un)["net"], load(bar, ti)["net"]
        d, lo, hi = block_bootstrap_sharpe(b, ppy, block, ref=a.reindex(b.index))
        out.update({f"{label} untimed": extended_stats(a, ppy)["Sharpe"], f"{label} timed": extended_stats(b, ppy)["Sharpe"],
                    f"{label} diff": d, f"{label} 5%": lo, f"{label} 95%": hi})
    rows[bar] = out
res = pd.DataFrame(rows).T
pd.options.display.float_format = "{:.3f}".format
pd.options.display.width = 250
print(res.to_string())
for label in ("H2 alone", "carry+H2"):
    keep = int((res[f"{label} 5%"] > 0).sum()) >= 2 and not (res[f"{label} 95%"] < 0).any()
    print(f"timing kept ({label}, paired lower bound above 0 on >= 2 of 3, none upper below 0): {'YES' if keep else 'NO'}")
out = Path("docs/experiments/data/016")
out.mkdir(parents=True, exist_ok=True)
res.to_csv(out / "comparison.csv")
