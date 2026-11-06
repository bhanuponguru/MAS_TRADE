"""Run the engine on real data, in ABSOLUTE terms: net Sharpe against zero, P&L decomposition, per-agent accounts.

python run_benchmark.py --bar 1d|4h|1h [--universe broad|majors] [--unseal] [--label NAME]

Development period only unless --unseal (the last cfg.holdout_months are sealed; unsealing is logged).
Every run is appended to results/trials.jsonl (the deflated Sharpe counts them).
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from mas_trade.agents.carry import RankCarry
from mas_trade.config import EngineConfig
from mas_trade.diagnostics import log_trial
from mas_trade.engine import run_engine
from mas_trade.metrics import block_bootstrap_sharpe, extended_stats, yearly_returns
from mas_trade.panel import load_crypto_panel

AGENTS = {"RankCarry": RankCarry}

ap = argparse.ArgumentParser()
ap.add_argument("--bar", default="1d", choices=["1d", "4h", "1h"])
ap.add_argument("--universe", default="broad", choices=["broad", "majors"])
ap.add_argument("--agents", nargs="+", default=["RankCarry"], choices=list(AGENTS))
ap.add_argument("--unseal", action="store_true")
ap.add_argument("--boot", type=int, default=1000)
ap.add_argument("--label", default=None, help="name of this variant in the trial log")
args = ap.parse_args()

cfg = EngineConfig.for_tier(args.bar)
P = load_crypto_panel(args.bar, args.universe)
cut = P.dates[-1] - pd.DateOffset(months=cfg.holdout_months)
end = len(P.dates) if args.unseal else int((P.dates < cut).sum())
res = run_engine(P, [AGENTS[a]() for a in args.agents], cfg, end=end)
print(f"{args.bar}/{args.universe}: {len(P.dates)} bars x {len(P.tickers)} symbols, H={cfg.rebal_bars} bars, "
      f"{res.dates[0].date()} -> {res.dates[-1].date()}" + ("  [HOLDOUT UNSEALED]" if args.unseal else "  [holdout sealed]"))

btc = pd.Series(P.btc, index=P.dates).reindex(res.dates).values
market = res.exposure * btc
bars = pd.DataFrame({"net": res.net, "price": res.price, "market": market, "selection": res.price - market,
                     "funding": res.funding, "cost": -res.cost}, index=res.dates)
net = bars["net"]
st = extended_stats(net, cfg.ppy)
lo, hi = block_bootstrap_sharpe(net, cfg.ppy, 7 * cfg.bpd, n_boot=args.boot)[1:]
ann = bars.mean() * cfg.ppy
print("\nabsolute performance (net of fees, impact and funding):")
print(pd.Series({**{k: st[k] for k in ("CAGR", "Vol", "Sharpe", "MaxDD", "Sortino", "Calmar")}, "Sharpe5%": lo, "Sharpe95%": hi,
                 "Turnover": res.turnover, "netExp": res.exposure.mean(), "gross": res.gross.mean(),
                 "cells not converged": res.unconverged}).round(3).to_string())
print("\nannualised P&L components:")
print(ann.drop("net").round(4).to_string(), "\n(sum", round(float(ann[["market", "selection", "funding", "cost"]].sum()), 4), ")")
acc = pd.DataFrame(res.account, index=res.dates, columns=res.names)
print("\nper-agent account P&L (annualised, units of initial equity) and final wealth share:")
print(pd.DataFrame({"pnl": acc.mean() * cfg.ppy, "wealth share": res.wealth[-1] / res.wealth[-1].sum()}).round(4).to_string())
print("\nyearly returns:")
print(yearly_returns(net.to_frame("net")).round(3).to_string())

out = Path("results") / f"{args.bar}_{args.universe}"
out.mkdir(parents=True, exist_ok=True)
bars.to_csv(out / "bars.csv")
log_trial(Path("results/trials.jsonl"), bar=args.bar, universe=args.universe, name=args.label or "+".join(args.agents),
          sharpe_ann=st["Sharpe"], bars=len(net), unsealed=args.unseal)
print(f"\nwritten to {out}/")
