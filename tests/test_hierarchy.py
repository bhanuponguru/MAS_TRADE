from dataclasses import replace

import numpy as np

from mas_trade.agents import default_agents
from mas_trade.backtest import run_backtest
from mas_trade.consensus import complete_graph
from mas_trade.forecasting import prob_positive
from mas_trade.hierarchy import auto_eta, reallocate_budgets, sub_graph, sub_trust

from test_backtest import CFG, make_returns

HCFG = replace(CFG, hierarchical=True)


def test_budgets_conserve_row_sums_and_respect_floor():
    rng = np.random.default_rng(0)
    G = rng.uniform(1, 5, (3, 6))
    c_new = np.array([30.0, 10.0, 60.0])
    S = rng.uniform(0.01, 1, (3, 6))
    out = reallocate_budgets(G, c_new, S, complete_graph(6), 0.5, 0.05)
    assert np.allclose(out.sum(1), c_new)
    assert (out >= 0.05 * c_new[:, None] - 1e-9).all()


def test_budgets_flow_to_trust_on_complete_graph():
    s = np.array([[0.2, 0.4, 0.9, 0.5]])
    G = np.full((1, 4), 25.0)
    for _ in range(60):
        G = reallocate_budgets(G, np.array([100.0]), s, complete_graph(4), 0.5, 0.0)
    assert np.allclose(G[0], s[0] / s[0].sum() * 100, rtol=1e-3)


def test_frozen_strategy_skips_level_two():
    x = np.array([[0.5, -0.5, 0.0], [1.0, 0.0, 0.0]])
    out = reallocate_budgets(np.ones((2, 3)), np.array([10.0, 20.0]), np.full((2, 3), 0.5),
                             complete_graph(3), 0.5, 0.0, frozen=np.array([True, False]), x=x)
    assert np.allclose(out[0], [5, 5, 0]) and np.isclose(out[1].sum(), 20.0)


def test_sub_trust_range_and_flipped_side():
    rng = np.random.default_rng(1)
    win = rng.normal(0.0005, 0.01, (252, 4))
    mu = np.full((2, 4), 0.001)
    hist = rng.normal(0.0005, 0.01, (100, 2, 4))
    agree = sub_trust(mu, np.ones((2, 4)), win, hist, 21, 63)
    flip = sub_trust(mu, -np.ones((2, 4)), win, hist, 21, 63)
    assert ((agree > 0) & (agree <= 1)).all() and (flip < agree).all()
    short = sub_trust(mu, np.ones((2, 4)), win, hist[:5], 21, 63)  # too little history -> p_track = 1
    assert np.allclose(short, prob_positive(mu, win.std(0)[None, :], 21))


def test_sub_graph_corr_has_self_loops():
    win = np.random.default_rng(2).normal(size=(200, 5))
    adj = sub_graph(win, "corr", 0.99)
    assert np.array_equal(adj, np.eye(5))


def test_hierarchical_backtest_consistency():
    rets = make_returns()
    res = run_backtest(rets, replace(HCFG, cost_bps=0.0), default_agents())
    assert res.sub_capital and res.sub_trust
    # level 1 is the sum of level 2; reallocation conserves the total
    cap_dates = list(res.capital.index)
    for d, G in list(res.sub_capital.items())[1:]:
        prev = cap_dates[cap_dates.index(d) - 1]
        assert np.isclose(G.sum(), res.capital.loc[prev].sum())
    equity = res.capital.sum(axis=1)
    implied = 1e6 * (1 + res.returns["MAS"]).cumprod()
    assert np.allclose(equity.values, implied.values, rtol=1e-9)
    assert (res.capital.div(equity, axis=0) >= CFG.c_min - 1e-9).all().all()


def test_hierarchical_weights_bounded_and_two_sided():
    res = run_backtest(make_returns(), HCFG, default_agents())
    assert (res.weights.values < 0).any() and (res.weights.values > 0).any()
    assert (res.weights.abs().sum(axis=1) <= 1 + 1e-9).all()


def test_hierarchical_no_lookahead():
    rets = make_returns()
    cut = 500
    base = run_backtest(rets, HCFG, default_agents())
    alt = rets.copy()
    alt.iloc[cut:] = np.random.default_rng(9).normal(0.0, 0.05, alt.iloc[cut:].shape)
    new = run_backtest(alt, HCFG, default_agents())
    dates = [d for d in base.weights.index if rets.index.get_loc(d) <= cut]
    assert len(dates) > 10
    assert np.allclose(base.weights.loc[dates], new.weights.loc[dates])
    for d in dates:
        assert np.allclose(base.sub_trust[d], new.sub_trust[d])
        assert np.allclose(base.sub_capital[d], new.sub_capital[d])


def test_auto_eta_responds_to_risk_and_cost():
    rng = np.random.default_rng(3)
    win = rng.normal(0, 1, (252, 4)) * np.array([0.005, 0.01, 0.02, 0.04])
    e = auto_eta(win.var(0), 21, 3.0, 5.0)
    assert (np.diff(e) > 0).all() and ((e > 0) & (e < 1)).all()          # riskier asset -> faster
    assert (auto_eta(win.var(0), 21, 3.0, 20.0) < e).all()                      # costlier trading -> slower
    assert np.allclose(auto_eta(win.var(0), 21, 3.0, 0.0), 1.0)                 # free trading -> jump to target


def test_vector_eta_conserves_and_matches_scalar():
    rng = np.random.default_rng(4)
    g, s = rng.uniform(1, 5, 6), rng.uniform(0.1, 1, 6)
    from mas_trade.capital import reallocate_capital
    from mas_trade.consensus import trust_matrix
    W = trust_matrix(complete_graph(6), s)
    v = reallocate_capital(g, W, rng.uniform(0.1, 0.9, 6), 0.0)
    assert np.isclose(v.sum(), g.sum())
    assert np.allclose(reallocate_capital(g, W, np.full(6, 0.4), 0.0), reallocate_capital(g, W, 0.4, 0.0))


def test_auto_eta_backtest_runs():
    res = run_backtest(make_returns(), replace(HCFG, eta_sub="auto"), default_agents())
    assert np.isfinite(res.returns["MAS"]).all()


def test_auto_eta_strategy_level_runs_flat_and_hierarchical():
    for h in (False, True):
        res = run_backtest(make_returns(), replace(CFG, hierarchical=h, eta="auto"), default_agents())
        assert np.isfinite(res.returns["MAS"]).all()
        assert (res.capital.div(res.capital.sum(axis=1), axis=0) >= CFG.c_min - 1e-9).all().all()


def test_vector_eta_all_ones_is_plain_transpose_step():
    from mas_trade.capital import reallocate_capital
    from mas_trade.consensus import trust_matrix
    g, s = np.array([1.0, 2.0, 3.0, 4.0]), np.array([0.2, 0.4, 0.6, 0.8])
    W = trust_matrix(complete_graph(4), s)
    out = reallocate_capital(g, W, np.ones(4), 0.0)  # free trading: jump straight to the target
    assert np.isfinite(out).all() and np.allclose(out, W.T @ g)
