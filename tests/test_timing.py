import numpy as np

from mas_trade.agents.timing import period_slopes, timed_skill, untimed_skill
from mas_trade.market import MarketConfig, run_market
from mas_trade.simulate import make_regime_signals, make_world

T, WARM, N = 1000, 100, 60


def _run_pair(seed, rho_on, rho_off):
    w = make_world(T, N=N, seed=seed)
    signal, z, _ = make_regime_signals(w, rho_on, rho_off, seed=seed + 500)
    slopes = period_slopes(signal, w.R)
    untimed = np.zeros((T, N))
    timed = np.zeros((T, N))
    for t in range(WARM, T):
        untimed[t] = untimed_skill(slopes[:t]) * signal[t]
        timed[t] = timed_skill(slopes[:t], z[:t], z[t]) * signal[t]
    d, B, F = w.risk()
    cfg = MarketConfig(kelly=np.array([0.5]), floor=0.0)
    out = []
    for b in (untimed, timed):
        r = run_market(w.R[WARM:], b[None, WARM:], d, B, F, cfg)
        out.append(float(np.mean(r.pnl[:, 0] / r.wealth[:-1, 0])))   # mean period return on wealth
    return out


def test_t1_timing_beats_its_untimed_twin_when_skill_depends_on_the_state():
    diffs = np.array([b - a for a, b in (_run_pair(s, 0.3, 0.0) for s in range(20))])
    boot = np.random.default_rng(0).choice(diffs, (4000, len(diffs))).mean(1)
    assert diffs.mean() > 0 and np.percentile(boot, 5) > 0


def test_t2_timing_costs_little_when_skill_does_not_depend_on_the_state():
    res = np.array([_run_pair(s, 0.15, 0.15) for s in range(20)])
    untimed, timed = res[:, 0].mean(), res[:, 1].mean()
    assert untimed > 0 and timed - untimed >= -0.10 * untimed


def test_timed_skill_recovers_the_state_dependence_and_shrinks_without_it():
    rng = np.random.default_rng(0)
    z = rng.normal(size=400)
    slopes = 0.15 + 0.1 * z + rng.normal(0, 0.05, 400)
    assert timed_skill(slopes, z, 1.0) > timed_skill(slopes, z, -1.0) + 0.1
    flat = 0.15 + rng.normal(0, 0.05, 400)
    assert abs(timed_skill(flat, z, 2.0) - untimed_skill(flat)) < 0.05
