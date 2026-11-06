import numpy as np

from mas_trade.costs import trade_cost


def test_trade_cost_monotone_in_size_and_inverse_in_adv():
    c = lambda d, adv: trade_cost(np.array([d]), np.array([adv]), np.array([0.05]), 5.0, 1.0, 1e6)
    assert c(0.02, 1e7) > c(0.01, 1e7) > 0
    assert c(0.01, 1e6) > c(0.01, 1e7)
    assert np.isclose(c(0.01, 1e7), 0.01 * (5e-4 + 0.05 * np.sqrt(0.01 * 1e6 / 1e7)))
