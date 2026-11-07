"""Control for experiment 015b: is the market of carry + H2 better than a fixed-weight blend of the two stand-alone runs?

python compare_blend.py

Blends (fixed before looking): 50/50 of the stand-alone net returns, and inverse-volatility weights from each run's own full-dev
volatility. Paired block-bootstrap Sharpe difference, market minus blend (7-day blocks, 90% interval), from saved runs.
"""
from pathlib import Path

import pandas as pd

from mas_trade.metrics import block_bootstrap_sharpe, extended_stats

BPD = {"1d": 1, "4h": 6, "1h": 24}
load = lambda bar, tag: pd.read_csv(Path("results") / f"{bar}_broad_{tag}" / "bars.csv", index_col=0, parse_dates=True)["net"]
rows = {}
for bar, bpd in BPD.items():
    ppy, block = 365.0 * bpd, 7 * bpd
    c, h, m = load(bar, "RankCarry"), load(bar, "TSMomentum_restricted"), load(bar, "RankCarry+TSMomentum_restricted")
    iv = (1 / c.std()) / (1 / c.std() + 1 / h.std())
    out = {"market": extended_stats(m, ppy)["Sharpe"], "inverse-vol weight on carry": iv}
    for name, w in (("50/50", 0.5), ("inv-vol", iv)):
        b = w * c + (1 - w) * h
        d, lo, hi = block_bootstrap_sharpe(m, ppy, block, ref=b)
        out.update({f"{name} blend": extended_stats(b, ppy)["Sharpe"], f"{name} diff": d, f"{name} 5%": lo, f"{name} 95%": hi})
    rows[bar] = out
res = pd.DataFrame(rows).T
pd.options.display.float_format = "{:.3f}".format
pd.options.display.width = 250
print(res.to_string())
out = Path("docs/experiments/data/015")
res.to_csv(out / "blend_control.csv")
