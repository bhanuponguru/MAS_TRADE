"""Level 2: one joint ADMM over cells (agent i, coin a), with prices for what the cells share.

Cell (i, a) is the notional position x_ia of agent i in coin a. Every agent keeps its own quadratic reward / risk,
its own neutrality constraints, capacities and margin; the agents are coupled only through the NET position per
coin, X_a = sum_i x_ia, which carries the trading cost and the system limits:

    min  sum_i [ -mu_i'x_i + 1/2 x_i' Q_i x_i ]  +  sum_a C_a(X_a - H_a)
    s.t. A_i' x_i = 0,  |x_ia| <= cap_ia,  sum_a |x_ia| <= margin_i   (agent i)
         sum_a |X_a| <= gross,   |beta'X| <= beta_band                          (system)
with Q_i = gamma_i (diag(d) + B F B') (own variance plus a few factors) and C_a(d) = fee|d| + kappa_a |d|^1.5. Optionally a
SYSTEM variance term (vol_penalty / 2) X' (diag(d) + B F B') X is added: the priced form of a volatility limit. It acts on the
net position, so an agent that adds variance (a directional one) raises the price for everyone who trades the same coins and
factor, and an agent whose positions hedge the book lowers it; it is not a uniform shrink of all stakes.

It is a sharing problem (Boyd, Distributed Optimization, section 7.3): agents update in parallel against the
current price, the net-position step is a separable 1-D prox plus the priced system limits, and the scaled dual
u is the price per coin. Reported prices: net trade per coin (rho u), margin per agent, gross cap, beta band and
each agent's neutrality multipliers. An agent's step with capacities and margin is solved by a short inner ADMM
(warm-started), so the whole solver is exact only in the limit; tests compare it with a one-node reference.
"""
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq, minimize


# ------------------------------------------------------------------ cost primitives
def prox_cost(v, t, fee, kappa):
    """argmin_y t (fee|y| + kappa|y|^1.5) + (y - v)^2 / 2, elementwise. With q = sqrt|y|: q^2 + 1.5 t kappa q = |v| - t fee."""
    m = np.maximum(np.abs(v) - t * fee, 0.0)
    b = 1.5 * t * kappa
    q = (-b + np.sqrt(b * b + 4.0 * m)) / 2.0
    return np.sign(v) * q * q


def cost_fn(d, fee, kappa):
    a = np.abs(d)
    return float((fee * a + kappa * a ** 1.5).sum())


def neutral_solve(Dinv, lin, A):
    """argmin 1/2 x'Dx + lin'x s.t. A'x = 0 for diagonal D, batched over rows: x = Dinv (c - A nu), c = -lin."""
    c = -lin
    AtDA = np.einsum("nj,mn,nk->mjk", A, Dinv, A)
    nu = np.linalg.solve(AtDA, np.einsum("mn,nk->mk", Dinv * c, A)[..., None])[..., 0]
    return Dinv * (c - nu @ A.T)


# ------------------------------------------------------------------ problem and solution
@dataclass
class CellProblem:
    mu: np.ndarray                    # (M, N) expected return of a unit position over the holding period
    gamma: np.ndarray                 # (M,) risk aversion of each agent (1 / (kelly fraction x wealth))
    d: np.ndarray                     # (N,) idiosyncratic variance per holding period
    H: np.ndarray                     # (N,) previous NET system position (drifted)
    fee: float = 0.0
    kappa: np.ndarray = None          # (N,) impact coefficient; cost kappa |trade|^1.5
    B: np.ndarray = None              # (N, K) factor loadings
    F: np.ndarray = None              # (K, K) factor covariance per holding period
    A: list = None                    # per agent: (N, C_i) matrix with A_i' x_i = 0, or None
    cap: np.ndarray = None            # (M, N) capacity |x_ia| <= cap
    margin: np.ndarray = None         # (M,) bound on sum_a |x_ia| (leverage x wealth)
    gross: float = np.inf             # system gross cap
    beta: np.ndarray = None           # (N,) loadings for the beta band
    beta_band: float = np.inf         # |beta'X| <= band
    vol_penalty: float = 0.0          # multiplier of the system variance term (priced volatility limit); needs at most one factor

    def __post_init__(self):
        M, N = self.mu.shape
        self.kappa = np.zeros(N) if self.kappa is None else self.kappa
        self.B = np.zeros((N, 0)) if self.B is None else self.B
        self.F = np.zeros((self.B.shape[1],) * 2) if self.F is None else self.F
        self.A = [None] * M if self.A is None else self.A
        self.cap = np.full((M, N), np.inf) if self.cap is None else self.cap
        self.margin = np.full(M, np.inf) if self.margin is None else self.margin
        self.beta = np.zeros(N) if self.beta is None else self.beta
        if self.vol_penalty > 0 and self.B.shape[1] > 1:
            raise NotImplementedError("the priced system variance supports one factor")

    def Q(self, i):
        return self.gamma[i] * (np.diag(self.d) + self.B @ self.F @ self.B.T)


