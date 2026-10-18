import numpy as np

from mas_trade.agents import AdversarialAgent, default_agents, weights_from_mu
from mas_trade.forecasting import ar1_forecast, prob_positive


def test_weights_gross_one_and_sign_follows_mu():
    mu = np.array([0.02, -0.01, 0.005, -0.03])
    w = weights_from_mu(mu)
    assert np.isclose(np.abs(w).sum(), 1.0)
    assert np.array_equal(np.sign(w), np.sign(mu))  # + long, - short
    assert np.all(weights_from_mu(np.zeros(3)) == 0)


def test_all_agents_produce_valid_portfolios():
    win = np.random.default_rng(0).normal(0.0005, 0.01, size=(252, 8))
    for a in default_agents() + [AdversarialAgent(0)]:
        w = weights_from_mu(a.forecast(win))
        assert w.shape == (8,) and np.isclose(np.abs(w).sum(), 1.0), a.name


def test_ar1_recovers_coefficient():
    rng = np.random.default_rng(0)
    r = np.zeros((5000, 1))
    for t in range(1, 5000):
        r[t] = 0.4 * r[t - 1] + rng.normal(0, 0.01, 1)
    assert abs(ar1_forecast(r)[0] - 0.4 * r[-1, 0]) < 0.003


def test_prob_positive():
    assert np.isclose(prob_positive(0.0, 0.01, 21), 0.5)
    assert prob_positive(0.001, 0.01, 21) > 0.5 > prob_positive(-0.001, 0.01, 21)
