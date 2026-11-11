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

from .cells_admm import CellProblem, CellSolution, _Agent, _x_step_system

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
    elif kind == "ring2":                  # each agent linked to the two nearest on each side (4 neighbours): sparse but robust
        for i in range(M):
            for s in (1, 2):
                A[i, (i + s) % M] = A[(i + s) % M, i] = True
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
        raise ValueError(f"unknown topology {kind!r}; one of {TOPOLOGIES + ('ring2',)}")
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


def extreme_share(S, A):
    """E[i, j]: the share of coordinates in which neighbour j sent agent i the most extreme value beyond i's own, i.e. the
    value W-MSR with F = 1 would discard first (W-MSR's trimmed MIXING was rejected in experiment 021: it breaks the
    optimiser's sum invariant; its code is at commit 93b0fe7). An honest neighbour is extreme now and then; a neighbour that adds a lie to
    everything it sends is extreme almost everywhere, every iteration."""
    E = np.zeros(A.shape)
    for i in range(len(S)):
        nb = np.flatnonzero(A[i])
        if len(nb):
            vals, own = S[nb], S[i]
            E[i, nb] = (((vals == vals.max(0)) & (vals > own)) | ((vals == vals.min(0)) & (vals < own))).mean(1)
    return E


def subproblem(p, keep):
    """The CellProblem of the agents in keep only (the others hold nothing)."""
    keep = np.asarray(keep, int)
    return CellProblem(mu=p.mu[keep], gamma=p.gamma[keep], d=p.d, H=p.H, fee=p.fee, kappa=p.kappa, B=p.B, F=p.F,
                       A=[p.A[i] for i in keep], cap=p.cap[keep], margin=p.margin[keep], gross=p.gross, beta=p.beta,
                       beta_band=p.beta_band, vol_penalty=p.vol_penalty)


def solve_cells_resilient(p, A, faulty=(), detect=50, share=0.9, **kw):
    """Detect and isolate (experiment 021): run solve_cells_graph with the detector on; when agents are isolated, the others
    restart on the graph without them (as for an agent that is offline), until a run ends with no new isolation. A is the
    adjacency matrix. Returns the solution on all M agents (isolated ones hold nothing); state['isolated'] lists them and
    state['restarts'] counts the restarts; iters is the total over all runs."""
    M = p.mu.shape[0]
    keep, total = np.arange(M), 0
    while True:
        Ak = A[np.ix_(keep, keep)]
        if not is_connected(Ak):
            raise RuntimeError(f"isolating agents {sorted(set(range(M)) - set(keep.tolist()))} disconnected the graph")
        fk = [q for q, i in enumerate(keep) if i in set(faulty)]
        sol = solve_cells_graph(subproblem(p, keep) if len(keep) < M else p, metropolis(Ak), faulty=fk, detect=detect,
                                share=share, **kw)
        total += sol.iters
        new = sol.state.get("isolate", [])
        if not new:
            break
        keep = np.delete(keep, new)
    x = np.zeros((M, p.mu.shape[1]))
    x[keep] = sol.x
    state = dict(sol.state, isolated=sorted(set(range(M)) - set(keep.tolist())), restarts=M - len(keep))
    return CellSolution(x=x, X=x.sum(0), prices=sol.prices, iters=total, converged=sol.converged, primal_res=sol.primal_res,
                        dual_res=sol.dual_res, state=state)