@dataclass
class CellSolution:
    x: np.ndarray                     # (M, N) cell positions
    X: np.ndarray                     # (N,) net system position
    prices: dict                      # net (N,), margin (M,), gross, beta, neutral (list)
    iters: int
    converged: bool
    primal_res: float
    dual_res: float
    state: dict = field(repr=False, default_factory=dict)   # warm start for the next call


def objective(p, x):
    """Value of the problem at agent positions x (M, N), constraints ignored."""
    M, N = x.shape
    val = 0.0
    for i in range(M):
        val += -p.mu[i] @ x[i] + 0.5 * x[i] @ p.Q(i) @ x[i]
    X = x.sum(0)
    val += 0.5 * p.vol_penalty * (X @ (p.d * X) + (X @ p.B) @ p.F @ (p.B.T @ X))
    return float(val + cost_fn(X - p.H, p.fee, p.kappa))


# ------------------------------------------------------------------ pieces of the solver
def _project_box_l1(t, cap, m):
    """Projection onto {|y| <= cap, sum|y| <= m}: soft-threshold by theta >= 0, then clip. Returns (y, theta).
    g(theta) = sum_i min(max(|t_i| - theta, 0), cap_i) is continuous, piecewise linear and decreasing, with breakpoints at
    |t_i| and |t_i| - cap_i, so theta solving g = m is found exactly by interpolating between the breakpoints."""
    a = np.abs(t)
    c0 = np.minimum(a, cap)
    if c0.sum() <= m:
        return np.sign(t) * c0, 0.0
    bp = np.concatenate([a, a - np.where(np.isfinite(cap), cap, 0.0), [0.0]])
    bp = np.unique(bp[bp >= 0.0])
    g = np.clip(a[None, :] - bp[:, None], 0.0, cap[None, :]).sum(1)         # g at every breakpoint (decreasing in theta)
    j = int(np.searchsorted(-g, -m))                                        # first breakpoint with g <= m
    j = min(max(j, 1), len(bp) - 1)
    g0, g1, t0, t1 = g[j - 1], g[j], bp[j - 1], bp[j]
    th = t0 if g0 == g1 else t0 + (g0 - m) / (g0 - g1) * (t1 - t0)
    return np.sign(t) * np.minimum(np.maximum(a - th, 0.0), cap), th


def _prox_net(m, t, p, lam_g, tilt, curv):
    """argmin_X fee|X-H| + kappa|X-H|^1.5 + lam_g |X| + tilt . X + (curv/2) X^2 + (1/2t)(X - m)^2, elementwise, closed form.
    The quadratic terms combine into one step tt = 1 / (1/t + curv) centred at tt (m/t - tilt); the kink of lam_g|X|
    at 0 splits the line into X > 0 and X < 0, each a plain cost prox."""
    tt = 1.0 / (1.0 / t + curv)
    mm = tt * (m / t - tilt)
    x_pos = p.H + prox_cost(mm - tt * lam_g - p.H, tt, p.fee, p.kappa)
    x_neg = p.H + prox_cost(mm + tt * lam_g - p.H, tt, p.fee, p.kappa)
    return np.where(x_pos > 0, x_pos, np.where(x_neg < 0, x_neg, 0.0))


