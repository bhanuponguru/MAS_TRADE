"""Crypto-perp benchmark for one bar size.

python run_crypto_benchmark.py --bar 1d|4h|1h [--universe broad|majors] [--holdout-months 12] [--no-hier] [--no-stl] [--eval-from 2022-01-13]

One walk-forward backtest (nothing is fitted, settings are the Config.for_tier defaults), reported as
the development period and a final holdout, with gross vs net of costs, per-year returns and a paired
block-bootstrap interval on the Sharpe difference against BTC buy-and-hold.
MAS+STL is MAS with the safety shield (decisions 0023-0029), with an STL summary per period.
Outputs go to results/crypto/<bar>_<universe>/.
"""
import argparse
from dataclasses import replace
from pathlib import Path

import pandas as pd

from mas_trade import crypto_data as cd
from mas_trade import plots, safety
from mas_trade.agents import default_agents
from mas_trade.backtest import run_backtest
from mas_trade.config import TIERS, Config
from mas_trade.metrics import block_bootstrap_sharpe, extended_stats, split_holdout, yearly_returns

ap = argparse.ArgumentParser()
ap.add_argument("--bar", default="1d", choices=list(TIERS))
ap.add_argument("--universe", default="broad", choices=["broad", "majors"])
ap.add_argument("--holdout-months", type=int, default=12)
ap.add_argument("--boot", type=int, default=2000)
ap.add_argument("--no-hier", action="store_true")
ap.add_argument("--no-stl", action="store_true", help="skip the MAS+STL (safety shield) run")
ap.add_argument("--eval-from", default=None, help="report only from this date (common window across bar sizes); the backtest itself still runs from its own start")
args = ap.parse_args()

cfg = Config.for_tier(args.bar)
bpd = TIERS[args.bar][0]
uni = cd.load_universe(args.universe)
members = set(uni.columns[uni.any()])
rets, elig, fund, btc = cd.load_panel(args.bar, universe=uni)
missing = members - set(rets.columns)
print(f"{args.bar} / {args.universe}: {rets.shape[1]} symbols x {len(rets)} bars, "
      f"{rets.index[0].date()} -> {rets.index[-1].date()}" + (f"  [WARNING {len(missing)} members lack {args.bar} data]" if missing else ""))
print(f"ppy={cfg.periods_per_year:.0f} lookback={cfg.lookback} rebalance={cfg.rebalance_days} bars, cost={cfg.cost_bps} bps")

agents = lambda: default_agents(cfg.lookback / 252)
run = lambda c: run_backtest(rets, c, agents(), benchmark=btc, eligible=elig, funding=fund)
hier = lambda c: replace(c, hierarchical=True, eta_sub="auto")

net = run(cfg)
df = net.returns.copy()
turn = dict(net.turnover)
gross = {"MAS": run(replace(cfg, cost_bps=0.0)).returns["MAS"]}
if not args.no_hier:
    h = run(hier(cfg))
    df["MAS-H"], turn["MAS-H"] = h.returns["MAS"], h.turnover["MAS"]
    gross["MAS-H"] = run(hier(replace(cfg, cost_bps=0.0))).returns["MAS"]
if not args.no_stl:
    st = run(replace(cfg, safety=True))
    df["MAS+STL"], turn["MAS+STL"] = st.returns["MAS"], st.turnover["MAS"]
    gross["MAS+STL"] = run(replace(cfg, safety=True, cost_bps=0.0)).returns["MAS"]
print(f"trading {df.index[0].date()} -> {df.index[-1].date()}  ({len(df)} bars, avg tradable "
      f"{int(elig.loc[net.weights.index].sum(axis=1).mean())} symbols)")

if args.eval_from:   # same window for every bar size (the shortest-history tier sets the common start)
    df = df.loc[args.eval_from:]
    gross = {k: g.loc[args.eval_from:] for k, g in gross.items()}
    print(f"reporting window restricted to {df.index[0].date()} -> {df.index[-1].date()} ({len(df)} bars); Turnover is over the whole run")
