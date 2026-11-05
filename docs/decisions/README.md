# Decision log

Every design choice is recorded here, so we can see why the system is the way it is and roll a choice back if it turns out worse or too complex. Comparisons between options live in [../experiments/](../experiments/).

## Rules
- One file per decision: `NNNN-short-name.md`, numbered in the order decisions are made and never renumbered from now on. The `D0NN` tags in code comments refer to these numbers.
- New behaviour goes behind a `Config` flag, and the old behaviour stays the default until the decision is **Accepted**. Rolling back = flipping the flag. Removing code is a separate, later decision.
- Status is one of: **Proposed** (nothing settled), **Open** (provisional value in use, still to be settled), **Recommended** (an experiment supports it, waiting for team sign-off), **Accepted**, **Rejected**, **Superseded by NNNN**.
- Never choose an option by looking at the test period (2023 onward for stocks, the sealed holdout for crypto). Decide on the dev period; the test period is only a check.

## Index (in the order the decisions were made)
Dates are commit dates. Within one commit the order is logical (data -> agents -> consensus -> capital -> evaluation), not exact. Where the original reasoning was never written down, a record says **(inferred)**. The log was started on 2026-11-05 and filled in back to the first commit then; numbers were assigned once, in date order, before the log was first committed.

### Initial system: 2026-10-18 (`b48056d`) and tooling 2026-10-20
| # | Decision | Status | Flag / where | Evidence |
|---|---|---|---|---|
| [0001](0001-us-stock-universe.md) | 20 US large caps, daily yfinance data, SPY benchmark | Accepted | `Config.tickers` | — |
| [0002](0002-heterogeneous-agents.md) | Six simple forecasting agents, `w = mu/sum|mu|`; adversary model | Accepted | `agents.py` | [exp 001](../experiments/001-stock-baseline.md) |
| [0003](0003-trust-from-forecast-reward.md) | Trust = forecast P(agent profitable) from its standalone record | Accepted | `trust_*` | — |
| [0004](0004-wmsr-consensus-with-pinning.md) | Trust-weighted W-MSR consensus with pinning | Accepted | `K, F, pin, graph` | [exp 003](../experiments/003-adversary-resilience.md) |
| [0005](0005-admm-mode.md) | ADMM consensus as an alternative mode | Accepted | `mode="admm"` | [exp 002](../experiments/002-wmsr-vs-admm.md) |
| [0006](0006-capital-flows-through-w.md) | Agents own capital; it moves through W transpose | Accepted | `eta, c_min, F_capital` | [exp 001](../experiments/001-stock-baseline.md), [003](../experiments/003-adversary-resilience.md) |
| [0007](0007-netting-and-costs.md) | Net agents' trades; costs on the net trade; 21-day rebalance | Accepted | `cost_bps, rebalance_days` | — |
| [0008](0008-no-lookahead-invariant.md) | No lookahead is a tested invariant | Accepted | `test_no_lookahead` | tests |
| [0009](0009-tooling.md) | uv, data/results out of git, all knobs in Config | Accepted | — | — |

