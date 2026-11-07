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
    target_vol: float = 0.20    # system volatility limit (annual), enforced through the risk aversion of the joint problem

    @property
    def ppy(self):
        return 365.0 * self.bpd

    @classmethod
    def for_tier(cls, bar, **kw):
        bpd, _, reb_h = TIERS[bar]
        return replace(cls(bpd=bpd, rebal_bars=max(1, round(reb_h / 24 * bpd))), **kw)
