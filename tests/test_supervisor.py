"""STL safety monitor and supervisor (decision 0044)."""
from dataclasses import replace

import numpy as np

from mas_trade import supervisor
from mas_trade.agents.carry import RankCarry
from mas_trade.engine import run_engine
from test_engine import CFG, make_panel_synth


def test_drawdown_scale_follows_the_mandate():
    cfg = CFG                                                   # dd_limit 0.15, buffer 0.5, floor 0.2 (decision 0026)
    flat = np.zeros(50)
    assert supervisor.drawdown_scale(flat, cfg) == 1.0
    def after(loss):                                            # one bar losing `loss` from the peak
        return supervisor.drawdown_scale(np.r_[np.zeros(10), -loss], cfg)
    assert np.isclose(after(0.075), 1.0)                        # half the budget left: not yet
    assert np.isclose(after(0.1125), 0.6)                       # a quarter left: halfway down
    assert np.isclose(after(0.15), 0.2) and np.isclose(after(0.4), 0.2)   # at or beyond the limit: the floor


def losing_run(safety):
    P = make_panel_synth(n=400, N=12, drift=np.random.default_rng(1).normal(0, 1, 12), strength=0.002, effect_sign=-1)
    return P, run_engine(P, [RankCarry(days=10), RankCarry(days=20)], replace(CFG, safety=safety, dd_days=120))


def test_derisk_shrinks_the_volatility_target_in_a_drawdown_and_uses_only_the_past():
    P, off = losing_run("off")
    _, on = losing_run("derisk")
    assert min(on.dd_scale) < 0.5 and max(off.dd_scale) == 1.0
    ratio = np.array(on.sys_vol) / (CFG.target_vol * np.array(on.dd_scale))   # volatility against the target in force
    assert np.median(ratio) <= 1.02 and ratio.max() <= 1.25                     # the price search is approximate (5 steps)
    assert np.std(on.net) < np.std(off.net)
    # no lookahead: the scale at a rebalance depends only on returns before it
    k = len(on.solved) // 2
    t = on.solved[k]
    net_abs = np.zeros(len(P.dates))
    net_abs[on.rebal[0]:on.rebal[0] + len(on.net)] = on.net
    assert np.isclose(on.dd_scale[k], supervisor.drawdown_scale(net_abs[:t], replace(CFG, dd_days=120)))


def test_hold_refuses_to_trade_on_a_corrupted_solve_and_only_then():
    P = make_panel_synth(n=300, N=12, drift=np.random.default_rng(1).normal(0, 1, 12))
    def agents():
        ags = [RankCarry(days=d) for d in (10, 20, 40)]
        for a, d in zip(ags, (10, 20, 40)):
            a.name = f"c{d}"
        return ags
    w = (P.dates[180].strftime("%Y-%m-%d"), P.dates[230].strftime("%Y-%m-%d"))
    cfg = replace(CFG, consensus="graph", topology="complete", faulty=("c40",), faulty_window=w, attack=0.01,
                  attack_kind="noise", safety="hold", hold_tol=1e-3)
    res = run_engine(P, agents(), cfg, solver={"iters": 300})
    inside = [w[0] <= d.strftime("%Y-%m-%d") <= w[1] for d in res.solve_dates]
    assert any(res.held) and all(i for i, h in zip(inside, res.held) if h)      # held only while the liar is active
    assert not any(h for i, h in zip(inside, res.held) if not i)
    for (_, x), h, t in zip(res.targets[-len(res.held):], res.held, res.solved):
        if h:
            assert res.cost[t - res.rebal[0]] == 0.0                              # nothing traded


def test_safety_record_and_window_summary():
    _, res = losing_run("derisk")
    rec = supervisor.safety_record(res, replace(CFG, dd_days=120))
    assert {"rho_dd", "rho_vol", "rho_solve", "rho_rvol_recovery"} <= set(rec.columns)
    assert (rec.rho_dd < 0).any()                               # the losing run breaches the drawdown spec
    s = supervisor.window_summary(rec, windows={"all": (str(rec.index[0].date()), str(rec.index[-1].date()))})
    assert "whole" in s.index and s.loc["whole", "bars_violating_rho_dd"] > 0
