from dataclasses import replace

import numpy as np
import pandas as pd

from mas_trade.agents.carry import RankCarry
from mas_trade.config import EngineConfig
from mas_trade.engine import run_engine
from mas_trade.panel import make_panel

CFG = EngineConfig(bpd=1, rebal_bars=5, hist_days=60, cov_days=30, beta_days=30, adv_days=10, burn_days=20, min_adv=1.0)


def make_panel_synth(n=400, N=20, seed=0, drift=None, strength=0.0004, effect_sign=1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="D", tz="UTC")
    cols = ["BTCUSDT"] + [f"S{i}" for i in range(N - 1)]
    btc = rng.normal(0.0005, 0.03, n)
    r = 0.8 * btc[:, None] + rng.normal(0, 0.03, (n, N))
    r[:, 0] = btc
    fund = np.zeros((n, N))
    if drift is not None:                                   # coins with low funding earn more: a planted carry effect
        fund = (-drift * 1e-4)[None, :] + rng.normal(0, 1e-5, (n, N))
        r = r + (effect_sign * drift * strength)[None, :]
    rets = pd.DataFrame(r, index=idx, columns=cols)
    ones = pd.DataFrame(1.0, index=idx, columns=cols)
    vol = ones * (1e7 * rng.uniform(0.5, 2, N))
    return make_panel(rets, ones.astype(bool), pd.DataFrame(fund, index=idx, columns=cols), vol, pd.Series(btc, index=idx), 1)


def test_engine_accounting_invariants():
    P = make_panel_synth(n=300, N=12, drift=np.random.default_rng(1).normal(0, 1, 12))
    res = run_engine(P, [RankCarry(days=10), RankCarry(days=20)], CFG)
    equity = 1.0 + np.cumsum(res.account.sum(1))                  # initial equity + all account P&L (costs included)
    assert np.allclose(np.cumprod(1.0 + res.net), equity, atol=1e-9)
    assert np.isclose(res.wealth[-1].sum(), equity[-1], atol=1e-9)
    assert res.unconverged == 0 and (res.cost >= 0).all() and res.cost.sum() > 0
    at_rebalance = [t - res.rebal[0] for t in res.rebal if t - res.rebal[0] < len(res.gross)]
    assert (res.gross[at_rebalance] <= CFG.gross + 1e-2).all()


def test_engine_has_no_lookahead():
    drift = np.random.default_rng(2).normal(0, 1, 12)
    P1 = make_panel_synth(n=300, N=12, drift=drift)
    P2 = make_panel_synth(n=300, N=12, drift=drift)
    cut = 200
    P2.R[cut:] = np.random.default_rng(9).normal(0, 0.1, P2.R[cut:].shape)
    P2.F[cut:] = np.random.default_rng(10).normal(0, 1e-3, P2.F[cut:].shape)
    r1, r2 = run_engine(P1, [RankCarry()], CFG), run_engine(P2, [RankCarry()], CFG)
    for k, t in enumerate(r1.rebal):
        if t <= cut:
            assert np.array_equal(r1.targets[k][1], r2.targets[k][1])        # positions decided before the cut agree


def test_engine_measures_a_planted_carry_effect_and_keeps_the_agent_on():
    drift = np.random.default_rng(3).normal(0, 1, 12)
    P = make_panel_synth(n=400, N=12, drift=drift, strength=0.003)
    good = RankCarry(days=10)
    res = run_engine(P, [good], CFG)
    assert np.mean(good.ics) > 0.1 and not good.killed()                     # the effect is there and measured
    assert good.ic_hat() == RankCarry.ic_prior_mean                          # the belief scale stays the card's
    assert res.net.sum() > 0
    flat = make_panel_synth(n=400, N=12)                                      # no effect: not enough evidence to switch it off
    ag = RankCarry(days=10)
    run_engine(flat, [ag], CFG)
    assert not ag.killed() and ag.ic_hat() == RankCarry.ic_prior_mean


def test_engine_switches_off_a_hypothesis_whose_own_evidence_contradicts_it():
    drift = np.random.default_rng(4).normal(0, 1, 12)
    P = make_panel_synth(n=600, N=12, drift=drift, strength=0.003, effect_sign=-1)   # the effect has the opposite sign
    ag = RankCarry(days=10)
    res = run_engine(P, [ag], CFG)
    assert ag.killed() and ag.ic_hat() == 0.0
    gross = [np.abs(x).sum() for _, x in res.targets]
    assert gross[-1] < 0.25 * max(gross)                                      # quiet at the end: the book unwinds (at a cost), no opposite bet


def test_engine_respects_the_volatility_limit_ex_ante():
    drift = np.random.default_rng(5).normal(0, 1, 12)
    P = make_panel_synth(n=400, N=12, drift=drift, strength=0.003)
    res = run_engine(P, [RankCarry(days=10)], CFG)
    realised = np.std(res.net[30:]) * np.sqrt(P.ppy)
    assert realised < 3 * CFG.target_vol                        # ex-ante limit; realised vol is noisy but of the same order
    assert res.unconverged == 0


