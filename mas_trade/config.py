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

    @property
    def ppy(self):
        return 365.0 * self.bpd

    @classmethod
    def for_tier(cls, bar, **kw):
        bpd, _, reb_h = TIERS[bar]
        return replace(cls(bpd=bpd, rebal_bars=max(1, round(reb_h / 24 * bpd))), **kw)
