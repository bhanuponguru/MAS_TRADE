"""Decentralised cell ADMM over a communication graph (decision 0042)."""
from dataclasses import replace

import numpy as np
import pytest

from mas_trade.agents.carry import RankCarry
from mas_trade.cells_admm import objective, solve_cells, solve_reference
from mas_trade.engine import run_engine
from mas_trade.graph_admm import TOPOLOGIES, adjacency, is_connected, metropolis, mixing_rate, network, solve_cells_graph, solve_cells_resilient, wmsr_mix
from test_cells_admm import COUPLINGS, make
from test_engine import CFG, make_panel_synth


def couplings_for(name, M):
    kw = dict(COUPLINGS[name])
    if "cap" in kw:
        kw["cap"] = np.full((M, 8), kw["cap"].max())
    if "margin" in kw:
        kw["margin"] = np.linspace(kw["margin"].min(), kw["margin"].max(), M)
    return kw


@pytest.mark.parametrize("kind", TOPOLOGIES)
@pytest.mark.parametrize("M", [2, 3, 8])
def test_metropolis_weights_are_a_valid_mixing_matrix(kind, M):
    A = adjacency(kind, M, seed=1)
    assert is_connected(A) and not A.diagonal().any() and (A == A.T).all()
    W = metropolis(A)
    assert np.allclose(W, W.T) and np.allclose(W.sum(0), 1) and np.allclose(W.sum(1), 1) and (W >= 0).all()
    assert ((W > 0) <= (A | np.eye(M, dtype=bool))).all()                  # weight only on edges: neighbours only
    assert mixing_rate(W) < 1 - 1e-9                                         # connected: averaging converges


def test_sparser_graphs_mix_more_slowly():
    rates = {k: mixing_rate(network(k, 8)) for k in ("complete", "ring", "line")}
    assert rates["complete"] < 1e-9 < rates["ring"] < rates["line"]


@pytest.mark.parametrize("name", ["plain", "fee", "all", "vol+all"])
def test_complete_graph_is_the_hub_algorithm(name):
    p = make(0, M=3, **couplings_for(name, 3))
    hub = solve_cells(p, tol=1e-9)
    g = solve_cells_graph(p, network("complete", 3), tol=1e-9, relax=1.7)     # same relaxation as the hub
    assert g.converged and g.iters == hub.iters
    assert np.abs(g.x - hub.x).max() <= 1e-10 * np.abs(hub.x).max()


CASES = [("ring", n) for n in ("plain", "fee", "cap", "margin", "gross", "beta", "all", "vol+all")] + \
        [(k, "all") for k in ("line", "star", "random")]          # every limit on one sparse graph, the hard case on every graph


@pytest.mark.parametrize("kind,name", CASES)
def test_every_topology_reaches_the_one_node_reference(kind, name):
    M = 4
    p = make(1, M=M, **couplings_for(name, M))
    g = solve_cells_graph(p, network(kind, M, seed=2), rounds=3, tol=1e-9, iters=6000)
    ref = solve_reference(p)
    typical = np.abs(ref.sum(0)).mean()
    assert g.converged and g.state["disagreement"] <= 1e-9
    assert np.abs(g.X - ref.sum(0)).max() <= 1e-3 * typical
    assert (objective(p, g.x) - objective(p, ref)) / abs(objective(p, ref)) <= 1e-5
    for i in range(M):                                                       # every agent's own constraints hold
        assert np.abs(p.A[i].T @ g.x[i]).max() < 1e-6
        assert np.abs(g.x[i]).max() <= p.cap[i].max() + 1e-6
        assert np.abs(g.x[i]).sum() <= p.margin[i] + 1e-6
    assert np.abs(g.X).sum() <= p.gross + 1e-6 and abs(p.beta @ g.X) <= p.beta_band + 1e-6


def test_poorer_connectivity_costs_more_communication():
    """The proposal's topology question in its simplest form: messages needed to converge (iterations x gossip rounds)."""
    M = 8
    p = make(0, M=M, **couplings_for("all", M))
    cost = {}
    for kind in ("complete", "ring", "line"):
        g = solve_cells_graph(p, network(kind, M), rounds=3, tol=1e-9, iters=6000)
        assert g.converged
        cost[kind] = g.iters * 3
    assert cost["complete"] < cost["ring"] < cost["line"]


def test_a_run_does_not_stop_while_agents_disagree_on_prices():
    M = 8
    p = make(0, M=M, **couplings_for("all", M))
    g = solve_cells_graph(p, network("ring", M), rounds=1, tol=1e-9, iters=300)   # far too few iterations for a ring of 8
    assert not g.converged


def test_engine_graph_mode_matches_the_hub():
    drift = np.random.default_rng(1).normal(0, 1, 12)
    P = make_panel_synth(n=300, N=12, drift=drift)
    agents = lambda: [RankCarry(days=10), RankCarry(days=20), RankCarry(days=40)]
    hub = run_engine(P, agents(), CFG)
    for kind in ("ring", "line"):
        g = run_engine(P, agents(), replace(CFG, consensus="graph", topology=kind, gossip_rounds=2))
        assert g.unconverged == 0
        assert np.allclose(np.cumprod(1 + g.net), np.cumprod(1 + hub.net), rtol=1e-4, atol=1e-6)
        for (_, xh), (_, xg) in zip(hub.targets, g.targets):
            if xh.size:
                assert np.abs(xh.sum(0) - xg.sum(0)).max() <= 1e-3 * max(np.abs(xh.sum(0)).max(), 1e-9)


