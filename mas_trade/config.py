"""All tunable settings in one place."""
from dataclasses import dataclass, field

TICKERS = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "NVDA", "JPM", "BAC", "GS", "XOM", "CVX",
    "JNJ", "PFE", "UNH", "PG", "KO", "WMT", "HD", "CAT", "DIS", "VZ",
]


@dataclass
class Config:
    # data
    tickers: list = field(default_factory=lambda: list(TICKERS))
    benchmark: str = "SPY"
    start: str = "2015-01-01"
    end: str = "2025-12-31"
    # schedule (trading days)
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
    eta: float = 0.5           # speed of capital reallocation
    c_min: float = 0.02        # floor on each agent's share of total capital
    F_capital: int = 0         # W-MSR trimming on the capital step (on trust scores)
    init_capital: float = 1_000_000.0
    # frictions
    cost_bps: float = 5.0      # per $ traded
    short_fee_bps: float = 0.0  # annual borrow fee on short notional
    seed: int = 0
