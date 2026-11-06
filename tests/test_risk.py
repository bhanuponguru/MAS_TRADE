import numpy as np

from mas_trade.risk import betas, ledoit_wolf, neutralise


def test_ledoit_wolf_is_psd_and_shrinks():
    X = np.random.default_rng(0).normal(size=(30, 20))
    S = ledoit_wolf(X)
    assert np.linalg.eigvalsh(S).min() > 0
    assert np.linalg.cond(S) < np.linalg.cond(np.cov(X.T, bias=True))


def test_neutralise_projects_out_dollar_and_beta():
    rng = np.random.default_rng(1)
    w, b = rng.normal(size=10), rng.uniform(0.5, 1.5, 10)
    v = neutralise(w, b)
    assert abs(v.sum()) < 1e-12 and abs(b @ v) < 1e-12


def test_betas_recover_planted_loading():
    rng = np.random.default_rng(2)
    rb = rng.normal(0, 0.02, 2000)
    true = np.array([0.5, 1.0, 1.5])
    R = rb[:, None] * true + rng.normal(0, 0.005, (2000, 3))
    assert np.allclose(betas(R, rb), true, atol=0.05)
