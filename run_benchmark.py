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
from mas_trade.agents.momentum import TimeSeriesMomentum
from mas_trade.agents.reversal import RankReversal
from mas_trade import supervisor
from mas_trade.config import EngineConfig
from mas_trade.diagnostics import log_trial
from mas_trade.engine import run_engine
from mas_trade.metrics import block_bootstrap_sharpe, extended_stats, yearly_returns
from mas_trade.panel import load_crypto_panel

AGENTS = {"RankCarry": RankCarry, "TSMomentum": TimeSeriesMomentum, "RankReversal": RankReversal}

ap = argparse.ArgumentParser()
ap.add_argument("--bar", default="1d", choices=["1d", "4h", "1h"])
ap.add_argument("--universe", default="broad", choices=["broad", "majors"])
ap.add_argument("--agents", nargs="+", default=["RankCarry"],
                help=f"agents, each NAME or NAME:DAYS for a window variant (e.g. RankCarry:7); NAME in {list(AGENTS)}")
ap.add_argument("--unseal", action="store_true")
ap.add_argument("--boot", type=int, default=1000)
ap.add_argument("--label", default=None, help="name of this variant in the trial log")
ap.add_argument("--tag", default=None, help="output folder name under results/ (default: bar_universe_agents)")
ap.add_argument("--consensus", default="hub", choices=["hub", "graph"], help="joint solver: one hub, or neighbours only (decision 0042)")
ap.add_argument("--topology", default="complete", help="agent graph when --consensus graph: complete, ring, line, star, random")
ap.add_argument("--rounds", type=int, default=1, help="gossip rounds per ADMM iteration (graph only)")
ap.add_argument("--iters", type=int, default=None, help="cap on solver iterations per solve (communication budget); default the solver's")
ap.add_argument("--link-fail", type=float, default=0.0, help="graph only: probability that an edge is down in a gossip round (experiment 021)")
ap.add_argument("--offline", nargs=3, action="append", default=[], metavar=("AGENT", "FIRST", "LAST"),
                help="agent AGENT is offline from day FIRST to day LAST (YYYY-MM-DD); repeatable (experiment 021)")
ap.add_argument("--faulty", nargs="+", default=[], help="agent names that misbehave: hold nothing, send false values in graph mode")
ap.add_argument("--attack", type=float, default=0.0, help="what a faulty agent adds to every value it sends")
ap.add_argument("--faulty-window", nargs=2, default=(), metavar=("FIRST", "LAST"), help="the faulty agents misbehave only between these days")
ap.add_argument("--attack-kind", default="constant", choices=["constant", "noise"])
ap.add_argument("--safety", default="off", choices=["off", "derisk", "hold", "both"], help="safety supervisor (decision 0044)")
ap.add_argument("--detect", type=int, default=0, help="graph only: detect and isolate a misbehaving agent after this many iterations")
args = ap.parse_args()

cfg = EngineConfig.for_tier(args.bar, consensus=args.consensus, topology=args.topology, gossip_rounds=args.rounds,
                            link_fail=args.link_fail, offline=tuple(tuple(o) for o in args.offline), faulty=tuple(args.faulty),
                            attack=args.attack, detect=args.detect,
                            faulty_window=tuple(args.faulty_window), attack_kind=args.attack_kind, safety=args.safety)
P = load_crypto_panel(args.bar, args.universe)
cut = P.dates[-1] - pd.DateOffset(months=cfg.holdout_months)
end = len(P.dates) if args.unseal else int((P.dates < cut).sum())
def make_agent(spec):
    name, _, days = spec.partition(":")
    if name not in AGENTS:
        ap.error(f"unknown agent {name!r}")
    if not days:
        return AGENTS[name]()
    ag = AGENTS[name](days=float(days))
    ag.name = f"{ag.name}{days}"                                   # distinct names for the per-agent tables
    return ag


agents = [make_agent(a) for a in args.agents]
res = run_engine(P, agents, cfg, end=end, solver=None if args.iters is None else {"iters": args.iters})
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
                 "cells not converged": res.unconverged, "solver iterations (mean)": float(np.mean(res.iters)) if res.iters else 0.0, "worst unconverged residual": max(res.residuals, default=0.0)}).round(3).to_string())
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
for a in agents:
    if hasattr(a, "liquidity_summary"):
        print(f"\n{a.name} diagnostic, rank IC by liquidity tercile: " + ", ".join(f"{k}: {v:.3f}" for k, v in a.liquidity_summary().items()))
print("\nyearly returns:")
print(yearly_returns(net.to_frame("net")).round(3).to_string())

out = Path("results") / (args.tag or f"{args.bar}_{args.universe}_{'+'.join(args.agents)}")
out.mkdir(parents=True, exist_ok=True)
bars.assign(btc=btc, **{f"acc_{c}": acc_ret[c] for c in acc_ret}).to_csv(out / "bars.csv")
if res.iters:                                                   # per rebalance: solver work, risk and isolation (experiments 020-021)
    pd.DataFrame({"date": P.dates[res.solved], "iterations": res.iters, "sys_vol": res.sys_vol,
                  "isolated": [" ".join(res.names[i] for i in q) for q in res.isolated], "converged": res.converged,
                  "rel_res": res.rel_res, "dd_scale": res.dd_scale, "held": res.held}).to_csv(out / "rebal.csv", index=False)
    rec = supervisor.safety_record(res, cfg)                    # STL safety monitor (decision 0044)
    rec.to_csv(out / "safety.csv")
    print("\nSTL safety record (robustness > 0 = satisfied; windows = stress periods, decision 0044):")
    print(supervisor.window_summary(rec, ppy=cfg.ppy).round(3).to_string())
if cfg.faulty or cfg.detect or cfg.offline or cfg.link_fail:
    first = next((k for k, q in enumerate(res.isolated) if q), None)
    print(f"resilience: isolated at the end {[res.names[i] for i in res.isolated[-1]] if res.isolated else []}; "
          f"first isolation at solve {first} of {len(res.isolated)}")
log_trial(Path("results/trials.jsonl"), bar=args.bar, universe=args.universe, name=args.label or "+".join(args.agents),
          sharpe_ann=st["Sharpe"], bars=len(net), unsealed=args.unseal)
print(f"\nwritten to {out}/")
