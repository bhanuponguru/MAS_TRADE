"""Main backtest: python run_backtest.py [--refresh] [--mode wmsr|admm]"""
import argparse
from dataclasses import replace
from pathlib import Path

import pandas as pd

from mas_trade import plots
from mas_trade.agents import default_agents
from mas_trade.backtest import run_backtest
from mas_trade.config import Config
from mas_trade.data import load_returns
from mas_trade.metrics import metrics_table

ap = argparse.ArgumentParser()
ap.add_argument("--refresh", action="store_true", help="re-download prices")
ap.add_argument("--mode", default="wmsr", choices=["wmsr", "admm"])
args = ap.parse_args()

cfg = Config(mode=args.mode)
rets, bench = load_returns(cfg, refresh=args.refresh)
res = run_backtest(rets, cfg, default_agents(), benchmark=bench)
hres = run_backtest(rets, replace(cfg, hierarchical=True), default_agents(), benchmark=bench)
res.returns["MAS-H"] = hres.returns["MAS"]
res.turnover["MAS-H"] = hres.turnover["MAS"]

out = Path("results")
out.mkdir(exist_ok=True)
tab = metrics_table(res.returns, res.turnover)
tab.to_csv(out / "metrics.csv")
res.capital.to_csv(out / "capital.csv")
res.trust.to_csv(out / "trust.csv")
res.weights.to_csv(out / "system_weights.csv")

pd.options.display.float_format = "{:.3f}".format
print(f"Universe: {len(cfg.tickers)} stocks, {res.returns.index[0].date()} -> "
      f"{res.returns.index[-1].date()}, mode={cfg.mode}, F={cfg.F}, K={cfg.K}")
print(tab.sort_values("Sharpe", ascending=False))
print(f"\nmean spectral gap of W: {res.spectral_gaps.mean():.3f}")
print("capital share, first -> last day:")
share = res.capital.div(res.capital.sum(axis=1), axis=0)
print(pd.DataFrame({"first": share.iloc[0], "last": share.iloc[-1]}))

plots.equity_curves(res.returns, out / "equity_curves.png")
plots.capital_area(res.capital, out / "capital_by_agent.png")
plots.heatmap(res.trust, out / "trust_scores.png", "Trust score s_i (normalised) per rebalance")
plots.heatmap(res.weights, out / "system_weights.png", "System weights (+long / -short)", center_zero=True)
plots.consensus_convergence(res.disagreement, out / "consensus_convergence.png")
last = list(res.W_hist)[-1]
plots.matrix_snapshot(res.W_hist[last], list(res.trust.columns), out / "consensus_matrix.png",
                      f"Consensus matrix W at {last.date()}")
names = list(hres.capital.columns)
last_h = list(hres.sub_capital)[-1]
print("\nhierarchical: top subagent budget share per strategy at the last rebalance")
for i, n in enumerate(names):
    g = hres.sub_capital[last_h][i] / hres.sub_capital[last_h][i].sum()
    print(f"  {n:14s} {rets.columns[g.argmax()]:6s} {g.max():.2f}  (equal share = {1 / len(g):.2f})")
hres.capital.to_csv(out / "capital_hier.csv")
plots.sub_capital_heatmap(hres.sub_capital[last_h], names, list(rets.columns), out / "sub_capital_heatmap.png",
                          f"Budget share of asset subagents inside each strategy at {last_h.date()}")
plots.sub_capital_area(hres.sub_capital, list(rets.columns), 0, names[0], out / "sub_capital_area.png")
print(f"\nplots + csv written to {out}/")
