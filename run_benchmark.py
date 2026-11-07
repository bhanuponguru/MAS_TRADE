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
from mas_trade.agents.momentum import TimedMomentum, TimeSeriesMomentum
from mas_trade.config import EngineConfig
from mas_trade.diagnostics import log_trial
from mas_trade.engine import run_engine
from mas_trade.metrics import block_bootstrap_sharpe, extended_stats, yearly_returns
from mas_trade.panel import load_crypto_panel

AGENTS = {"RankCarry": RankCarry, "TSMomentum": TimeSeriesMomentum, "TSMomentumTimed": TimedMomentum}

ap = argparse.ArgumentParser()
ap.add_argument("--bar", default="1d", choices=["1d", "4h", "1h"])
ap.add_argument("--universe", default="broad", choices=["broad", "majors"])
ap.add_argument("--agents", nargs="+", default=["RankCarry"], choices=list(AGENTS))
ap.add_argument("--unseal", action="store_true")
ap.add_argument("--boot", type=int, default=1000)
ap.add_argument("--label", default=None, help="name of this variant in the trial log")
ap.add_argument("--tag", default=None, help="output folder name under results/ (default: bar_universe_agents)")
args = ap.parse_args()

cfg = EngineConfig.for_tier(args.bar)
P = load_crypto_panel(args.bar, args.universe)
cut = P.dates[-1] - pd.DateOffset(months=cfg.holdout_months)
end = len(P.dates) if args.unseal else int((P.dates < cut).sum())
agents = [AGENTS[a]() for a in args.agents]
res = run_engine(P, agents, cfg, end=end)
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
                 "cells not converged": res.unconverged, "worst unconverged residual": max(res.residuals, default=0.0)}).round(3).to_string())
print("\nannualised P&L components:")
print(ann.drop("net").round(4).to_string(), "\n(sum", round(float(ann[["market", "selection", "funding", "cost"]].sum()), 4), ")")
acc = pd.DataFrame(res.account, index=res.dates, columns=res.names)
equity_prev = 1.0 + np.r_[0.0, np.cumsum(acc.sum(1).values)[:-1]]
acc_ret = acc.div(equity_prev, axis=0)                          # each account's return on system equity (they add up to net)
print("\nper-agent account P&L (annualised, units of initial equity), ex-ante Sharpe at its belief, mean gross, final wealth share:")
print(pd.DataFrame({"pnl": acc.mean() * cfg.ppy, "ex-ante Sharpe": np.mean(res.exante, axis=0), "gross": np.mean(res.agent_gross, axis=0),
                    "wealth share": res.wealth[-1] / res.wealth[-1].sum()}).round(3).to_string())
print(f"specs: coin beliefs zeroed by the sanity spec {res.sanitized}; calibration multiplier min {np.min(res.kelly_scales):.2f}; "
      f"volatility limit binding at {np.mean(np.array(res.vol_price) > 0):.0%} of rebalances")
print("\nrealised skill of each agent (rank IC for cross-sectional agents, pooled slope of returns on the signal for time-series ones), dev:")
print(pd.DataFrame({a.name: a.skill_summary() for a in agents}).T.round(3).to_string())
print("\nyearly returns:")
print(yearly_returns(net.to_frame("net")).round(3).to_string())

out = Path("results") / (args.tag or f"{args.bar}_{args.universe}_{'+'.join(args.agents)}")
out.mkdir(parents=True, exist_ok=True)
bars.assign(btc=btc, **{f"acc_{c}": acc_ret[c] for c in acc_ret}).to_csv(out / "bars.csv")
log_trial(Path("results/trials.jsonl"), bar=args.bar, universe=args.universe, name=args.label or "+".join(args.agents),
          sharpe_ann=st["Sharpe"], bars=len(net), unsealed=args.unseal)
print(f"\nwritten to {out}/")
