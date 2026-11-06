import numpy as np
import pytest

from mas_trade.attribution import allocate_cost
from mas_trade.cells_admm import CellProblem, solve_cells, solve_uncoupled
from mas_trade.market import MarketConfig, apply_floor, limited_liability, run_market
from mas_trade.simulate import kelly_growth, make_beliefs, make_world

F_KELLY = 0.5
SEEDS = range(20)


def _q(w):
    return w.N * w.sigma_alpha ** 2 / w.sigma_eps ** 2


def _run(world, beliefs, cfg=None):
    d, B, F = world.risk()
    return run_market(world.R, np.stack(beliefs), d, B, F, cfg or MarketConfig(kelly=np.full(len(beliefs), F_KELLY)))


def _horizon_skill_vs_noise():
    w = make_world(1)
    gap = kelly_growth(w, 0.3, 0.3, F_KELLY) - kelly_growth(w, 0.0, 0.3, F_KELLY)
    return int(np.ceil(3.0 / gap))


def test_uncoupled_admm_equals_the_closed_form_kelly_stake():
    w = make_world(1, N=12)
    d, B, F = w.risk()
    bel = np.stack([make_beliefs(w, 0.3, 0.3, seed=s)[0] for s in range(3)])
    p = CellProblem(mu=bel, gamma=1.0 / np.array([0.5, 0.3, 0.2]), d=d, H=np.zeros(12), B=B, F=F,
                    A=[np.column_stack([np.ones(12), B[:, 0]])] * 3)
    assert np.abs(solve_cells(p, tol=1e-10).x - solve_uncoupled(p)).max() < 1e-6


def test_l1_1_skilled_agents_gain_share():
    T = _horizon_skill_vs_noise()
    wins = 0
    for seed in SEEDS:
        w = make_world(T, seed=seed)
        r = _run(w, [make_beliefs(w, 0.3, 0.3, seed=100 + seed), make_beliefs(w, 0.0, 0.3, seed=200 + seed),
                     make_beliefs(w, 0.3, 0.3, seed=300 + seed)])
        wins += r.share[-1][[0, 2]].sum() > 0.5
    assert wins >= 0.9 * len(SEEDS), (wins, T)


def _l1_2_setup():
    w0 = make_world(1)
    g_cal, g_over = kelly_growth(w0, 0.3, 0.3, F_KELLY), kelly_growth(w0, 0.3, 0.3, F_KELLY, kappa=4.0)
    sd = lambda kappa: F_KELLY * kappa * 0.3 * np.sqrt(_q(w0))
    assert g_cal > g_over
    return int(np.ceil((1.3 * np.hypot(sd(1.0), sd(4.0)) / (g_cal - g_over)) ** 2))


def _pair(seed, T, cfg):
    w = make_world(T, seed=seed)
    return _run(w, [make_beliefs(w, 0.3, 0.3, seed=100 + seed), make_beliefs(w, 0.3, 0.3, kappa=4.0, seed=200 + seed)], cfg)


def test_l1_2_over_confidence_is_punished_without_a_floor():
    T = _l1_2_setup()
    cfg = MarketConfig(kelly=np.full(2, F_KELLY), floor=0.0)
    runs = [_pair(seed, T, cfg) for seed in SEEDS]
    wins = sum(r.wealth[-1][0] > r.wealth[-1][1] for r in runs)                  # system ruin counts as no win
    assert wins >= 0.9 * len(SEEDS), (wins, T)


@pytest.mark.xfail(strict=True, reason="experiment 012: a 2% wealth floor re-seeds and rebalances the ruined agent, so selection against "
                   "over-confidence is not reliable (14/20 seeds, 5 more are wiped out); the guard is the agent's calibration spec")