def _x_step_system(m, t, p, tol=1e-10):
    """Net-position step: separable cost prox plus the priced system terms. Prices: the gross-cap price lam_g (smallest
    lam_g >= 0 meeting the cap), the beta-band price lam_b, and the variance penalty (diagonal part: extra curvature per coin;
    factor part: a tilt vol_penalty F (B'X) along B, solved as a scalar fixed point). All by bracketed root finding on
    monotone functions."""
    curv = p.vol_penalty * p.d
    Fb = float(p.F[0, 0]) if p.vol_penalty > 0 and p.F.size else 0.0
    B0 = p.B[:, 0] if p.B.shape[1] else np.zeros_like(m)           # factor loadings of the variance term

    def X_of(lam_g, lam_b):
        band = lam_b * p.beta                                        # the beta-band price tilts along the band's loadings
        if Fb == 0.0:
            return _prox_net(m, t, p, lam_g, band, curv)
        f = lambda e: e - B0 @ _prox_net(m, t, p, lam_g, band + p.vol_penalty * Fb * e * B0, curv)   # increasing in e
        hi = 1.0
        while f(hi) < 0 or f(-hi) > 0:
            hi *= 4.0
        e = brentq(f, -hi, hi, xtol=1e-14, rtol=1e-12)
        return _prox_net(m, t, p, lam_g, band + p.vol_penalty * Fb * e * B0, curv)

    def gross_price(lb):
        if not np.isfinite(p.gross) or np.abs(X_of(0.0, lb)).sum() <= p.gross + tol:
            return 0.0
        hi = 1.0
        while np.abs(X_of(hi, lb)).sum() > p.gross:
            hi *= 4.0
        return brentq(lambda l: np.abs(X_of(l, lb)).sum() - p.gross, 0.0, hi, xtol=1e-14, rtol=1e-12)

    def net_of(lb):
        lg = gross_price(lb)
        return X_of(lg, lb), lg

    if Fb > 0.0 and np.isfinite(p.beta_band) and np.allclose(p.beta, B0):
        # the band and the variance factor share their loadings: one scalar T tilts X along beta, X(T) is decreasing in beta'X
        # and T = lam_b + vol_penalty F e with e = beta'X, so a single root finds either the slack-band fixed point or the
        # band edge (lam_b follows). The gross cap is checked afterwards; if it binds, the general nested solve below runs.
        e_of = lambda T: p.beta @ _prox_net(m, t, p, 0.0, T * p.beta, curv)
        lamF = p.vol_penalty * Fb
        f0 = lambda T: T - lamF * e_of(T)
        hi = 1.0
        while f0(hi) < 0 or f0(-hi) > 0:
            hi *= 4.0
        T = brentq(f0, -hi, hi, xtol=1e-14, rtol=1e-12)
        lam_b = 0.0
        if abs(e_of(T)) > p.beta_band + tol:
            sgn = np.sign(e_of(T))
            g = lambda T_: sgn * e_of(T_) - p.beta_band                    # decreasing in sgn * T
            hi = 1.0
            while g(sgn * hi) > 0:
                hi *= 4.0
            T = sgn * brentq(lambda u: g(sgn * u), 0.0, hi, xtol=1e-14, rtol=1e-12)
            lam_b = T - lamF * e_of(T)
        X = _prox_net(m, t, p, 0.0, T * p.beta, curv)
        if not np.isfinite(p.gross) or np.abs(X).sum() <= p.gross + tol:
            return X, 0.0, lam_b
    X, lam_g = net_of(0.0)
    lam_b = 0.0
    if np.isfinite(p.beta_band) and abs(p.beta @ X) > p.beta_band + tol:
        s = np.sign(p.beta @ X)                                    # beta'X falls as s * lam_b grows
        f = lambda l: s * (p.beta @ net_of(s * l)[0]) - p.beta_band
        hi = 1.0
        while f(hi) > 0:
            hi *= 4.0
        lam_b = s * brentq(f, 0.0, hi, xtol=1e-14, rtol=1e-12)
        X, lam_g = net_of(lam_b)
    return X, lam_g, lam_b


