import numpy as np
import pandas as pd

from mas_trade.agents.carry import RankCarry
from mas_trade.config import EngineConfig
from mas_trade.engine import run_engine
from mas_trade.panel import make_panel

CFG = EngineConfig(bpd=1, rebal_bars=5, hist_days=60, cov_days=30, beta_days=30, adv_days=10, burn_days=20, min_adv=1.0)


def make_panel_synth(n=400, N=20, seed=0, drift=None, strength=0.0004):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="D", tz="UTC")
    cols = ["BTCUSDT"] + [f"S{i}" for i in range(N - 1)]
    btc = rng.normal(0.0005, 0.03, n)
    r = 0.8 * btc[:, None] + rng.normal(0, 0.03, (n, N))
    r[:, 0] = btc
    fund = np.zeros((n, N))
    if drift is not None:                                   # coins with low funding earn more: a planted carry effect
        fund = (-drift * 1e-4)[None, :] + rng.normal(0, 1e-5, (n, N))
        r = r + (drift * strength)[None, :]
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


def test_engine_learns_a_planted_carry_effect():
    drift = np.random.default_rng(3).normal(0, 1, 12)
    P = make_panel_synth(n=400, N=12, drift=drift, strength=0.003)
    good = RankCarry(days=10)
    res = run_engine(P, [good], CFG)
    assert good.ic_hat() > 0.08
    flat = make_panel_synth(n=400, N=12)                                           # no effect: skill should stay near zero
    ag = RankCarry(days=10)
    run_engine(flat, [ag], CFG)
    assert 0.0 <= ag.ic_hat() < 0.04                 # no effect: it stays near the card's prior (0.02), never flips sign
    assert res.net.sum() > 0


def test_engine_respects_the_volatility_limit_ex_ante():
    drift = np.random.default_rng(5).normal(0, 1, 12)
    P = make_panel_synth(n=400, N=12, drift=drift, strength=0.003)
    res = run_engine(P, [RankCarry(days=10)], CFG)
    realised = np.std(res.net[30:]) * np.sqrt(P.ppy)
    assert realised < 3 * CFG.target_vol                        # ex-ante limit; realised vol is noisy but of the same order
    assert res.unconverged == 0


def test_rank_agent_does_not_flip_sign_on_a_bad_stretch():
    ag = RankCarry()
    ag.ics = [-0.3] * 30                                        # a long run of wrong-signed ICs
    assert ag.ic_hat() == 0.0                                   # goes quiet, does not bet the opposite
    ag.ics = []
    assert np.isclose(ag.ic_hat(), RankCarry.ic_prior_mean)     # no evidence: the card's prior
