"""All tunable settings in one place."""
from dataclasses import dataclass, field, replace

TICKERS = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "NVDA", "JPM", "BAC", "GS", "XOM", "CVX",
    "JNJ", "PFE", "UNH", "PG", "KO", "WMT", "HD", "CAT", "DIS", "VZ",
]

# bar -> (bars per day, lookback in days, rebalance every this many hours)
TIERS = {"1d": (1, 365, 14 * 24), "4h": (6, 120, 5 * 24), "1h": (24, 60, 48), "15m": (96, 20, 12), "5m": (288, 7, 4)}


@dataclass
class Config:
    # data
    tickers: list = field(default_factory=lambda: list(TICKERS))
    benchmark: str = "SPY"
    start: str = "2015-01-01"
    end: str = "2025-12-31"
    # schedule: all lengths below are in BARS (trading days for stocks); see Config.for_tier
    periods_per_year: float = 252.0  # bars per year, used to annualise
    lookback: int = 252        # T: history window used by every forecast
    rebalance_days: int = 21   # H: hold period between rebalances
    warmup: int = 252          # days of standalone agent track record before trading starts
    # forecasted reward -> trust
    trust_window: int = 252    # days of standalone agent returns used for the forecast
    trust_halflife: float = 126.0
    trust_power: float = 1.0   # s_i = p_i ** power (higher = sharper preference for good agents)
    # consensus
    mode: str = "wmsr"         # "wmsr" (W-MSR consensus) or "admm" (ADMM consensus)
    K: int = 10                # consensus rounds per rebalance
    F: int = 1                 # W-MSR: number of suspicious values trimmed on each side (0 = plain)
    pin: float = 0.3           # b: pull of each agent back to its own strategy portfolio
    graph: str = "complete"    # "complete" or "er" (Erdos-Renyi)
    er_p: float = 0.6
    admm_gamma: float = 1.0
    admm_rho: float = 1.0
    # capital reallocation (through W transpose)
    eta: object = 0.5          # speed of capital reallocation between strategies, or "auto" (risk/cost-aware)
    c_min: float = 0.02        # floor on each agent's share of total capital
    F_capital: int = 0         # W-MSR trimming on the capital step (on trust scores)
    init_capital: float = 1_000_000.0
    # hierarchy: one subagent per asset inside each strategy, with its own capital consensus
    hierarchical: bool = False
    eta_sub: object = 0.5      # speed of reallocation between a strategy's subagents, or "auto" (risk/cost-aware)
    risk_aversion: float = 3.0  # gamma in eta/eta_sub="auto": eta = g var H / (g var H + lam)
    g_min: float = 0.005       # floor on each subagent's share of its strategy's capital (N * g_min < 1)
    F_sub: int = 0             # W-MSR trimming on the subagent trust scores
    sub_graph: str = "complete"  # "complete" or "corr" (link assets with |corr| >= corr_threshold)
    corr_threshold: float = 0.3
    # frictions
    cost_bps: float = 5.0      # per $ traded
    short_fee_bps: float = 0.0  # annual borrow fee on short notional
    seed: int = 0

    @classmethod
    def for_tier(cls, bar, **kw):
        """Config for 24/7 crypto/perp data on a given bar size; schedules are set in time units
        and converted to bars. Cost is taker fee + slippage per $ traded (an untuned default)."""
        bpd, look_d, reb_h = TIERS[bar]
        cfg = cls(tickers=[], benchmark="BTCUSDT", periods_per_year=365.0 * bpd,
                  lookback=round(look_d * bpd), warmup=round(look_d * bpd),
                  trust_window=round(look_d * bpd), trust_halflife=look_d * bpd / 2,
                  rebalance_days=max(1, round(reb_h / 24 * bpd)), cost_bps=7.0, start="2020-01-01")
        return replace(cfg, **kw)


@dataclass
class V2Config:
    """Settings for the v2 engine (mas_trade/v2). Windows are in DAYS; bars = days * bpd."""
    bpd: int = 1                # bars per day
    rebal_bars: int = 14        # H: bars between rebalances
    # agents
    mom_days: float = 90.0
    skip_days: float = 7.0
    rev_days: float = 7.0
    carry_days: float = 14.0
    size_days: float = 30.0
    timing_days: float = 60.0
    # risk model and scaling
    beta_days: float = 60.0
    cov_days: float = 60.0
    adv_days: float = 30.0
    hist_days: float = 120.0    # window handed to agents; must cover every window above
    target_vol: float = 0.20    # annual
    gross_cap: float = 3.0
    # costs
    fee_bps: float = 5.0        # taker fee per $ traded
    impact_k: float = 1.0       # slippage = k * daily vol * sqrt(trade $ / ADV $)
    aum: float = 1_000_000.0
    risk_aversion: float = 3.0   # gamma in the cost-aware partial adjustment eta = a / (a + lam)
    regime_days: float = 180.0   # expected length of a strategy's good/bad regime: fixed-share rate = H / regime
    ic_prior: float = 10.0       # pseudo-observations of IC = 0 shrinking the EWMA IC estimate
    z_window: int = 24           # rebalances pooled for the score correlation R_z
    z_shrink: float = 0.2        # shrink R_z toward the identity
    fusion_cov: str = "diag"    # risk model inside the mean-variance book: "diag" (per-asset variance) or "lw" (full Ledoit-Wolf)
    min_adv: float = 1_000_000.0  # tradable only if trailing median daily dollar volume >= this
    # decentralised consensus ADMM combiner (v2/admm.py); rho, sigma and the iteration budget only set convergence
    admm_graph: str = "ring"    # agent communication graph: ring | complete
    admm_rho: float = 1.0       # consensus penalty, in units of mean(gamma * S)
    admm_sigma: float = 1.0     # penalty of the inner split that carries the non-smooth trading cost
    admm_iters: int = 1000
    admm_tol: float = 1e-6      # stop when disagreement and step size are <= tol * max |mean x|
    admm_inner: int = 3
    admm_cost_mult: float = 1.0  # trading cost weight against one holding period of expected return
    # schedule
    min_assets: int = 8         # no cross-section below this many tradable assets
    burn_days: float = 90.0     # every combiner starts this long after the first usable rebalance
    ic_halflife: float = 12.0   # in rebalances
    holdout_months: int = 12

    @property
    def ppy(self):
        return 365.0 * self.bpd

    @classmethod
    def for_tier(cls, bar, **kw):
        bpd, _, reb_h = TIERS[bar]
        return replace(cls(bpd=bpd, rebal_bars=max(1, round(reb_h / 24 * bpd))), **kw)
