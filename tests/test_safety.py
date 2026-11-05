from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from mas_trade import safety
from mas_trade.agents import default_agents
from mas_trade.backtest import run_backtest
from mas_trade.config import Config
from mas_trade.consensus import admm_consensus, central_mv

CFG = Config(lookback=60, warmup=60, rebalance_days=10, trust_window=60, trust_halflife=30,
             safety_dd_window=60, safety_vol_window=10, safety_recover=5)


def make_returns(n=700, N=6, seed=0, vol=0.01):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2018-01-01", periods=n)
    return pd.DataFrame(rng.normal(0.0004, vol, (n, N)), index=idx, columns=[f"S{i}" for i in range(N)])


# ------------------------------------------------------------ STL semantics
def test_temporal_operators_match_brute_force():
    rng = np.random.default_rng(1)
    x = rng.normal(size=40)
    n = len(x)
    for a, b in [(0, 0), (0, 3), (2, 5)]:
        fut = [x[t + a:min(t + b, n - 1) + 1] for t in range(n)]
        past = [x[max(t - b, 0):t - a + 1] if t - a >= 0 else np.array([]) for t in range(n)]
        assert np.allclose(safety.always(x, a, b), [f.min() if len(f) else np.inf for f in fut])
        assert np.allclose(safety.eventually(x, a, b), [f.max() if len(f) else -np.inf for f in fut])
        assert np.allclose(safety.historically(x, a, b), [p.min() if len(p) else np.inf for p in past])
        assert np.allclose(safety.once(x, a, b), [p.max() if len(p) else -np.inf for p in past])


def test_boolean_connectives_and_predicates():
    assert safety.le(0.1, 0.2) == pytest.approx(0.5)     # half the limit left
    assert safety.ge(-0.3, -0.15) == pytest.approx(-1.0)  # breach by one full limit
    a, b = np.array([1.0, -1.0]), np.array([-2.0, 3.0])
    assert np.allclose(safety.and_(a, b), [-2, -1]) and np.allclose(safety.or_(a, b), [1, 3])
    assert np.allclose(safety.implies(a, b), [-1, 3])


def test_recovery_spec_flags_only_long_breaches():
    cfg = replace(CFG, safety_max_vol=0.20, safety_recover=3)
    rho_vol = safety.le(np.array([0.1, 0.3, 0.3, 0.1, 0.3, 0.3, 0.3, 0.3, 0.3, 0.1]), cfg.safety_max_vol)
    rho_rec = safety.implies(safety.not_(rho_vol), safety.eventually(rho_vol, 0, cfg.safety_recover))
    assert (rho_rec[:4] > 0).all()                    # 2-bar breach recovers within 3 bars
    assert rho_rec[4] < 0                             # 5-bar breach: no recovery within [t, t+3]
    assert rho_rec[6] > 0                             # from here it does recover in time


# ------------------------------------------------------------ shield in the backtest
VARIANTS = [dict(safety_daily=False), dict(safety_daily=True)]   # D028: daily is the default


@pytest.mark.parametrize("hier", [False, True])
@pytest.mark.parametrize("variant", VARIANTS)
def test_no_lookahead_with_shield(variant, hier):
    rets = make_returns()
    cfg = replace(CFG, safety=True, safety_max_vol=0.05, hierarchical=hier, **variant)
    cut = 500
    base = run_backtest(rets, cfg, default_agents())
    alt = rets.copy()
    alt.iloc[cut:] = np.random.default_rng(9).normal(0.0, 0.05, alt.iloc[cut:].shape)
    new = run_backtest(alt, cfg, default_agents())
    dates = [d for d in base.weights.index if rets.index.get_loc(d) <= cut]
    assert base.safety.loc[dates, "intervened"].any()
    assert np.allclose(base.weights.loc[dates], new.weights.loc[dates])
    assert np.allclose(base.safety.loc[dates, "lam"], new.safety.loc[dates, "lam"])
    assert np.allclose(base.central_weights.loc[dates], new.central_weights.loc[dates])
    assert all(np.allclose(base.agent_weights[d], new.agent_weights[d]) for d in dates)


@pytest.mark.parametrize("hier", [False, True])
@pytest.mark.parametrize("variant", VARIANTS)
def test_shield_enforces_limits(variant, hier):
    cfg = replace(CFG, safety=True, safety_max_vol=0.04, safety_max_weight=0.15, hierarchical=hier, **variant)
    res = run_backtest(make_returns(vol=0.02), cfg, default_agents())
    assert (res.weights.abs().max(axis=1) <= cfg.safety_max_weight + 1e-9).all()
    assert (res.safety["rho_vol_post"] >= -1e-9).all() and (res.safety["rho_conc_post"] >= -1e-9).all()
    assert (res.safety["rho_vol"] < 0).any()          # the limits were binding before the shield