# ------------------------------------------------------------------ resilience options (experiment 021)
def test_wmsr_mix_is_plain_mixing_when_nothing_is_trimmed_and_ignores_an_outlier():
    A = adjacency("complete", 5)
    W = metropolis(A)
    S = np.random.default_rng(0).normal(size=(5, 3))
    assert np.allclose(wmsr_mix(S, A, W, 0), W @ S)
    S2 = S.copy()
    S2[4] = 1e6                                                              # one neighbour sends nonsense
    out = wmsr_mix(S2, A, W, 1)
    lo, hi = S[:4].min(0), S[:4].max(0)
    assert (out[:4] >= lo - 1e-12).all() and (out[:4] <= hi + 1e-12).all()   # honest values stay in the honest range


def test_link_failures_still_reach_the_reference():
    """Edges that drop at random in every round: the weights are recomputed on the edges that are up, so the sum of the
    estimates is kept and the solver still reaches the optimum, only later."""
    M = 4
    p = make(1, M=M, **couplings_for("all", M))
    ref = solve_reference(p)
    base = solve_cells_graph(p, network("ring", M), rounds=3, tol=1e-9, iters=6000)
    g = solve_cells_graph(p, network("ring", M), rounds=3, tol=1e-9, iters=6000, link_fail=0.3, seed=1)
    assert g.converged and g.iters >= base.iters
    assert np.abs(g.X - ref.sum(0)).max() <= 1e-3 * np.abs(ref.sum(0)).mean()


def test_engine_offline_agent_holds_nothing_and_graph_matches_hub():
    drift = np.random.default_rng(1).normal(0, 1, 12)
    P = make_panel_synth(n=300, N=12, drift=drift)
    def agents():
        ags = [RankCarry(days=10), RankCarry(days=20), RankCarry(days=40)]
        for a, nm in zip(ags, ("c10", "c20", "c40")):
            a.name = nm
        return ags
    names = ["c10", "c20", "c40"]
    d0, d1 = P.dates[200].strftime("%Y-%m-%d"), P.dates[260].strftime("%Y-%m-%d")
    cfg = replace(CFG, offline=((names[1], d0, d1),))
    hub = run_engine(P, agents(), cfg)
    g = run_engine(P, agents(), replace(cfg, consensus="graph", topology="ring", gossip_rounds=2))
    hit = 0
    for t, (_, x) in zip(hub.rebal, hub.targets):
        if x.size and d0 <= P.dates[t].strftime("%Y-%m-%d") <= d1:
            assert np.abs(x[1]).max() == 0.0
            hit += 1
    assert hit >= 2
    assert np.allclose(np.cumprod(1 + g.net), np.cumprod(1 + hub.net), rtol=1e-4, atol=1e-6)


def test_detector_isolates_a_liar_on_a_robust_graph_and_nobody_otherwise():
    M = 6
    p = make(0, M=M, **couplings_for("all", M))
    p.cap = p.cap.copy()
    p.cap[2] = 0.0                                                           # the misbehaving agent holds nothing
    opt = solve_cells(p, tol=1e-10, iters=50000).X
    A = adjacency("complete", M)
    clean = solve_cells_resilient(p, A, tol=1e-9, iters=4000)
    assert clean.state["isolated"] == [] and clean.converged
    g = solve_cells_resilient(p, A, faulty=[2], attack=lambda v, k: v + 0.01, tol=1e-9, iters=4000)
    assert g.state["isolated"] == [2] and g.converged
    assert np.abs(g.X - opt).max() <= 1e-4 * np.abs(opt).mean()
    bad = solve_cells_graph(p, metropolis(A), faulty=[2], attack=lambda v, k: v + 0.01, tol=1e-9, iters=400)
    assert np.abs(bad.X - opt).max() > 0.1 * np.abs(opt).mean()             # without the detector the lie spoils the result


def test_engine_detector_quarantines_the_liar_and_matches_the_hub_without_it():
    drift = np.random.default_rng(1).normal(0, 1, 12)
    P = make_panel_synth(n=300, N=12, drift=drift)

    def agents():
        ags = [RankCarry(days=d) for d in (10, 20, 40, 60)]
        for a, d in zip(ags, (10, 20, 40, 60)):
            a.name = f"c{d}"
        return ags
    hub = run_engine(P, agents(), replace(CFG, faulty=("c40",)))
    g = run_engine(P, agents(), replace(CFG, consensus="graph", topology="complete", faulty=("c40",), attack=0.01, detect=50))
    assert all(q == [2] for q in g.isolated)
    assert np.allclose(np.cumprod(1 + g.net), np.cumprod(1 + hub.net), rtol=1e-4, atol=1e-6)
