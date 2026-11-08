"""Decentralised cell ADMM over a communication graph (decision 0042)."""
from dataclasses import replace

import numpy as np
import pytest

from mas_trade.agents.carry import RankCarry
from mas_trade.cells_admm import objective, solve_cells, solve_reference
from mas_trade.engine import run_engine
from mas_trade.graph_admm import TOPOLOGIES, adjacency, is_connected, metropolis, mixing_rate, network, solve_cells_graph
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
