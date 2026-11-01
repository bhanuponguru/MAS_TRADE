"""v2 benchmark in ABSOLUTE terms (no BTC-relative score): signal IC, each book alone, combiners, with a P&L
decomposition, Sharpe tested against 0, regime split and a deflated Sharpe over all logged trials.

python run_v2_benchmark.py --bar 1d|4h|1h [--universe broad|majors] [--eval-from 2022-01-13] [--unseal]

Development period only unless --unseal (the last cfg.holdout_months are sealed; unsealing is logged).
Outputs: results/v2/<bar>_<universe>/ and the append-only results/v2/trials.jsonl.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from mas_trade.config import V2Config
from mas_trade.metrics import block_bootstrap_sharpe, extended_stats, split_holdout, yearly_returns
from mas_trade.v2 import combiners as cb
from mas_trade.v2.agents import default_v2_agents
from mas_trade.v2.books import build_books
from mas_trade.v2.diagnostics import (decompose, deflated_sharpe, ic_table, log_trial, read_trials,
                                      regime_labels, regime_table)
from mas_trade.v2.execute import execute
from mas_trade.v2.smooth import smooth_books
from mas_trade.v2.panel import load_crypto_panel

ap = argparse.ArgumentParser()
ap.add_argument("--bar", default="1d", choices=["1d", "4h", "1h"])
ap.add_argument("--universe", default="broad", choices=["broad", "majors"])
ap.add_argument("--eval-from", default=None)
ap.add_argument("--boot", type=int, default=1000)
ap.add_argument("--unseal", action="store_true")
ap.add_argument("--smooth", action="store_true", help="cost-aware partial adjustment of every weight path")
args = ap.parse_args()

cfg = V2Config.for_tier(args.bar)
P = load_crypto_panel(args.bar, args.universe)
bs = build_books(P, cfg, default_v2_agents())
print(f"{args.bar}/{args.universe}: {len(P.dates)} bars x {len(P.tickers)} symbols, {len(bs.rebal)} rebalances, "
      f"trading from {P.dates[bs.rebal[bs.k0]].date()}, ppy={cfg.ppy:.0f}, H={cfg.rebal_bars} bars")

if args.smooth:
    bs = smooth_books(bs, P, cfg)    # every book is executed cost-aware before it is mixed
runs = {n: execute(P, bs, cb.single_book(bs, cfg, a), cfg) for a, n in enumerate(bs.names)}
for name, fn in (("EW", cb.equal_weight), ("InvVol", cb.inverse_vol), ("Hedge", cb.hedge_only),
                 ("RiskBudget", cb.risk_budget_only), ("Hedge+RB", cb.hedge_risk_budget)):
    runs[name] = execute(P, bs, fn(bs, cfg), cfg)
runs["C3-xs"] = execute(P, bs, cb.view_fusion(bs, P, cfg), cfg)
runs["C3+Timing"] = execute(P, bs, cb.view_fusion(bs, P, cfg, timing_weight=0.5), cfg)
runs["C3-xs (full cov)"] = execute(P, bs, cb.view_fusion(bs, P, cfg, cov="lw"), cfg)

nets = pd.DataFrame({k: r.net for k, r in runs.items()})
nets["BTC (context)"] = pd.Series(P.btc, index=P.dates).reindex(nets.index)
if args.eval_from:
    nets = nets.loc[args.eval_from:]
cut = nets.index[-1] - pd.DateOffset(months=cfg.holdout_months)
dev = nets if args.unseal else nets.loc[nets.index < cut]
print(f"evaluating {dev.index[0].date()} -> {dev.index[-1].date()} ({len(dev)} bars)" + ("  [HOLDOUT UNSEALED]" if args.unseal else "  [holdout sealed]"))
end_bar = len(P.dates) if args.unseal else P.dates.get_indexer([dev.index[-1]])[0] + 1

pd.options.display.float_format = "{:.3f}".format
pd.options.display.width = 220
out = Path("results/v2") / f"{args.bar}_{args.universe}{'_common' if args.eval_from else ''}{'_smooth' if args.smooth else ''}"
out.mkdir(parents=True, exist_ok=True)

ic = ic_table(bs, P, end=end_bar)
print("\n=== signal quality: rank-IC of each agent's score vs realised forward return (cross-sectional) ===")
print(ic.to_string())
ic.to_csv(out / "ic.csv")

sl = slice(None)
stats = pd.DataFrame({c: extended_stats(dev[c], cfg.ppy) for c in dev}).T.drop(columns=["HitRate"])
rows = {}
for c in [c for c in dev if c in runs]:
    ex = runs[c]
    sub = lambda s: s.loc[dev.index[0]:dev.index[-1]]
    comp = {"market": sub(ex.market).mean() * cfg.ppy, "selection": sub(ex.selection).mean() * cfg.ppy,
            "funding": sub(ex.funding).mean() * cfg.ppy, "cost": -sub(ex.cost).mean() * cfg.ppy}
    comp["sum"] = sum(comp.values())
    comp["netExp"] = sub(ex.exposure).mean()
    comp["gross"] = sub(ex.gross).mean()
    pt, lo, hi = block_bootstrap_sharpe(dev[c], cfg.ppy, 7 * cfg.bpd, n_boot=args.boot)
    comp.update({"Sharpe5%": lo, "Sharpe95%": hi, "Turnover": ex.turnover})
    rows[c] = comp
stats = stats.join(pd.DataFrame(rows).T)
print("\n=== absolute performance (net of fees, impact, funding; annualised arithmetic P&L components) ===")
print(stats.to_string())
stats.to_csv(out / "absolute.csv")

lab = regime_labels(P.btc, cfg.bpd, P.dates)
reg = {c: regime_table(dev[[c]], lab, cfg.ppy)[c] for c in dev if c in runs}
rt = pd.DataFrame(reg)
rt["bars"] = regime_table(dev[[dev.columns[0]]], lab, cfg.ppy)["bars"]
print("\n=== annualised Sharpe by regime (BTC 90d trend / vol vs expanding median) ===")
print(rt.to_string())
rt.to_csv(out / "regimes.csv")
yearly = yearly_returns(dev)
print("\nyearly returns:")
print(yearly.to_string())
yearly.to_csv(out / "yearly.csv")

# multiple-testing control: every variant evaluated is logged; DSR is over all logged trials
tp = Path("results/v2/trials.jsonl")
for c in runs:
    r = dev[c]
    log_trial(tp, bar=args.bar, universe=args.universe, name=c, sharpe_ann=extended_stats(r, cfg.ppy)["Sharpe"],
              bars=len(r), unsealed=args.unseal, smooth="books" if args.smooth else False)
tr = read_trials(tp)
sr_p = tr["sharpe_ann"].astype(float) / np.sqrt(cfg.ppy)
print(f"\ndeflated Sharpe (P[true Sharpe > best of {len(tr)} logged trials by chance]):")
dsr = {}
for c in runs:
    r = dev[c].dropna()
    sr = r.mean() / r.std()
    dsr[c] = deflated_sharpe(sr, len(tr), float(sr_p.var()), float(r.skew()), float(r.kurt() + 3), len(r))
print(pd.Series(dsr).to_string())
print(f"\nwritten to {out}/")
