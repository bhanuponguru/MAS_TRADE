import numpy as np

from mas_trade.capital import reallocate_capital
from mas_trade.consensus import (complete_graph, is_r_s_robust, laplacian, laplacian_step,
                                 run_consensus, trust_matrix, wmsr_step, wmsr_trust_matrix)


def ring(n):
    adj = np.eye(n)
    for i in range(n):
        adj[i, (i + 1) % n] = adj[(i + 1) % n, i] = 1
    return adj


def test_doubly_stochastic_consensus_converges_to_average():
    adj = ring(6)
    W = trust_matrix(adj, np.ones(6))  # uniform trust on a regular graph -> doubly stochastic
    assert np.allclose(W.sum(0), 1) and np.allclose(W.sum(1), 1)
    x0 = np.random.default_rng(0).normal(size=(6, 4))
    x, _ = run_consensus(x0, W, adj, K=400, F=0, b=0.0, normalize=False)
    assert np.allclose(x, x0.mean(0), atol=1e-6)


def test_wmsr_keeps_benign_agents_inside_benign_range():
    rng = np.random.default_rng(1)
    adj = complete_graph(7)
    x0 = rng.uniform(-0.2, 0.2, size=(7, 5))
    x0[0] = 100.0  # adversary, frozen at an extreme value
    frozen = np.zeros(7, bool)
    frozen[0] = True
    lo, hi = x0[1:].min(0), x0[1:].max(0)
    W = trust_matrix(adj, np.ones(7))
    x, _ = run_consensus(x0, W, adj, K=50, F=1, b=0.0, frozen=frozen, normalize=False)
    assert np.all(x[1:] >= lo - 1e-9) and np.all(x[1:] <= hi + 1e-9)
    # plain consensus is dragged to the adversary
    xp, _ = run_consensus(x0, W, adj, K=50, F=0, b=0.0, frozen=frozen, normalize=False)
    assert xp[1:].max() > hi.max() + 1


def test_laplacian_stability_threshold():
    adj = ring(6)
    lmax = np.linalg.eigvalsh(laplacian(adj)).max()
    x0 = np.random.default_rng(2).normal(size=(6, 1))
    for eps, converges in ((0.9 * 2 / lmax, True), (1.1 * 2 / lmax, False)):
        x = x0.copy()
        for _ in range(500):
            x = laplacian_step(x, adj, eps)
        spread = np.ptp(x)
        assert (spread < 1e-6) if converges else (spread > 1e3)
    # sum of states preserved (1^T L = 0) -> consensus value is the initial average
    x = x0.copy()
    for _ in range(500):
        x = laplacian_step(x, adj, 0.9 * 2 / lmax)
    assert np.allclose(x, x0.mean())


def test_robustness_checks():
    assert is_r_s_robust(complete_graph(7), 2, 2)
    path = np.eye(5) + np.diag(np.ones(4), 1) + np.diag(np.ones(4), -1)
    assert not is_r_s_robust(path, 2, 2)


def test_trust_matrix_row_stochastic_and_favours_high_trust():
    s = np.array([0.2, 0.5, 0.8])
    W = trust_matrix(complete_graph(3), s)
    assert np.allclose(W.sum(1), 1) and W[0, 2] > W[0, 1] > W[0, 0]
    assert np.allclose(wmsr_trust_matrix(complete_graph(3), s, 1).sum(1), 1)


def test_capital_conserved_and_flows_to_trust():
    adj = complete_graph(5)
    s = np.array([0.2, 0.4, 0.5, 0.6, 0.9])
    W = trust_matrix(adj, s)
    c = np.full(5, 200.0)
    for _ in range(60):
        c2 = reallocate_capital(c, W, 0.5, 0.02)
        assert abs(c2.sum() - c.sum()) < 1e-8
        c = c2
    assert np.allclose(c, s / s.sum() * 1000, rtol=1e-3)
    assert c.argmax() == s.argmax()
    # floor respected
    c = reallocate_capital(np.array([1.0, 1.0, 98.0]), trust_matrix(complete_graph(3), np.array([1e-6, 1e-6, 1.0])), 1.0, 0.05)
    assert c.min() >= 5.0 - 1e-9 and abs(c.sum() - 100) < 1e-8


def test_wmsr_step_f0_equals_plain_product():
    rng = np.random.default_rng(3)
    adj = complete_graph(4)
    W = trust_matrix(adj, rng.uniform(0.3, 0.9, 4))
    x = rng.normal(size=(4, 3))
    assert np.allclose(wmsr_step(x, W, adj, 0), W @ x)
