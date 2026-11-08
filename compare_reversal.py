"""Pre-registered comparisons of experiment 017 (decision 0040) from saved runs under results/ and the run logs.

python compare_reversal.py

Admission of reversal: (a) stand-alone net Sharpe 90% block-bootstrap lower bound above 0, (b) rank IC t > 2 (read from results/<tag>/run.log),
(c) intercept of its net return on BTC and the stand-alone carry and H2 returns, lower bound above 0; each on at least two of three
bars. Market acceptance: market of three minus market of two (paired Sharpe difference, ladder rule). Reported: market of three
against a fixed inverse-volatility blend of the three stand-alone runs, and the annual cost of the market against the blended cost.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

from mas_trade.metrics import block_bootstrap_regression, block_bootstrap_sharpe, extended_stats

BPD = {"1d": 1, "4h": 6, "1h": 24}
load = lambda bar, tag: pd.read_csv(Path("results") / f"{bar}_broad_{tag}" / "bars.csv", index_col=0, parse_dates=True)


def ic_t(bar):
    text = (Path("results") / f"{bar}_broad_RankReversal" / "run.log").read_text()
    m = re.search(r"^RankReversal\s+(-?[\d.]+)\s+(-?[\d.]+)", text, re.M)
    return float(m.group(1)), float(m.group(2))


rows = {}
for bar, bpd in BPD.items():
    ppy, block = 365.0 * bpd, 7 * bpd
    c, h, rv = load(bar, "RankCarry"), load(bar, "TSMomentum_restricted"), load(bar, "RankReversal")
    m2, m3 = load(bar, "RankCarry+TSMomentum_restricted"), load(bar, "RankCarry+TSMomentum+RankReversal")
    sh, lo, hi = block_bootstrap_sharpe(rv["net"], ppy, block)
    X = pd.DataFrame({"btc": rv["btc"], "carry": c["net"].reindex(rv.index), "h2": h["net"].reindex(rv.index)})
    reg = block_bootstrap_regression(rv["net"], X, block)
    d2, lo2, hi2 = block_bootstrap_sharpe(m3["net"], ppy, block, ref=m2["net"].reindex(m3.index))
    w = np.array([1 / x["net"].std() for x in (c, h, rv)]); w = w / w.sum()
    blend = w[0] * c["net"] + w[1] * h["net"] + w[2] * rv["net"].reindex(c.index)
    blend = blend.reindex(m3.index)
    db, lob, hib = block_bootstrap_sharpe(m3["net"], ppy, block, ref=blend)
    blend_cost = (w[0] * c["cost"] + w[1] * h["cost"] + w[2] * rv["cost"].reindex(c.index)).reindex(m3.index)
    ic, t = ic_t(bar)
    rows[bar] = {"reversal Sharpe": sh, "5% (a)": lo, "95%": hi, "IC": ic, "IC t (b)": t,
                 "beta to BTC": reg.loc["btc", "coef"], "alpha ann": reg.loc["intercept", "coef"] * ppy, "alpha 5% (c)": reg.loc["intercept", "5%"] * ppy,
                 "alpha 95%": reg.loc["intercept", "95%"] * ppy, "market of two": extended_stats(m2["net"], ppy)["Sharpe"],
                 "market of three": extended_stats(m3["net"], ppy)["Sharpe"], "3 vs 2 diff": d2, "3 vs 2 5%": lo2, "3 vs 2 95%": hi2,
                 "blend of three": extended_stats(blend, ppy)["Sharpe"], "market - blend": db, "mb 5%": lob, "mb 95%": hib,
                 "market cost ann": m3["cost"].mean() * ppy, "blend cost ann": blend_cost.mean() * ppy}
res = pd.DataFrame(rows).T
pd.options.display.float_format = "{:.3f}".format
pd.options.display.width = 280
print(res.T.to_string())
a = int((res["5% (a)"] > 0).sum()) >= 2
b = int((res["IC t (b)"] > 2).sum()) >= 2
cc = int((res["alpha 5% (c)"] > 0).sum()) >= 2
acc = int((res["3 vs 2 5%"] > 0).sum()) >= 2 and not (res["3 vs 2 95%"] < 0).any()
print(f"\nadmission (a) Sharpe lower bound above 0 on >= 2 of 3: {'PASS' if a else 'FAIL'}")
print(f"admission (b) IC t > 2 on >= 2 of 3: {'PASS' if b else 'FAIL'}")
print(f"admission (c) alpha vs BTC, carry, H2 lower bound above 0 on >= 2 of 3: {'PASS' if cc else 'FAIL'}")
print(f"reversal admitted: {'YES' if a and b and cc else 'NO'}")
print(f"market acceptance (three beats two, paired, ladder rule): {'PASS' if acc else 'FAIL'}")
out = Path("docs/experiments/data/017")
out.mkdir(parents=True, exist_ok=True)
res.to_csv(out / "comparison.csv")