@pytest.mark.parametrize("hier", [False, True])
@pytest.mark.parametrize("variant", VARIANTS)
def test_shield_off_or_slack_changes_nothing(variant, hier):
    rets = make_returns()
    off = run_backtest(rets, replace(CFG, hierarchical=hier), default_agents())
    slack = replace(CFG, hierarchical=hier, safety=True, safety_max_vol=1e9, safety_max_weight=1e9, safety_max_dd=1e9,
                    **variant)
    on = run_backtest(rets, slack, default_agents())
    assert not on.safety["intervened"].any()
    pd.testing.assert_frame_equal(off.returns, on.returns)


@pytest.mark.parametrize("variant", VARIANTS)
def test_capital_identity_holds_with_shield(variant):
    cfg = replace(CFG, safety=True, safety_max_vol=0.05, cost_bps=0.0, **variant)
    res = run_backtest(make_returns(), cfg, default_agents())
    implied = 1e6 * (1 + res.returns["MAS"]).cumprod()
    assert np.allclose(res.capital.sum(axis=1).values, implied.values, rtol=1e-9)


def test_offline_evaluation_counts_episodes():
    idx = pd.bdate_range("2020-01-01", periods=60)
    r = pd.Series(0.0, index=idx)
    r.iloc[20] = -0.30                                  # one crash: drawdown breach that persists
    cfg = replace(CFG, safety_dd_window=10)
    traces, summary = safety.evaluate(r, cfg)
    # the 10-bar window (current bar included) still holds the pre-crash peak at bars 20..28
    assert summary.loc["phi_dd", "episodes"] == 1 and summary.loc["phi_dd", "longest"] == 9
    assert summary.loc["phi_dd", "robustness"] < 0


# ------------------------------------------------------------ centralised reference
def test_admm_converges_to_central_optimum():
    rng = np.random.default_rng(3)
    A, N = 5, 8
    w0 = rng.normal(size=(A, N))
    X = rng.normal(size=(200, N))
    Sig = np.cov(X.T)
    Sig = Sig / np.mean(np.diag(Sig)) + 1e-3 * np.eye(N)
    s = rng.uniform(0.2, 1.0, A)
    x, hist = admm_consensus(w0, Sig, s, gamma=1.0, rho=1.0, iters=500)
    xc = central_mv(w0, Sig, s, 1.0)
    assert np.abs(x - xc[None]).max() < 1e-6 * np.abs(xc).max()
    assert hist[-1] < 1e-12


# ------------------------------------------------------------ D028
def test_daily_checks_cut_inside_the_period_after_a_crash():
    rets = make_returns()
    rets.iloc[400:405] = -0.04                           # a crash in the middle of a holding period
    cfg = replace(CFG, safety=True, rebalance_days=20, safety_max_dd=0.10)
    reb = run_backtest(rets, replace(cfg, safety_daily=False), default_agents())
    day = run_backtest(rets, cfg, default_agents())
    assert reb.safety["daily_cuts"].sum() == 0 and day.safety["daily_cuts"].sum() > 0
    assert day.turnover["MAS"] > reb.turnover["MAS"]


def test_daily_is_the_default_when_the_shield_is_on():
    assert Config().safety_daily and not Config().safety


def test_consensus_spec_only_in_wmsr_mode():
    r = pd.Series(0.0, index=pd.bdate_range("2020-01-01", periods=30))
    dis = pd.Series([0.1, 0.2], index=r.index[[0, 10]])
    assert "phi_cons" in safety.evaluate(r, CFG, disagreement=dis)[1].index
    assert "phi_cons" not in safety.evaluate(r, replace(CFG, mode="admm"), disagreement=dis)[1].index


# ------------------------------------------------------------ 24/7 panel (listings, delistings, funding)
@pytest.mark.parametrize("hier", [False, True])
def test_shield_on_a_gappy_perp_panel(hier):
    rets = make_returns(N=8, vol=0.02)
    rets.iloc[:300, 6] = np.nan                          # listing
    rets.iloc[500:, 7] = np.nan                          # delisting
    fund = pd.DataFrame(0.0001, index=rets.index, columns=rets.columns)
    cfg = replace(CFG, safety=True, safety_max_vol=0.05, safety_max_weight=0.2, hierarchical=hier)
    res = run_backtest(rets, cfg, default_agents(), funding=fund)
    assert np.isfinite(res.returns["MAS"]).all() and res.safety["daily_cuts"].sum() > 0
    assert (res.weights.abs().max(axis=1) <= 0.2 + 1e-9).all()
    late = [d for d in res.weights.index if rets.index.get_loc(d) >= 501]
    assert (res.weights.loc[late, "S7"] == 0).all()       # nothing allocated to a delisted asset
