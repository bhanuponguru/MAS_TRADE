"""All tunable settings in one place."""
from dataclasses import dataclass, replace

# bar -> (bars per day, lookback in days, rebalance every this many hours)
TIERS = {"1d": (1, 365, 14 * 24), "4h": (6, 120, 5 * 24), "1h": (24, 60, 48), "15m": (96, 20, 12), "5m": (288, 7, 4)}


@dataclass
class EngineConfig:
    """Settings of the engine. Windows are in DAYS; bars = days * bpd. Fields are added when the phase that
    uses them is built, not before."""
    bpd: int = 1                # bars per day
    rebal_bars: int = 14        # H: bars between rebalances
    min_adv: float = 1_000_000.0  # tradable only if trailing median daily dollar volume >= this
    min_assets: int = 8         # no cross-section below this many tradable assets
    # costs
    fee_bps: float = 5.0        # taker fee per $ traded
    impact_k: float = 1.0       # slippage = k * daily vol * sqrt(trade $ / ADV $)
    aum: float = 1_000_000.0
    holdout_months: int = 12    # the last months are SEALED: reported only with --unseal
    # windows (days; bars = days * bpd)
    hist_days: float = 120.0    # history handed to the agents; must cover every window they use
    cov_days: float = 60.0      # per-coin variance window
    beta_days: float = 60.0     # BTC beta window
    adv_days: float = 30.0      # trailing median daily dollar volume
    burn_days: float = 90.0     # no trading until this long after the first usable rebalance (calibration warm-up)
    # market and cells (pre-registered, not tuned)
    kelly: float = 0.5          # Kelly fraction of every agent
    leverage: float = 3.0       # margin: sum_a |x_ia| <= leverage x wealth
    gross: float = 3.0          # system gross cap, multiple of equity
    participation: float = 0.05  # capacity: a position may be at most this share of a coin's daily volume
    wealth_floor: float = 0.02  # minimum wealth share of an agent (a liveness device)
    target_vol: float = 0.20    # system volatility limit (annual): a priced variance term in the joint problem
    beta_band: float = 0.25     # system net BTC-beta exposure within +-this multiple of equity (a priced constraint)
    belief_bound_k: float = 6.0  # sanity spec: |belief| within this many robust standard deviations of the agent's past beliefs
    calibration_floor: float = 0.5   # agent spec: slope of realised returns on its beliefs at least this; the margin scales its Kelly fraction
    calibration_window: int = 52     # rebalances of past beliefs behind the slope
    calibration_min_obs: int = 1500  # (period, coin) observations needed before the spec acts
    # coordination of the joint problem (decision 0042)
    consensus: str = "hub"      # "hub": one node averages and prices (cells_admm); "graph": neighbours only (graph_admm)
    topology: str = "complete"  # graph of the agents when consensus = "graph": complete, ring, line, star, random
    gossip_rounds: int = 1      # neighbour-averaging rounds per ADMM iteration (graph only)
    topology_seed: int = 0      # seed of the "random" topology
    # resilience (experiment 021); all off by default
    link_fail: float = 0.0      # graph only: every edge is down with this probability in every gossip round
    offline: tuple = ()         # ((agent name, first day, last day), ...): the agent is out; its positions are closed and the
                                # others solve without it (graph: on the graph without that node)
    faulty: tuple = ()          # agent names that misbehave: they hold nothing; in graph mode they send false estimates
    attack: float = 0.0         # what a faulty agent adds to every value it sends (initial-equity units)
    trim: int = 0               # graph only: F of the W-MSR (trimmed) mixing step; 0 = plain mixing
    detect: int = 0             # graph only: if > 0, detect and isolate a misbehaving agent (graph_admm.solve_cells_resilient):
                                # flagged after this many iterations in a row of extreme values; isolated agents stay out

    @property
    def ppy(self):
        return 365.0 * self.bpd

    @classmethod
    def for_tier(cls, bar, **kw):
        bpd, _, reb_h = TIERS[bar]
        return replace(cls(bpd=bpd, rebal_bars=max(1, round(reb_h / 24 * bpd))), **kw)
