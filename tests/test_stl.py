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