### Hierarchy, 24/7 crypto and the v2 engine: 2026-11-01 (`47fa8ee`) and 2026-11-05 (`92ccc47`)
| # | Decision | Status | Flag / where | Evidence |
|---|---|---|---|---|
| [0010](0010-hierarchy.md) | Two-level hierarchy with per-asset subagents | Accepted (opt-in) | `hierarchical` | [exp 004](../experiments/004-hierarchy.md) |
| [0011](0011-auto-eta.md) | Optional risk/cost-aware reallocation speed | Accepted (opt-in) | `eta="auto"` | tests only |
| [0012](0012-engine-24-7-generalisation.md) | Engine generalised to 24/7 perps (eligibility, funding, bars) | Accepted | `for_tier` | tests |
| [0013](0013-crypto-data-pipeline.md) | Binance USD-M data, point-in-time, survivorship-free universe | Accepted | `crypto_data.py` | tests |
| [0014](0014-crypto-benchmark-protocol.md) | v1 crypto benchmark: dev/holdout, bootstrap vs BTC | Accepted | `run_crypto_benchmark.py` | [exp 005](../experiments/005-v1-crypto-benchmark.md) (not recorded) |
| [0015](0015-v2-absolute-return-engine.md) | Second engine (v2) judged in absolute terms | Accepted | `mas_trade/v2/` | [exp 006](../experiments/006-v2-dev-findings.md) |
| [0016](0016-v2-neutral-books.md) | v2 books: rank-gauss, dollar/beta-neutral, vol-targeted | Accepted | `v2/books.py` | [exp 006](../experiments/006-v2-dev-findings.md) |
| [0017](0017-v2-combiners.md) | v2 combiners compared (EW ... C3 fusion) | Accepted | `v2/combiners.py` | [exp 006](../experiments/006-v2-dev-findings.md) |
| [0018](0018-v2-costs-and-min-adv.md) | v2 fee + sqrt-impact costs; liquidity floor | Accepted | `min_adv` | [exp 006](../experiments/006-v2-dev-findings.md) |
| [0019](0019-v2-cost-aware-smoothing.md) | v2 cost-aware partial adjustment | Accepted (opt-in) | `--smooth` | — |
| [0020](0020-v2-research-hygiene.md) | Sealed holdout, trial log, deflated Sharpe | Accepted | `--unseal` | — |
| [0021](0021-v2-decentralised-admm.md) | v2 decentralised consensus-ADMM combiner on a ring | Accepted | `admm_*` | [exp 007](../experiments/007-v2-admm-combiner.md) |

### Phase 1: safety layer and centralised baseline, 2026-11-05
| # | Decision | Status | Flag / where | Evidence |
|---|---|---|---|---|
| [0022](0022-build-on-v1-engine.md) | Build the proposal's system on v1; freeze v2 | Accepted | — | — |
| [0023](0023-stl-implementation.md) | Hand-written quantitative STL, normalised robustness | Accepted | `safety.py` | tests |
| [0024](0024-monitor-always-shield-opt-in.md) | Monitor always runs; shield opt-in | Accepted | `safety` | — |
| [0025](0025-shield-mechanism.md) | Shield = scale toward cash | Accepted | `supervise` | [exp 008](../experiments/008-stl-shield-baseline.md) |
| [0026](0026-safety-thresholds.md) | Safety limits (mandate-based) | Accepted | `safety_*` | — |
| [0027](0027-centralised-baseline.md) | Centralised baseline = ADMM's fixed point | Accepted | `central_mv` | [exp 002](../experiments/002-wmsr-vs-admm.md), [008](../experiments/008-stl-shield-baseline.md) |
| [0028](0028-intra-period-safety-checks.md) | Shield also checks every bar (de-risk only) | Accepted (default on) | `safety_daily` | [exp 009](../experiments/009-intra-period-safety-checks.md) |
| [0029](0029-shield-allocation-across-agents.md) | Shield cuts every agent alike; `risk` option removed | Accepted | — | [exp 010](../experiments/010-shield-allocation-across-agents.md) |
| [0030](0030-skip-market-wide-dump-holes.md) | Universe skips days missing for every symbol (dump holes) | Accepted | `build_universe` | test, [exp 005](../experiments/005-v1-crypto-benchmark.md) |
| [0031](0031-crypto-drawdown-limit.md) | Crypto drawdown limit 30% (same drawdown/vol ratio as stocks) | Proposed | `for_tier` | [exp 005](../experiments/005-v1-crypto-benchmark.md) |

## Template
```
# NNNN. Title
Status: ...   Date: YYYY-MM-DD   Flag: Config.xxx (default ...)
## Context      why a choice is needed
## Options      each option, one paragraph, with its cost in complexity
## Decision     what we chose (or "pending") and why
## Consequences what changes, what we give up
## Rollback     exactly how to undo it
```