def test_volatility_limit_is_a_share_of_current_equity():
    """Positions are in initial-equity units and Kelly stakes grow with wealth; the limit must scale with equity, or a
    system that has doubled is held to half its mandate (the bug found on real data: realised vol fell from 20% to 8%)."""
    drift = np.random.default_rng(5).normal(0, 1, 12)
    P = make_panel_synth(n=500, N=12, drift=drift, strength=0.01)
    cfg = replace(CFG, target_vol=0.05)                                       # tight enough to bind
    res = run_engine(P, [RankCarry(days=10)], cfg)
    eq = res.wealth[1:len(res.sys_vol) + 1].sum(1)
    assert eq.max() > 1.5                                                     # equity has moved far from its start
    binding = np.array(res.vol_price) > 0
    assert binding.sum() >= 5
    v = np.array(res.sys_vol)[binding]
    assert abs(np.median(v) / cfg.target_vol - 1) < 0.03                    # held at the limit relative to equity ...
    assert (v > 0.85 * cfg.target_vol).all() and (v < 1.15 * cfg.target_vol).all()   # ... also late, when equity is ~3x


def test_kill_rule_acts_at_realistic_ic_not_only_extreme_ones():
    ag = RankCarry()
    assert ag.ic_hat() == RankCarry.ic_prior_mean                             # no evidence: the card's prior
    ag.ics = list(np.random.default_rng(0).normal(-0.04, 0.2, 300))           # a wrong-signed hypothesis at a realistic IC
    assert ag.killed() and ag.ic_hat() == 0.0
    ag.ics = list(np.random.default_rng(0).normal(0.035, 0.2, 140))           # the measured carry IC: stays on
    assert not ag.killed()
    ag.ics = [-0.3] * 10                                                      # too few periods to judge
    assert not ag.killed()


def test_time_series_agent_skill_summary_and_kill_rule():
    from mas_trade.agents.momentum import TimeSeriesMomentum
    ag = TimeSeriesMomentum()
    rng = np.random.default_rng(0)
    for _ in range(40):                                        # the signal has the WRONG sign against realised returns
        z = rng.normal(0, 1, 2)
        ag.record(z, -0.05 * z + rng.normal(0, 0.02, 2))
    s = ag.skill_summary()
    assert s["slope"] < 0 and s["t"] < -2 and ag.killed()
    ok = TimeSeriesMomentum()
    for _ in range(40):
        z = rng.normal(0, 1, 2)
        ok.record(z, 0.05 * z + rng.normal(0, 0.02, 2))
    assert ok.skill_summary()["t"] > 2 and not ok.killed()


def test_an_agent_only_holds_the_coins_of_its_card():
    from mas_trade.agents.momentum import TimeSeriesMomentum
    P = make_panel_synth(n=300, N=12, drift=np.random.default_rng(6).normal(0, 1, 12), strength=0.003)
    res = run_engine(P, [TimeSeriesMomentum(days=10)], CFG)
    allowed = {P.tickers.index(t) for t in TimeSeriesMomentum.universe if t in P.tickers}   # the synthetic panel has BTC only
    held = {int(j) for jj, x in res.targets for j, v in zip(jj, x[0]) if abs(v) > 1e-9}
    assert held and held <= allowed                              # no hedge positions in other coins


def test_reversal_signal_is_long_the_residual_losers_and_ignores_the_market_move():
    from mas_trade.agents.base import Ctx
    from mas_trade.agents.reversal import RankReversal
    rng = np.random.default_rng(1)
    T, n = 60, 6
    btc = rng.normal(0, 0.03, T)
    R = 1.0 * btc[:, None] + rng.normal(0, 0.01, (T, n))
    R[-7:, 0] -= 0.02                                       # coin 0 fell on its own over the last week
    R[-7:, 1] += 0.02                                       # coin 1 rose on its own
    ctx = Ctx(R, np.zeros((T, n)), np.ones((T, n)), btc, [f"C{i}" for i in range(n)], 1, np.full(n, 0.05))
    s = RankReversal().signal(ctx)
    assert s.argmax() == 0 and s.argmin() == 1
    ctx.R[-7:] += 0.05 * ctx.btc[-7:, None]                 # a market move that every coin shares changes nothing important
    assert RankReversal().signal(ctx).argmax() == 0


def test_reversal_agent_runs_in_the_engine_and_reports_its_liquidity_diagnostic():
    from mas_trade.agents.reversal import RankReversal
    P = make_panel_synth(n=300, N=24, seed=3)
    a = RankReversal()
    res = run_engine(P, [a], CFG)
    assert np.isfinite(res.net).all() and len(a.ics) > 10
    d = a.liquidity_summary()
    assert len(d) == 3 and all(np.isfinite(v) for v in d.values())