def test_l1_2_with_a_floor_the_over_confident_agent_keeps_a_minority_share():
    T = _l1_2_setup()
    cfg = MarketConfig(kelly=np.full(2, F_KELLY), floor=0.02)
    runs = [_pair(seed, T, cfg) for seed in SEEDS]
    wins = sum(r.wealth[-1].sum() > 0 and r.share[T // 2:, 1].mean() < 0.5 for r in runs)     # a wiped-out system is not a win
    assert wins >= 0.9 * len(SEEDS), (wins, T)


def test_l1_3_decayed_skill_loses_share():
    T = _horizon_skill_vs_noise()
    wins = 0
    for seed in SEEDS:
        w = make_world(2 * T, seed=seed)
        path = np.r_[np.full(T, 0.3), np.zeros(T)]
        r = _run(w, [make_beliefs(w, path, 0.3, seed=100 + seed), make_beliefs(w, 0.3, 0.3, seed=200 + seed),
                     make_beliefs(w, 0.0, 0.3, seed=300 + seed)])
        wins += r.share[-1][0] < r.share[T][0]
    assert wins >= 0.9 * len(SEEDS), (wins, T)


def test_l1_4_accounting_with_cost_netting_limits_and_floor():
    N, T = 16, 12
    w = make_world(T, N=N, seed=7)
    kappa = np.full(N, 0.05)
    cfg = MarketConfig(kelly=np.full(3, 0.5), floor=0.05, fee=5e-4, kappa=kappa, coupled=True, leverage=3.0, cap=0.5,
                       gross=4.0, beta_band=0.2)
    r = _run(w, [make_beliefs(w, 0.3, 0.3, seed=1), make_beliefs(w, 0.0, 0.3, seed=2), make_beliefs(w, 0.3, 0.3, kappa=4.0, seed=3)], cfg)
    assert np.abs(r.pnl.sum(1) - (r.real_pnl - r.real_cost)).max() < 1e-9          # accounts add up to the real P&L
    assert np.abs(r.stakes.sum(1) - r.net).max() < 1e-12                              # cells add up to the real position
    assert np.abs(r.wealth.sum(1) - r.equity).max() < 1e-9                            # wealths add up to real equity
    assert np.abs(r.cost.sum(1) - r.real_cost).max() < 1e-12 and (r.cost >= 0).all()
    assert (r.share >= cfg.floor - 1e-12).all()                                       # the floor holds
    assert r.real_cost.sum() > 0


def test_cost_allocation_sends_the_bill_to_the_agents_trading_with_the_net():
    prev = np.zeros((3, 2))
    new = np.array([[1.0, 0.0], [-0.4, 0.0], [0.6, 0.0]])                         # net +1.2: agents 0 and 2 pay, agent 1 crosses
    per, total = allocate_cost(prev, new, fee=0.0, kappa=np.array([0.1, 0.1]))
    assert np.isclose(total, 0.1 * 1.2 ** 1.5) and np.isclose(per.sum(), total)
    assert per[1] == 0 and np.isclose(per[0] / per[2], 1.0 / 0.6)


def test_limited_liability_covers_a_negative_account_from_the_others():
    w = limited_liability(np.array([-0.2, 0.8, 0.4]))
    assert np.isclose(w.sum(), 1.0) and w[0] == 0 and np.allclose(w[1:] / w[1:].sum(), [2 / 3, 1 / 3])


def test_wealth_floor_is_a_transfer_that_keeps_the_total():
    w = apply_floor(np.array([0.9, 0.09, 0.01]), 0.05)
    assert np.isclose(w.sum(), 1.0) and w.min() >= 0.05 - 1e-12 and np.isclose(w[2], 0.05)


def test_calibration_spec_removes_system_ruin_from_an_over_confident_agent():
    T = _l1_2_setup()
    ruined = 0
    for floor in (0.0, 0.02):
        cfg = MarketConfig(kelly=np.full(2, F_KELLY), floor=floor, calibration_floor=0.5)
        ruined += sum(_pair(seed, T, cfg).wealth[-1].sum() <= 0 for seed in range(10))
    assert ruined == 0                                   # without the spec 2 of 20 (no floor) and 5 of 20 (floor) seeds are wiped out