class _Agent:
    """Constant matrices of one agent's step and its inner-ADMM state."""

    def __init__(self, p, i, rho, sigma):
        N = p.mu.shape[1]
        self.i = i
        self.Hinv = np.linalg.inv(p.Q(i) + (rho + sigma) * np.eye(N))
        A = p.A[i]
        self.A = None if A is None or A.shape[1] == 0 else A
        if self.A is not None:
            self.HA = self.Hinv @ self.A
            self.Sinv = np.linalg.inv(self.A.T @ self.HA)
        self.y = np.zeros(N)
        self.w = np.zeros(N)
        self.nu = np.zeros(0 if self.A is None else self.A.shape[1])
        self.theta = 0.0

    def solve(self, p, v, rho, sigma, inner):
        for _ in range(inner):
            rhs = p.mu[self.i] + rho * v + sigma * (self.y - self.w)
            x = self.Hinv @ rhs
            if self.A is not None:
                self.nu = self.Sinv @ (self.A.T @ x)
                x = x - self.HA @ self.nu
            self.y, self.theta = _project_box_l1(x + self.w, p.cap[self.i], p.margin[self.i])
            self.w = self.w + x - self.y
        return x


def solve_cells(p, rho=None, sigma=None, iters=3000, tol=1e-6, inner=10, warm=None, relax=1.7):
    """Sharing ADMM over the cells of CellProblem p. rho and sigma default to 5 x the typical curvature of the agents' own risk
    plus the system variance price, with over-relaxation 1.7 (on random test problems 3x was fastest, on the slow-converging
    problems captured from the real 4h run 6-10x was; 5x with relaxation 1.7 is the compromise. The optimum does not depend on
    either). A warm start only helps when the next problem is a small change of the last one; a warm start
    taken from a different variance price made convergence 8x slower on real problems, so the engine solves cold."""
    M, N = p.mu.shape
    curv = 5.0 * float((np.mean(p.gamma) + p.vol_penalty) * max(np.mean(p.d), 1e-12))
    rho = curv if rho is None else rho
    sigma = curv if sigma is None else sigma
    agents = [_Agent(p, i, rho, sigma) for i in range(M)]
    x = np.zeros((M, N)) if warm is None else warm["x"].copy()
    u = np.zeros(N) if warm is None else warm["u"].copy()
    zbar = x.mean(0)
    t = M / rho
    lam_g = lam_b = 0.0
    prim = dual = np.inf
    for k in range(1, iters + 1):
        xbar = x.mean(0)
        xn = np.stack([agents[i].solve(p, x[i] - xbar + zbar - u, rho, sigma, inner) for i in range(M)])
        xbar_n = xn.mean(0)
        xh = relax * xbar_n + (1.0 - relax) * zbar                  # over-relaxation (relax = 1: plain ADMM)
        X, lam_g, lam_b = _x_step_system(M * (xh + u), t, p)
        z_new = X / M
        u = u + xh - z_new
        prim = float(np.linalg.norm(xbar_n - z_new))
        dual = float(rho * np.linalg.norm(z_new - zbar))
        x, zbar = xn, z_new
        # relative stopping rule (Boyd section 3.3): residuals small against the size of what is being solved. The old absolute
        # rule (1e-7) stopped real problems (positions of order 0.01) after 10 iterations. At tol 1e-6 the NET position is accurate
        # to about 1e-6 while the split of it between agents (offsetting positions cost only their own risk) converges more slowly,
        # about 9% at 1e-6 and 1% at 1e-10: account attribution carries that noise, the system P&L does not.
        scale_p = max(float(np.linalg.norm(xn)), float(np.linalg.norm(z_new)), 1e-9)      # the cells, not only their net: offsetting
        #                                                                         positions between agents are invisible in the net
        scale_d = max(float(np.linalg.norm(rho * u)), 1e-9)
        if prim <= tol * scale_p and dual <= tol * scale_d:
            break
    prices = {"net": rho * u, "margin": np.array([sigma * a.theta for a in agents]), "gross": lam_g, "beta": lam_b,
              "vol": p.vol_penalty,
              "neutral": [a.nu.copy() for a in agents]}
    return CellSolution(x=x, X=x.sum(0), prices=prices, iters=k, converged=prim <= tol * scale_p and dual <= tol * scale_d,
                        primal_res=prim, dual_res=dual, state={"x": x.copy(), "u": u.copy()})