ppy = cfg.periods_per_year
table = lambda d: pd.DataFrame({c: extended_stats(d[c], ppy) for c in d}).T
out = Path("results/crypto") / f"{args.bar}_{args.universe}{'_common' if args.eval_from else ''}"
out.mkdir(parents=True, exist_ok=True)
full = table(df)
full["Turnover"] = pd.Series(turn)
for k, g in gross.items():
    full.loc[k, "CostDrag"] = extended_stats(g, ppy)["CAGR"] - full.loc[k, "CAGR"]
dev, hold = split_holdout(df, args.holdout_months)
tabs = {"full": full, "dev": table(dev), "holdout": table(hold)}
for name, t in tabs.items():
    t.to_csv(out / f"metrics_{name}.csv")
yearly = yearly_returns(df)
yearly.to_csv(out / "yearly_returns.csv")

pd.options.display.float_format = "{:.3f}".format
pd.options.display.width = 200
for name, t in tabs.items():
    span = {"full": df, "dev": dev, "holdout": hold}[name]
    print(f"\n=== {name}: {span.index[0].date()} -> {span.index[-1].date()} ({len(span)} bars) ===")
    print(t.sort_values("Sharpe", ascending=False).drop(columns=["HitRate"]).to_string())

# STL specs per period (robustness normalised by the limit; violated = share of bars / rebalances)
if not args.no_stl:
    print(f"\nSTL limits: maxDD {cfg.safety_max_dd:.0%} over {cfg.safety_dd_window} bars, vol {cfg.safety_max_vol:.0%} "
          f"over {cfg.safety_vol_window} bars, recover within {cfg.safety_recover} bars, |w_k| <= {cfg.safety_max_weight:.0%}")
    dis = lambda r: pd.Series(r.disagreement[:, -1], index=r.weights.index)
    stl_rows = {}
    for pname, span in (("dev", dev), ("holdout", hold)):
        a, b = span.index[0], span.index[-1]
        for label, r in (("MAS", net), ("MAS+STL", st)):
            _, summ = safety.evaluate(r.returns["MAS"].loc[a:b], cfg, r.weights.loc[a:b], dis(r).loc[a:b])
            for spec, row in summ.iterrows():
                stl_rows[(pname, label, spec)] = row
    stl = pd.DataFrame(stl_rows).T
    stl.index.names = ["period", "system", "spec"]
    stl.to_csv(out / "stl_summary.csv")
    st.safety.to_csv(out / "safety_monitor.csv")
    print("violated share:\n" + stl["violated"].unstack("spec").to_string())
    print(f"shield acted at {int(st.safety['intervened'].sum())} of {len(st.safety)} rebalances, "
          f"{int(st.safety['daily_cuts'].sum())} intra-period cuts, mean scale {st.safety['lam'].mean():.2f}")

# paired block bootstrap vs BTC: is the Sharpe difference distinguishable from zero?
block = 7 * bpd
rows = {}
for label, d in (("full", df), ("holdout", hold)):
    for c in [c for c in ("MAS", "MAS+STL", "MAS-H", "Naive avg", "EW long-only") if c in d]:
        pt, lo, hi = block_bootstrap_sharpe(d[c], ppy, block, ref=d["BTC"], n_boot=args.boot)
        rows[(label, c)] = {"Sharpe diff vs BTC": pt, "5%": lo, "95%": hi, "excludes 0": bool(lo > 0 or hi < 0)}
boot = pd.DataFrame(rows).T
boot.to_csv(out / "bootstrap_vs_btc.csv")
print(f"\npaired block bootstrap ({args.boot} draws, {block}-bar blocks), Sharpe(strategy) - Sharpe(BTC):")
print(boot.to_string())
print("\nyearly returns:")
print(yearly[[c for c in ("BTC", "MAS", "MAS+STL", "MAS-H", "Naive avg", "EW long-only") if c in yearly]].to_string())

plots.equity_curves(df, out / "equity.png", f"{args.bar} / {args.universe} - growth of $1 (log), net of costs and funding")
print(f"\nwritten to {out}/")
