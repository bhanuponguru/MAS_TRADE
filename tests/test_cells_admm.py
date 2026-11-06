import copy

import numpy as np
import pytest

from mas_trade import cells_admm as ca
from mas_trade.cells_admm import CellProblem, objective, solve_cells, solve_reference


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


def make(seed, M=3, N=8, neutral=True, **kw):
    r = np.random.default_rng(seed)
    B = r.uniform(0.5, 1.5, (N, 1))
    A = [np.column_stack([np.ones(N), B[:, 0]]) if neutral else None for _ in range(M)]
    return CellProblem(mu=r.normal(0, 0.004, (M, N)), gamma=r.uniform(0.8, 1.5, M) * 100, d=r.uniform(0.02, 0.06, N) ** 2,
                       H=r.normal(0, 0.2, N), kappa=r.uniform(0.01, 0.05, N), B=B, F=np.array([[0.05 ** 2]]), A=A, **kw)


COUPLINGS = {
    "plain": {},
    "fee": dict(fee=5e-4),
    "cap": dict(cap=np.full((3, 8), 0.03)),
    "margin": dict(margin=np.array([0.15, 0.2, 0.25])),
    "gross": dict(gross=0.12),
    "beta": dict(beta=np.linspace(0.5, 1.5, 8), beta_band=0.05),
    "all": dict(fee=5e-4, cap=np.full((3, 8), 0.04), margin=np.array([0.2, 0.25, 0.3]), gross=0.2,
                beta=np.linspace(0.5, 1.5, 8), beta_band=0.03),
}


@pytest.mark.parametrize("name", list(COUPLINGS))
@pytest.mark.parametrize("seed", range(5))
def test_l2_1_matches_one_node_reference(name, seed):
    p = make(seed, **COUPLINGS[name])
    s = solve_cells(p)
    ref = solve_reference(p)
    typical = np.abs(ref.sum(0)).mean()
    assert s.converged
    assert np.abs(s.X - ref.sum(0)).max() <= 1e-3 * typical
    assert (objective(p, s.x) - objective(p, ref)) / abs(objective(p, ref)) <= 1e-5
    for i in range(3):                                                  # the constraints hold
        assert np.abs(p.A[i].T @ s.x[i]).max() < 1e-6
        assert np.abs(s.x[i]).max() <= p.cap[i].max() + 1e-6
        assert np.abs(s.x[i]).sum() <= p.margin[i] + 1e-6
    assert np.abs(s.X).sum() <= p.gross + 1e-6
    assert abs(p.beta @ s.X) <= p.beta_band + 1e-6


def test_l2_2_prices_nonnegative_and_zero_when_slack():
    slack = make(0, margin=np.full(3, 50.0), gross=50.0, beta=np.linspace(0.5, 1.5, 8), beta_band=50.0)
    s = solve_cells(slack)
    assert s.prices["gross"] == 0 and s.prices["beta"] == 0 and (s.prices["margin"] == 0).all()
    tight = make(1, **COUPLINGS["all"])
    s = solve_cells(tight)
    assert (s.prices["margin"] >= 0).all() and s.prices["gross"] >= 0
    assert s.prices["gross"] > 0 or (s.prices["margin"] > 0).any()       # something binds


def _value(p):
    s = solve_cells(p, tol=1e-10)
    return objective(p, s.x), s


def test_l2_2_margin_and_gross_prices_equal_the_marginal_value_of_the_limit():
    base = make(2, margin=np.array([0.15, 5.0, 5.0]))
    v0, s0 = _value(base)
    lam = s0.prices["margin"][0]
    assert lam > 0
    dm = 1e-4
    up = make(2, margin=np.array([0.15 + dm, 5.0, 5.0]))
    v1, _ = _value(up)
    assert abs((v1 - v0) / dm + lam) <= 0.05 * lam                      # d objective / d margin = -price
    g = make(3, gross=0.12)
    v0, s0 = _value(g)
    lam = s0.prices["gross"]
    assert lam > 0
    v1, _ = _value(make(3, gross=0.12 + dm))
    assert abs((v1 - v0) / dm + lam) <= 0.05 * lam


def test_l2_3_netting_charges_cost_on_the_net_trade_only():
    N = 6
    kw = dict(d=np.full(N, 0.04 ** 2), kappa=np.full(N, 0.05), fee=5e-4, H=np.zeros(N), gamma=np.array([100.0, 100.0]))
    mu = np.zeros((2, N))
    mu[0, 0], mu[1, 0] = 0.004, -0.0035                                  # opposite views on coin 0
    joint = solve_cells(CellProblem(mu=mu, **kw))
    sep = [solve_cells(CellProblem(mu=mu[i:i + 1], **{**kw, "gamma": kw["gamma"][i:i + 1]})) for i in range(2)]
    net_cost = ca.cost_fn(joint.X, kw["fee"], kw["kappa"])
    separate_cost = sum(ca.cost_fn(s.X, kw["fee"], kw["kappa"]) for s in sep)
    assert net_cost < separate_cost
    assert abs(joint.X[0]) < abs(sep[0].X[0]) and abs(joint.X[0]) < 0.5 * abs(sep[0].X[0] + sep[1].X[0]) + abs(sep[0].X[0])
    assert not np.allclose(joint.X, sep[0].X + sep[1].X, atol=1e-6)      # the netted solution differs from solving apart
    gross_positions = np.abs(joint.x).sum()
    assert gross_positions > np.abs(joint.X).sum() - 1e-9               # offsetting positions exist inside the net


def test_l2_4_binding_margin_moves_capital_to_higher_edge_per_unit_risk():
    N = 5
    mu = np.array([[0.002, 0.004, 0.006, 0.008, 0.010]])
    base = dict(mu=mu, gamma=np.array([100.0]), d=np.full(N, 0.04 ** 2), H=np.zeros(N))
    shares = []
    for m in (10.0, 0.15, 0.08, 0.04):                                   # the first is slack: unconstrained sum|x| = 0.19
        x = solve_cells(CellProblem(**base, margin=np.array([m]))).x[0]
        assert np.abs(x).sum() <= m + 1e-6
        shares.append(x[-1] / np.abs(x).sum())
    assert shares[0] < shares[1] < shares[2] < shares[3]                 # tighter margin: more capital on the best coin


def test_l2_5_solver_is_pure_and_warm_start_agrees():
    p = make(4, **COUPLINGS["all"])
    before = copy.deepcopy(p)
    a, b = solve_cells(p), solve_cells(p)
    assert np.array_equal(a.x, b.x) and np.array_equal(a.X, b.X)
    for f in ("mu", "gamma", "d", "H", "kappa"):
        assert np.array_equal(getattr(p, f), getattr(before, f))
    w = solve_cells(p, warm=a.state)
    assert w.iters <= a.iters and np.abs(w.X - a.X).max() < 1e-6
