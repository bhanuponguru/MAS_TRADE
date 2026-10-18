from dataclasses import replace

import numpy as np
import pandas as pd

from mas_trade.agents import default_agents
from mas_trade.backtest import run_backtest
from mas_trade.config import Config


def make_returns(n=700, N=6, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2018-01-01", periods=n)
    return pd.DataFrame(rng.normal(0.0004, 0.01, (n, N)), index=idx, columns=[f"S{i}" for i in range(N)])


CFG = Config(lookback=60, warmup=60, rebalance_days=10, trust_window=60, trust_halflife=30)


def test_no_lookahead():
    rets = make_returns()
    cut = 500
    base = run_backtest(rets, CFG, default_agents())
    alt = rets.copy()
    alt.iloc[cut:] = np.random.default_rng(9).normal(0.0, 0.05, alt.iloc[cut:].shape)  # rewrite the future
    new = run_backtest(alt, CFG, default_agents())
    dates = [d for d in base.weights.index if rets.index.get_loc(d) <= cut]
    assert len(dates) > 10
    assert np.allclose(base.weights.loc[dates], new.weights.loc[dates])
    assert np.allclose(base.trust.loc[dates], new.trust.loc[dates])


def test_capital_total_only_changes_by_pnl_and_costs():
    rets = make_returns()
    res = run_backtest(rets, replace(CFG, cost_bps=0.0), default_agents())
    # with no costs, system equity must equal the compounded system return series
    equity = res.capital.sum(axis=1)
    implied = 1e6 * (1 + res.returns["MAS"]).cumprod()
    assert np.allclose(equity.values, implied.values, rtol=1e-9)
    assert (res.capital.div(equity, axis=0) >= CFG.c_min - 1e-9).all().all()


def test_weights_are_long_short_and_bounded():
    res = run_backtest(make_returns(), CFG, default_agents())
    assert (res.weights.values < 0).any() and (res.weights.values > 0).any()
    assert (res.weights.abs().sum(axis=1) <= 1 + 1e-9).all()


def test_admm_mode_runs():
    res = run_backtest(make_returns(), replace(CFG, mode="admm"), default_agents())
    assert np.isfinite(res.returns["MAS"]).all()
