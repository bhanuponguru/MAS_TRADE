import numpy as np
import pandas as pd
import pytest

from mas_trade import stl


def test_temporal_operators_match_brute_force():
    rng = np.random.default_rng(1)
    x = rng.normal(size=40)
    n = len(x)
    for a, b in [(0, 0), (0, 3), (2, 5)]:
        fut = [x[t + a:min(t + b, n - 1) + 1] for t in range(n)]
        past = [x[max(t - b, 0):t - a + 1] if t - a >= 0 else np.array([]) for t in range(n)]
        assert np.allclose(stl.always(x, a, b), [f.min() if len(f) else np.inf for f in fut])
        assert np.allclose(stl.eventually(x, a, b), [f.max() if len(f) else -np.inf for f in fut])
        assert np.allclose(stl.historically(x, a, b), [p.min() if len(p) else np.inf for p in past])
        assert np.allclose(stl.once(x, a, b), [p.max() if len(p) else -np.inf for p in past])


def test_boolean_connectives_and_predicates():
    assert stl.le(0.1, 0.2) == pytest.approx(0.5)     # half the limit left
    assert stl.ge(-0.3, -0.15) == pytest.approx(-1.0)  # breach by one full limit
    a, b = np.array([1.0, -1.0]), np.array([-2.0, 3.0])
    assert np.allclose(stl.and_(a, b), [-2, -1]) and np.allclose(stl.or_(a, b), [1, 3])
    assert np.allclose(stl.implies(a, b), [-1, 3])


def test_recovery_spec_flags_only_long_breaches():
    max_vol, recover = 0.20, 3
    rho_vol = stl.le(np.array([0.1, 0.3, 0.3, 0.1, 0.3, 0.3, 0.3, 0.3, 0.3, 0.1]), max_vol)
    rho_rec = stl.implies(stl.not_(rho_vol), stl.eventually(rho_vol, 0, recover))
    assert (rho_rec[:4] > 0).all()                    # 2-bar breach recovers within 3 bars
    assert rho_rec[4] < 0                             # 5-bar breach: no recovery within [t, t+3]
    assert rho_rec[6] > 0                             # from here it does recover in time


def test_rolling_drawdown_and_vol():
    r = np.array([0.1, -0.1, -0.1, 0.05, 0.0])
    eq = np.cumprod(1 + r)
    dd = stl.rolling_drawdown(r, window=3)
    assert dd[0] == 0 and dd[2] == pytest.approx(eq[2] / eq[:3].max() - 1)
    assert np.all(dd <= 0)
    v = stl.rolling_vol(np.random.default_rng(0).normal(0, 0.01, 200), 20, 365.0)
    assert np.isnan(v[0]) and np.all(v[19:] > 0)


def test_s1_deadline_and_recovery_specs_match_brute_force():
    rng = np.random.default_rng(4)
    gap = np.abs(rng.normal(0, 1, 60))
    tol, n = 0.5, 4
    rho = stl.reaches_within(gap, tol, n)
    brute = [max((tol - gap[u]) / tol for u in range(t, min(t + n, len(gap) - 1) + 1)) for t in range(len(gap))]
    assert np.allclose(rho, brute)
    assert (rho[gap < tol] > 0).all()                      # already at target: satisfied
    ok = stl.le(np.array([0.1, 0.3, 0.3, 0.3, 0.1, 0.3]), 0.2)
    assert np.allclose(stl.recovery(ok, 2), stl.implies(stl.not_(ok), stl.eventually(ok, 0, 2)))


def test_s2_belief_sanity_zeroes_corrupt_beliefs_and_leaves_honest_ones():
    rng = np.random.default_rng(5)
    history = rng.normal(0, 0.004, (300, 50))
    bound = stl.belief_bound(history)
    honest = rng.normal(0, 0.004, 50)
    b, share = stl.sanitize_belief(honest, bound)
    assert np.array_equal(b, honest) and share == 0.0
    for corrupt in (np.full(50, np.nan), honest * 100, np.full(50, np.inf)):
        b, share = stl.sanitize_belief(corrupt, bound)
        assert share > 0.9 and (b[np.abs(corrupt) > bound] == 0).all() and np.isfinite(b).all()
    mixed = honest.copy()
    mixed[7] = np.nan
    b, share = stl.sanitize_belief(mixed, bound)
    assert b[7] == 0 and np.array_equal(np.delete(b, 7), np.delete(honest, 7)) and np.isclose(share, 1 / 50)


def test_s2_kelly_scale_is_monotone_in_the_spec_margin():
    m = np.linspace(-1, 2, 61)
    s = stl.kelly_scale(m)
    assert (np.diff(s) >= -1e-12).all() and s.min() == 0.2 and s.max() == 1.0
    assert stl.kelly_scale(0.5) == 1.0 and stl.kelly_scale(0.0) == 0.2


def test_calibration_slope_is_one_when_calibrated_and_falls_with_over_confidence():
    rng = np.random.default_rng(6)
    belief = rng.normal(0, 0.003, 20000)
    r = belief + rng.normal(0, 0.06, 20000)               # E[r | belief] = belief
    assert abs(stl.calibration_slope(belief, r) - 1.0) < 0.4
    assert stl.calibration_slope(4 * belief, r) < 0.6
    assert stl.ge(stl.calibration_slope(4 * belief, r), 0.5) < stl.ge(stl.calibration_slope(belief, r), 0.5)


def test_calibration_ucb_acts_only_on_provable_over_confidence():
    rng = np.random.default_rng(7)
    small = rng.normal(0, 0.002, 3000)                                       # the size of a card's belief on real data
    r_small = 1.75 * small + rng.normal(0, 0.15, 3000)                       # truly calibrated-ish, but returns are noisy
    slope, se, ucb = stl.calibration_ucb(small, r_small)
    assert se > 0.5 and ucb > 0.5                                            # too noisy to call it over-confident: no action
    big = rng.normal(0, 0.006, 15000)
    r_big = 0.25 * big + rng.normal(0, 0.06, 15000)                          # a clearly over-confident agent with enough data
    assert stl.calibration_ucb(big, r_big)[2] < 0.5
