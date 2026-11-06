import numpy as np

from mas_trade import cells_admm as ca


def test_prox_cost_matches_brute_force_and_dead_zone():
    grid = np.linspace(-1, 1, 400001)
    for v in (-0.5, -0.0004, 0.0, 0.0003, 0.2, 0.9):
        t, fee, kap = 0.7, 5e-4, 0.3
        f = t * (fee * np.abs(grid) + kap * np.abs(grid) ** 1.5) + 0.5 * (grid - v) ** 2
        assert abs(ca.prox_cost(np.array([v]), t, fee, np.array([kap]))[0] - grid[f.argmin()]) < 1e-4
    assert ca.prox_cost(np.array([1e-4]), 1.0, 5e-4, np.array([0.1]))[0] == 0.0


def test_neutral_solve_matches_kkt_solution():
    rng = np.random.default_rng(0)
    n = 8
    d = rng.uniform(0.5, 2, n)
    A = np.column_stack([np.ones(n), rng.uniform(0.5, 1.5, n)])
    lin = rng.normal(size=(3, n))
    x = ca.neutral_solve((1 / d)[None, :], lin, A)
    assert x.shape == (3, n) and np.abs(x @ A).max() < 1e-10             # neutral
    for row, l in zip(x, lin):                                          # optimal: gradient lies in span(A)
        g = d * row + l
        assert np.abs(g - A @ np.linalg.lstsq(A, g, rcond=None)[0]).max() < 1e-10
