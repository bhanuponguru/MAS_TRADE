# 010. How the shield's cut is split across agents

Date: 2026-11-05   Decision: [0029](../decisions/0029-shield-allocation-across-agents.md)   Code: working tree on top of `7eff0f1`
Command (at the time): `uv run python run_safety_experiments.py --exp d029`. That option no longer exists; the `risk` variant can only be re-run after restoring the code below   Raw: `results/experiments/safety/{flat,hier,adversary}_*.csv`, `adversary_agent_scales.csv`

## Question
When the shield must cut exposure, should it cut every agent alike (`uniform`) or take the cut from the agents that contribute most to portfolio risk (`risk`)? In particular, does `risk` cut a compromised agent harder?

## Variants
| Variant | Config | What it does |
|---|---|---|
| rebalance+uniform | `safety=True` | Every agent's portfolio scaled by the same factor |
| rebalance+risk | `safety=True, safety_alloc="risk"` | Agent i keeps `clip(1 - k * RC_i+/max RC+, 0, 1)` of its exposure, RC_i = Euler risk contribution; `k` set by bisection so total vol equals what `uniform` would give; hedging agents (RC <= 0) are not cut |
| daily+uniform / daily+risk | `+ safety_daily=True` | Same two, with daily checks ([exp 009](009-intra-period-safety-checks.md)) |

## Setup
As in experiment 001, plus a third scenario: the 6 default agents **plus one compromised agent** (`AdversarialAgent`: bets all its capital on one random stock, random side, every rebalance; frozen in consensus, so it is not pulled toward the others).

## Results: no adversary (flat MAS)
| Variant | dev Sharpe | dev MaxDD | dev viol dd | dev viol vol | test Sharpe | test viol dd | turnover |
|---|---|---|---|---|---|---|---|
| rebalance+uniform | 0.676 | -21.1% | 3.2% | 14.0% | 1.086 | 0.4% | 3.81 |
| rebalance+risk | 0.680 | -21.3% | 4.0% | 14.3% | 1.040 | 0.4% | 3.82 |
| daily+uniform | 0.656 | -18.6% | 1.3% | 11.2% | 1.151 | 0% | 4.38 |
| daily+risk | 0.672 | -18.7% | 1.3% | 11.3% | 1.085 | 0.1% | 4.35 |
Hierarchical: same picture (dev Sharpe 0.691 vs 0.710, identical violations).

## Results: with one compromised agent (flat MAS)
| Variant | dev Sharpe | dev MaxDD | dev viol dd | dev viol vol | test Sharpe | test MaxDD | test viol dd |
|---|---|---|---|---|---|---|---|
| no shield | 0.676 | -27.5% | 9.4% | 17.3% | 0.896 | -18.9% | 1.9% |
| rebalance+uniform | 0.641 | -25.0% | 1.9% | 10.6% | **1.029** | -16.0% | **0.3%** |
| rebalance+risk | 0.657 | -24.2% | 2.4% | 10.9% | 0.860 | -16.5% | **10.5%** |
| daily+uniform | 0.652 | -22.0% | 1.2% | 8.2% | 1.026 | -14.6% | 0% |
| daily+risk | 0.547 | -20.8% | 2.6% | 6.6% | 0.851 | -16.8% | 14.6% |

Exposure kept per agent on rebalances where the shield cut (1 = untouched):
| Variant | Momentum | MeanRev | Shrinkage | AR1 | EWMATrend | LowVol | **Adversary** |
|---|---|---|---|---|---|---|---|
| rebalance+uniform | 0.55 | 0.55 | 0.55 | 0.55 | 0.55 | 0.55 | 0.55 |
| rebalance+risk | 0.45 | 0.49 | 0.42 | 0.49 | 0.52 | 0.52 | **0.67** |
| daily+risk | 0.43 | 0.50 | 0.40 | 0.49 | 0.50 | 0.51 | **0.63** |

## Findings
1. Without an adversary, `risk` and `uniform` are the same within noise. The honest agents hold similar diversified long-short books, so their risk contributions are similar and the cut ends up near-uniform anyway.
2. With an adversary, `risk` cuts the adversary **least**. Its single random stock bet is mostly idiosyncratic: it adds little to total variance at the margin (and sometimes offsets the others), so Euler risk contribution calls it "low risk". The honest agents, whose books are correlated with the system, get cut instead, which makes the adversary's share of the book larger. Result: test-period drawdown violations 0.3% -> 10.5%, Sharpe 1.03 -> 0.86.
3. Risk contribution measures "how much variance would fall if I cut you", not "who is misbehaving". The trust scores are the system's existing measure of misbehaviour.

## Outcome
Kept `uniform`; decision 0029 accepted and the `risk` code removed (2026-11-05). The `risk` code (~35 lines) can be removed once the team agrees. If agent-aware cuts are wanted for the Week 7 "safety <-> optimisation interaction", the next candidate is cutting low-**trust** agents first (option 3 in 0029), tested with this same adversary scenario.

## Appendix: removed `risk` allocation (from `mas_trade/safety.py`, never committed)
It was called from `supervise` when `cfg.safety_alloc == "risk"` and `lam < 1`, as `lam_i = allocate_cut(books_capped[:, el], Sig, lam * vol_capped, ppy)`, with `books` = per-agent positions as fractions of total capital (A x N) and the returned per-agent `lam_i` applied as `S = lam_i[:, None] * m[None, :]`. It uses the helper `_vol(h, Sig, ppy) = sqrt(max(h' Sig h, 0) * ppy)`.
```python
def allocate_cut(books, Sig, target, ppy, iters=60):
    """Decision 3, alloc="risk": cut the agents that cause the risk. books (A x n) are per-agent
    positions (fractions of total capital), the system holds books.sum(0). Euler risk contribution
    RC_i = b_i' Sig h / h' Sig h (sums to 1). Agent i keeps lam_i = clip(1 - k * RC_i+ / max RC+, 0, 1);
    k is found by bisection so that the system's vol hits `target`. Agents that hedge (RC_i <= 0)
    are not cut. If cutting every risk-adding agent is not enough, all books are scaled down
    uniformly on top, so vol <= target is always guaranteed. Returns lam (A,)."""
    A = len(books)
    h = books.sum(0)
    v0 = _vol(h, Sig, ppy)
    if v0 <= target:
        return np.ones(A)
    rc = books @ Sig @ h / max(h @ Sig @ h, 1e-300)
    r = np.clip(rc, 0, None)
    r = r / r.max() if r.max() > 0 else r
    lam_of = lambda k: np.clip(1 - k * r, 0.0, 1.0)
    vol_of = lambda k: _vol(lam_of(k) @ books, Sig, ppy)
    k_hi = 1.0 / r[r > 0].min() if (r > 0).any() else 0.0
    if vol_of(k_hi) > target:                    # even removing all risk-adding agents is not enough
        lam = lam_of(k_hi)
        v = vol_of(k_hi)
        return lam * (target / v if v > 0 else 0.0)
    lo, hi = 0.0, k_hi
    for _ in range(iters):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if vol_of(mid) > target else (lo, mid)
    lam = lam_of(hi)
    v = vol_of(hi)
    return lam * min(1.0, target / v) if v > 0 else lam
```