def solve_uncoupled(p):
    """Closed form when nothing couples the agents (no trading cost, capacities, margin or system limits): every agent
    stakes x = Q^-1 (mu - A nu), the Kelly stake on its own belief with its neutrality constraints."""
    out = np.zeros_like(p.mu)
    for i in range(p.mu.shape[0]):
        Qi = np.linalg.inv(p.Q(i))
        x = Qi @ p.mu[i]
        A = p.A[i]
        if A is not None and A.shape[1]:
            x = x - Qi @ A @ np.linalg.solve(A.T @ Qi @ A, A.T @ x)
        out[i] = x
    return out


# ------------------------------------------------------------------ one-node reference
def solve_reference(p, smooth=1e-9):
    """The same problem solved by SLSQP on (positive part, negative part) of every cell. For tests: small problems
    only. The L1 constraints use the usual split, the fee kink a smoothing of width `smooth`."""
    M, N = p.mu.shape
    nv = 2 * M * N + N
    def unpack(z):
        return z[:M * N].reshape(M, N), z[M * N:2 * M * N].reshape(M, N), z[2 * M * N:]
    def fun(z):
        pp, nn, _ = unpack(z)
        x = pp - nn
        r = x.sum(0) - p.H
        fee = p.fee * np.sqrt(r * r + smooth ** 2).sum()
        X = x.sum(0)
        var = 0.5 * p.vol_penalty * (X @ (p.d * X) + (X @ p.B) @ p.F @ (p.B.T @ X))
        return sum(-p.mu[i] @ x[i] + 0.5 * x[i] @ p.Q(i) @ x[i] for i in range(M)) + fee + var + (p.kappa * (r * r + smooth ** 2) ** 0.75).sum()
    cons = []
    for i in range(M):
        if p.A[i] is not None and p.A[i].shape[1]:
            cons.append({"type": "eq", "fun": lambda z, i=i: p.A[i].T @ (unpack(z)[0][i] - unpack(z)[1][i])})
        if np.isfinite(p.margin[i]):
            cons.append({"type": "ineq", "fun": lambda z, i=i: p.margin[i] - (unpack(z)[0][i] + unpack(z)[1][i]).sum()})
    if np.isfinite(p.gross):
        cons.append({"type": "ineq", "fun": lambda z: p.gross - unpack(z)[2].sum()})
        cons.append({"type": "ineq", "fun": lambda z: unpack(z)[2] - (unpack(z)[0] - unpack(z)[1]).sum(0)})
        cons.append({"type": "ineq", "fun": lambda z: unpack(z)[2] + (unpack(z)[0] - unpack(z)[1]).sum(0)})
    if np.isfinite(p.beta_band):
        cons.append({"type": "ineq", "fun": lambda z: p.beta_band - p.beta @ (unpack(z)[0] - unpack(z)[1]).sum(0)})
        cons.append({"type": "ineq", "fun": lambda z: p.beta_band + p.beta @ (unpack(z)[0] - unpack(z)[1]).sum(0)})
    ub = np.where(np.isfinite(p.cap), p.cap, 1e6)
    bounds = [(0, b) for b in ub.ravel()] * 2 + [(0, None)] * N
    res = minimize(fun, np.zeros(nv), method="SLSQP", bounds=bounds, constraints=cons,
                   options={"maxiter": 2000, "ftol": 1e-13})
    pp, nn, _ = unpack(res.x)
    return pp - nn
