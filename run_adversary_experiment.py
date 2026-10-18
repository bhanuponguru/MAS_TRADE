"""Resilience experiment: one compromised agent (random all-in bets) under plain vs W-MSR consensus."""
from dataclasses import replace
from pathlib import Path

import pandas as pd

from mas_trade import plots
from mas_trade.agents import AdversarialAgent, default_agents
from mas_trade.backtest import run_backtest
from mas_trade.config import Config
from mas_trade.data import load_returns
from mas_trade.metrics import metrics_table

cfg = Config()
rets, bench = load_returns(cfg)
runs = {
    "Clean (6 agents, W-MSR F=1)": (cfg, default_agents()),
    "Attacked, plain consensus F=0": (replace(cfg, F=0), default_agents() + [AdversarialAgent(cfg.seed)]),
    "Attacked, W-MSR F=1": (cfg, default_agents() + [AdversarialAgent(cfg.seed)]),
}
series, turnover = {bench.name: None}, {}
for name, (c, agents) in runs.items():
    res = run_backtest(rets, c, agents, benchmark=bench)
    series[name] = res.returns["MAS"]
    turnover[name] = res.turnover["MAS"]
    if "Attacked" in name:
        share = res.capital.iloc[-1] / res.capital.iloc[-1].sum()
        print(f"{name}: adversary capital share at end = {share['Adversary']:.3f}")
series[bench.name] = res.returns[bench.name]
df = pd.DataFrame(series)

pd.options.display.float_format = "{:.3f}".format
tab = metrics_table(df, turnover)
print(tab)
out = Path("results")
out.mkdir(exist_ok=True)
tab.to_csv(out / "adversary_metrics.csv")
plots.equity_curves(df, out / "adversary_equity.png", "Resilience to one adversarial agent")