def solve_cells_graph(p, W, rounds=1, rho=None, sigma=None, iters=3000, tol=1e-6, inner=10, relax=1.0, trace=None,
                      link_fail=0.0, faulty=(), attack=None, seed=0, detect=0, share=0.9):
    """Decentralised version of cells_admm.solve_cells on the graph with mixing matrix W (see the module docstring).
    rho and sigma as in the hub version (agreed once from the mean risk aversion). Over-relaxation is off by default: with slow
    mixing the hub's 1.7 oscillated. The run counts as converged only when the hub's residuals are small AND the agents'
    estimates of the average and their prices agree. trace: an optional list that receives the net position x.sum(0) and the
    disagreement after every iteration (for the communication-budget experiment).

    Resilience options (experiment 021), all off by default:
      link_fail  every edge is down independently with this probability in every gossip round (the Metropolis weights are
                 recomputed on the edges that are up, so the mixing stays doubly stochastic and the sum invariant holds);
      faulty     indices of misbehaving agents: they hold no position and send attack(values, k) instead of their state;
      attack     function (values of the faulty rows, iteration) -> what they send; default adds 1.0 to every entry;
      detect     if > 0: agent i flags neighbour j when j sent the most extreme value (extreme_share) in at least `share` of
                 the coordinates of both the average estimate and the price for `detect` iterations in a row; an agent flagged
                 by more than half of its neighbours is isolated: the run stops and returns state['isolate'] (used by
                 solve_cells_resilient, which restarts without it).
    Convergence and disagreement are then measured over the honest agents only."""
    M, N = p.mu.shape
    faulty = np.array(sorted(faulty), int)
    honest = np.setdiff1d(np.arange(M), faulty)
    attack = (lambda v, k: v + 1.0) if attack is None else attack
    A0 = np.asarray(W) > 0
    np.fill_diagonal(A0, False)
    rng = np.random.default_rng(seed)
    plain = link_fail == 0 and not len(faulty) and not detect
    streak = np.zeros((M, M), int)
    deg = A0.sum(1)
    ext = []
    isolate = []

    def mix(V, k):
        if plain:
            return Wr @ V
        for rd in range(max(int(rounds), 1)):
            A = A0
            if link_fail > 0:
                up = np.triu(rng.random(A0.shape) >= link_fail, 1)
                A = A0 & (up | up.T)
            S = V.copy()
            if len(faulty):
                S[faulty] = attack(V[faulty], k)
            if detect and rd == 0:
                ext.append(extreme_share(S, A0))
            V = (metropolis(A) if link_fail > 0 else np.asarray(W, float)) @ S
        return V

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
        xn = np.zeros((M, N))
        for i in honest:
            xn[i] = agents[i].solve(p, x[i] - s[i] + z[i] - u[i], rho, sigma, inner)
        s = mix(s + xn - x, k)
        sh = relax * s + (1.0 - relax) * z
        zn = np.empty((M, N))
        for i in range(M):
            X, lam[i, 0], lam[i, 1] = _x_step_system(M * (sh[i] + u[i]), t, p)
            zn[i] = X / M
        u = mix(u + sh - zn, k)
        if detect:
            streak = np.where(np.minimum(ext[0], ext[1]) >= share, streak + 1, 0)
            ext.clear()
            isolate = [j for j in range(M) if (streak[:, j] >= detect).sum() * 2 > deg[j]]
        xbar = xn.mean(0)
        h = honest
        prim = float(np.linalg.norm(s[h] - zn[h], axis=1).max())
        dual = float(rho * np.linalg.norm(zn[h] - z[h], axis=1).max())
        ubar = u[h].mean(0)
        scale_p = max(float(np.linalg.norm(xn)), float(np.linalg.norm(zn.mean(0))), 1e-9)
        scale_d = max(float(np.linalg.norm(rho * ubar)), 1e-9)
        disagree_x = float(np.linalg.norm(s[h] - xbar, axis=1).max())
        disagree_u = float(rho * np.linalg.norm(u[h] - ubar, axis=1).max())
        x, z = xn, zn
        if trace is not None:
            trace.append((xn.sum(0).copy(), max(disagree_x / scale_p, disagree_u / scale_d)))
        ok = prim <= tol * scale_p and dual <= tol * scale_d and disagree_x <= tol * scale_p and disagree_u <= tol * scale_d
        if ok or isolate:
            break
    prices = {"net": rho * ubar, "net_by_agent": rho * u, "margin": np.array([sigma * a.theta for a in agents]),
              "gross": float(lam[honest, 0].mean()), "beta": float(lam[honest, 1].mean()), "vol": p.vol_penalty,
              "neutral": [a.nu.copy() for a in agents]}
    return CellSolution(x=x, X=x.sum(0), prices=prices, iters=k, converged=ok, primal_res=prim, dual_res=dual,
                        state={"disagreement": max(disagree_x / scale_p, disagree_u / scale_d), "rounds": int(rounds),
                               "isolate": isolate,
                               "rel_res": max(prim / scale_p, dual / scale_d, disagree_x / scale_p, disagree_u / scale_d)})
