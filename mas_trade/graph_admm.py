"""The joint cell ADMM without a hub: agents talk only to their neighbours on a communication graph (decision 0042).

cells_admm.solve_cells is a sharing ADMM whose hub, every iteration, averages all agents' positions, solves the system step
(cost of the net trade, gross cap, beta band, priced variance) and returns one price per coin. Here every agent i keeps its
own copies of what the hub held:
    s_i  estimate of the average position (dynamic average consensus),
    z_i  its own solution of the system step (the system data are public),
    u_i  its own scaled price.
Per iteration:
    x_i  <- agent i's step against v_i = x_i - s_i + z_i - u_i              (exactly the hub version's agent step)
    s    <- W^r (s + x_new - x_old)                                           (add own change, then mix with neighbours)
    z_i  <- system step at M (s_i + u_i)
    u    <- W^r (u + s - z)                                                   (prices are mixed too, so they must agree)
W is the Metropolis weight matrix of the graph (symmetric, doubly stochastic), r the gossip rounds per iteration. The sum of
the estimates always equals the sum of the positions, so at a fixed point every estimate is the true average and every
price is the same: the hub's fixed point, i.e. the optimum. On the complete graph (W = 11'/M) it is the hub algorithm.
"""
import numpy as np

from .cells_admm import CellSolution, _Agent, _x_step_system

TOPOLOGIES = ("complete", "ring", "line", "star", "random")


def adjacency(kind, M, p=0.4, seed=0):
    """Undirected graph on M agents, no self-loops. 'random' is Erdos-Renyi G(M, p), redrawn until connected."""
    A = np.zeros((M, M), bool)
    if kind == "complete":
        A[:] = True
    elif kind in ("ring", "line"):
        for i in range(M - 1):
            A[i, i + 1] = A[i + 1, i] = True
        if kind == "ring" and M > 2:
            A[0, -1] = A[-1, 0] = True
    elif kind == "star":
        A[0, :] = A[:, 0] = True
    elif kind == "random":
        rng = np.random.default_rng(seed)
        while True:
            U = np.triu(rng.random((M, M)) < p, 1)
            A = U | U.T
            if is_connected(A):
                break
    else:
        raise ValueError(f"unknown topology {kind!r}; one of {TOPOLOGIES}")
    np.fill_diagonal(A, False)
    return A


def is_connected(A):
    M = len(A)
    seen, todo = {0}, [0]
    while todo:
        i = todo.pop()
        for j in np.flatnonzero(A[i]):
            if j not in seen:
                seen.add(int(j))
                todo.append(int(j))
    return len(seen) == M


def metropolis(A):
    """Metropolis-Hastings weights W_ij = 1 / (1 + max(deg_i, deg_j)) on edges, the rest on the diagonal: symmetric and
    doubly stochastic for any undirected graph, using only what neighbours know about each other."""
    M = len(A)
    deg = A.sum(1)
    W = np.where(A, 1.0 / (1.0 + np.maximum(deg[:, None], deg[None, :])), 0.0)
    np.fill_diagonal(W, 0.0)
    W[np.diag_indices(M)] = 1.0 - W.sum(1)
    return W


def mixing_rate(W):
    """|lambda_2(W)|: the second largest eigenvalue modulus. Average consensus error shrinks like |lambda_2|^k; 1 - |lambda_2|
    is the spectral gap (larger = faster mixing, better connected graph)."""
    ev = np.sort(np.abs(np.linalg.eigvalsh(W)))
    return float(ev[-2]) if len(ev) > 1 else 0.0


def network(kind, M, seed=0):
    return metropolis(adjacency(kind, M, seed=seed))


def solve_cells_graph(p, W, rounds=1, rho=None, sigma=None, iters=3000, tol=1e-6, inner=10, relax=1.0):
    """Decentralised version of cells_admm.solve_cells on the graph with mixing matrix W (see the module docstring).
    rho and sigma as in the hub version (agreed once from the mean risk aversion). Over-relaxation is off by default: with slow
    mixing the hub's 1.7 oscillated. The run counts as converged only when the hub's residuals are small AND the agents'
    estimates of the average and their prices agree."""
    M, N = p.mu.shape
    curv = 5.0 * float((np.mean(p.gamma) + p.vol_penalty) * max(np.mean(p.d), 1e-12))
    rho = curv if rho is None else rho
    sigma = curv if sigma is None else sigma
    agents = [_Agent(p, i, rho, sigma) for i in range(M)]
    Wr = np.linalg.matrix_power(np.asarray(W, float), max(int(rounds), 1))
    x = np.zeros((M, N))
    s = np.zeros((M, N))                     # estimates of the average position (sum s = sum x at all times)
    z = np.zeros((M, N))
    u = np.zeros((M, N))
    t = M / rho
    lam = np.zeros((M, 2))                   # each agent's gross-cap and beta-band prices
    ok = False
    for k in range(1, iters + 1):
        xn = np.stack([agents[i].solve(p, x[i] - s[i] + z[i] - u[i], rho, sigma, inner) for i in range(M)])
        s = Wr @ (s + xn - x)
        sh = relax * s + (1.0 - relax) * z
        zn = np.empty((M, N))
        for i in range(M):
            X, lam[i, 0], lam[i, 1] = _x_step_system(M * (sh[i] + u[i]), t, p)
            zn[i] = X / M
        u = Wr @ (u + sh - zn)
        xbar = xn.mean(0)
        prim = float(np.linalg.norm(s - zn, axis=1).max())
        dual = float(rho * np.linalg.norm(zn - z, axis=1).max())
        ubar = u.mean(0)
        scale_p = max(float(np.linalg.norm(xn)), float(np.linalg.norm(zn.mean(0))), 1e-9)
        scale_d = max(float(np.linalg.norm(rho * ubar)), 1e-9)
        disagree_x = float(np.linalg.norm(s - xbar, axis=1).max())
        disagree_u = float(rho * np.linalg.norm(u - ubar, axis=1).max())
        x, z = xn, zn
        ok = prim <= tol * scale_p and dual <= tol * scale_d and disagree_x <= tol * scale_p and disagree_u <= tol * scale_d
        if ok:
            break
    prices = {"net": rho * ubar, "net_by_agent": rho * u, "margin": np.array([sigma * a.theta for a in agents]),
              "gross": float(lam[:, 0].mean()), "beta": float(lam[:, 1].mean()), "vol": p.vol_penalty,
              "neutral": [a.nu.copy() for a in agents]}
    return CellSolution(x=x, X=x.sum(0), prices=prices, iters=k, converged=ok, primal_res=prim, dual_res=dual,
                        state={"disagreement": max(disagree_x / scale_p, disagree_u / scale_d), "rounds": int(rounds)})
