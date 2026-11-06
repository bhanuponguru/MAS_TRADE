"""Simulated markets with planted skill, for validating the mechanisms where the truth is known.

Coin a earns, in period t, r = alpha + beta_a m + eps with alpha ~ N(0, sigma_alpha^2) the (latent) expected return,
m a common factor and eps idiosyncratic. An agent with skill rho sees the signal s = rho alpha + sqrt(1-rho^2)
sigma_alpha eta and believes E[alpha | s] = rho_claim s, so its belief is calibrated when rho_claim = rho. Scaling the
belief by kappa > 1 makes it over-confident.
"""
from dataclasses import dataclass

import numpy as np


@dataclass
class World:
    R: np.ndarray            # (T, N) returns
    alpha: np.ndarray        # (T, N) latent expected returns
    B: np.ndarray            # (N,) factor loadings
    factor: np.ndarray       # (T,)
    sigma_alpha: float
    sigma_eps: float
    factor_vol: float

    @property
    def T(self):
        return self.R.shape[0]

    @property
    def N(self):
        return self.R.shape[1]

    def risk(self):
        """(d, B, F): idiosyncratic variance per coin, loadings (N, 1) and factor variance (1, 1) of this world."""
        return np.full(self.N, self.sigma_eps ** 2), self.B[:, None], np.array([[self.factor_vol ** 2]])


def make_world(T, N=60, sigma_alpha=0.005, sigma_eps=0.06, factor_vol=0.08, seed=0):
    rng = np.random.default_rng(seed)
    B = rng.uniform(0.5, 1.5, N)
    m = rng.normal(0, factor_vol, T)
    alpha = rng.normal(0, sigma_alpha, (T, N))
    R = alpha + m[:, None] * B + rng.normal(0, sigma_eps, (T, N))
    return World(R, alpha, B, m, sigma_alpha, sigma_eps, factor_vol)


def make_beliefs(world, rho_true, rho_claim, kappa=1.0, seed=0):
    """(T, N) beliefs of one agent. rho_true may be a scalar or a (T,) path (skill that appears or decays)."""
    rng = np.random.default_rng(seed)
    rho = np.broadcast_to(np.asarray(rho_true, float), (world.T,))[:, None]
    s = rho * world.alpha + np.sqrt(1 - rho ** 2) * world.sigma_alpha * rng.normal(size=world.alpha.shape)
    return kappa * rho_claim * s


def kelly_growth(world, rho_true, rho_claim, f, kappa=1.0):
    """Expected per-period log-growth of an agent staking fraction f of full Kelly on its belief (no neutrality
    or factor terms): q f_eff (1 - f_eff / 2) - (the mismatch term), with q = N sigma_alpha^2 / sigma_eps^2.
    E[return] = f kappa rho_claim rho_true q, Var = (f kappa rho_claim)^2 q."""
    q = world.N * world.sigma_alpha ** 2 / world.sigma_eps ** 2
    return f * kappa * rho_claim * rho_true * q - 0.5 * (f * kappa * rho_claim) ** 2 * q


def make_regime_signals(world, rho_on, rho_off, p_stay=0.97, z_noise=0.5, seed=0):
    """Signals of an agent whose skill depends on a hidden two-state Markov regime. Returns (signal (T, N), z (T,), rho (T,)):
    z is an observable noisy indicator of the state, known at the time the period starts. E[alpha | signal] = rho_t x signal."""
    rng = np.random.default_rng(seed)
    state = np.zeros(world.T, int)
    state[0] = rng.random() < 0.5
    for t in range(1, world.T):
        state[t] = state[t - 1] if rng.random() < p_stay else 1 - state[t - 1]
    rho = np.where(state == 1, rho_on, rho_off)
    signal = rho[:, None] * world.alpha + np.sqrt(1 - rho[:, None] ** 2) * world.sigma_alpha * rng.normal(size=world.alpha.shape)
    z = state + rng.normal(0, z_noise, world.T)
    return signal, z, rho
