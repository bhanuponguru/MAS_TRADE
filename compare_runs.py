"""Pre-registered comparisons of experiment 015 from the saved runs under results/ (no new engine run).

python compare_runs.py

H2 admission (stand-alone runs): static regression of the agent's net return on BTC (and on BTC and the carry agent's return), the
intercept annualised, 90% moving-block bootstrap interval (7-day blocks). Market acceptance: Sharpe of carry + H2 minus Sharpe of
carry alone, paired block bootstrap. Both rules are in docs/experiments/015-time-series-momentum-and-the-market.md.
"""
import argparse
from pathlib import Path

import pandas as pd

from mas_trade.metrics import block_bootstrap_regression, block_bootstrap_sharpe, extended_stats

ap = argparse.ArgumentParser()
ap.add_argument("--suffix", default="", help="tag suffix of the H2 runs (e.g. _restricted for the corrected runs of Amendment 1)")
args = ap.parse_args()
BPD = {"1d": 1, "4h": 6, "1h": 24}
load = lambda bar, tag: pd.read_csv(Path("results") / f"{bar}_broad_{tag}" / "bars.csv", index_col=0, parse_dates=True)
rows, tables = {}, {}
for bar, bpd in BPD.items():
    ppy, block = 365.0 * bpd, 7 * bpd
    carry, h2, both = load(bar, "RankCarry"), load(bar, "TSMomentum" + args.suffix), load(bar, "RankCarry+TSMomentum" + args.suffix)
    X1 = pd.DataFrame({"btc": h2["btc"]})
    X2 = pd.DataFrame({"btc": h2["btc"], "carry": carry["net"].reindex(h2.index)})
    r1 = block_bootstrap_regression(h2["net"], X1, block)
    r2 = block_bootstrap_regression(h2["net"], X2, block)
    d, lo, hi = block_bootstrap_sharpe(both["net"], ppy, block, ref=carry["net"].reindex(both.index))
    s = lambda df: extended_stats(df["net"], ppy)["Sharpe"]
    rows[bar] = {"H2 alone Sharpe": s(h2), "H2 beta to BTC": r1.loc["btc", "coef"],
                 "H2 alpha vs BTC (ann)": r1.loc["intercept", "coef"] * ppy, "5% a": r1.loc["intercept", "5%"] * ppy, "95% a": r1.loc["intercept", "95%"] * ppy,
                 "H2 alpha vs BTC+carry (ann)": r2.loc["intercept", "coef"] * ppy, "5% b": r2.loc["intercept", "5%"] * ppy, "95% b": r2.loc["intercept", "95%"] * ppy,
                 "carry alone Sharpe": s(carry), "carry+H2 Sharpe": s(both), "diff": d, "diff 5%": lo, "diff 95%": hi}
    tables[bar] = {"vs BTC": r1, "vs BTC+carry": r2}
res = pd.DataFrame(rows).T
pd.options.display.float_format = "{:.3f}".format
pd.options.display.width = 200
print(res.to_string())
adm_a = int((res["5% a"] > 0).sum()) >= 2
adm_b = int((res["5% b"] > 0).sum()) >= 2
acc_ok = int((res["diff 5%"] > 0).sum()) >= 2 and not (res["diff 95%"] < 0).any()
print(f"\nH2 admission (a) alpha vs BTC lower bound above 0 on >= 2 of 3 bars: {'PASS' if adm_a else 'FAIL'}")
print(f"H2 admission (b) alpha vs BTC and carry lower bound above 0 on >= 2 of 3 bars: {'PASS' if adm_b else 'FAIL'}")
print(f"Market acceptance (carry+H2 beats carry alone, paired): {'PASS' if acc_ok else 'FAIL'}")
out = Path("docs/experiments/data/015")
out.mkdir(parents=True, exist_ok=True)
res.to_csv(out / f"comparison{args.suffix}.csv")
