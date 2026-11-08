# Decision log

Every design choice is recorded here, so we can see why the system is the way it is and roll a choice back if it turns out worse or too complex. Comparisons between options live in [../experiments/](../experiments/).

## Rules
- One file per decision: `NNNN-short-name.md`, numbered in the order decisions are made and never renumbered from now on. The `D0NN` tags in code comments refer to these numbers.
- Until 0032, new behaviour went behind a `Config` flag with the old behaviour as default. Since 0032 the system is one implementation: a decision that replaces something deletes the old code, and rolling back means returning to a git tag or commit named in the record, not keeping both paths alive.
- Status is one of: **Proposed** (nothing settled), **Open** (provisional value in use, still to be settled), **Recommended** (an experiment supports it, waiting for team sign-off), **Accepted**, **Rejected**, **Superseded by NNNN**.
- Never choose an option by looking at the test period / the sealed holdout. Decide on the dev period; the test period is only a check.

## Index (in the order the decisions were made)
Dates are commit dates. Within one commit the order is logical (data -> agents -> consensus -> capital -> evaluation), not exact. Where the original reasoning was never written down, a record says **(inferred)**. The log was started on 2026-11-05 and filled in back to the first commit then; numbers were assigned once, in date order, before the log was first committed.

### Initial system: 2026-10-18 (`b48056d`) and tooling 2026-10-20
| # | Decision | Status | Flag / where | Evidence |
|---|---|---|---|---|
| [0001](0001-us-stock-universe.md) | 20 US large caps, daily yfinance data, SPY benchmark | Superseded by [0032](0032-replace-v1-v2.md) | `Config.tickers` | — |
| [0002](0002-heterogeneous-agents.md) | Six simple forecasting agents, `w = mu/sum abs(mu)`; adversary model | Superseded by [0032](0032-replace-v1-v2.md) | `agents.py` | [exp 001](../experiments/001-stock-baseline.md) |
| [0003](0003-trust-from-forecast-reward.md) | Trust = forecast P(agent profitable) from its standalone record | Superseded by [0032](0032-replace-v1-v2.md) | `trust_*` | — |
| [0004](0004-wmsr-consensus-with-pinning.md) | Trust-weighted W-MSR consensus with pinning | Superseded by [0032](0032-replace-v1-v2.md) | `K, F, pin, graph` | [exp 003](../experiments/003-adversary-resilience.md) |
| [0005](0005-admm-mode.md) | ADMM consensus as an alternative mode | Superseded by [0032](0032-replace-v1-v2.md) | `mode="admm"` | [exp 002](../experiments/002-wmsr-vs-admm.md) |
| [0006](0006-capital-flows-through-w.md) | Agents own capital; it moves through W transpose | Superseded by [0032](0032-replace-v1-v2.md) | `eta, c_min, F_capital` | [exp 001](../experiments/001-stock-baseline.md), [003](../experiments/003-adversary-resilience.md) |
| [0007](0007-netting-and-costs.md) | Net agents' trades; costs on the net trade; 21-day rebalance | Superseded by [0032](0032-replace-v1-v2.md) | `cost_bps, rebalance_days` | — |
| [0008](0008-no-lookahead-invariant.md) | No lookahead is a tested invariant | Accepted | `test_no_lookahead` | tests |
| [0009](0009-tooling.md) | uv, data/results out of git, all knobs in Config | Accepted | — | — |

### Hierarchy, 24/7 crypto and the v2 engine: 2026-11-01 (`47fa8ee`) and 2026-11-05 (`92ccc47`)
| # | Decision | Status | Flag / where | Evidence |
|---|---|---|---|---|
| [0010](0010-hierarchy.md) | Two-level hierarchy with per-asset subagents | Superseded by [0032](0032-replace-v1-v2.md) | `hierarchical` | [exp 004](../experiments/004-hierarchy.md) |
| [0011](0011-auto-eta.md) | Optional risk/cost-aware reallocation speed | Superseded by [0032](0032-replace-v1-v2.md) | `eta="auto"` | tests only |
| [0012](0012-engine-24-7-generalisation.md) | Engine generalised to 24/7 perps (eligibility, funding, bars) | Superseded by [0032](0032-replace-v1-v2.md) | `for_tier` | tests |
| [0013](0013-crypto-data-pipeline.md) | Binance USD-M data, point-in-time, survivorship-free universe | Accepted | `crypto_data.py` | tests |
| [0014](0014-crypto-benchmark-protocol.md) | v1 crypto benchmark: dev/holdout, bootstrap vs BTC | Superseded by [0032](0032-replace-v1-v2.md) | `run_crypto_benchmark.py` | [exp 005](../experiments/005-v1-crypto-benchmark.md) (not recorded) |
| [0015](0015-v2-absolute-return-engine.md) | Second engine (v2) judged in absolute terms | Superseded by [0032](0032-replace-v1-v2.md) | `mas_trade/v2/` | [exp 006](../experiments/006-v2-dev-findings.md) |
| [0016](0016-v2-neutral-books.md) | v2 books: rank-gauss, dollar/beta-neutral, vol-targeted | Superseded by [0032](0032-replace-v1-v2.md) | `v2/books.py` | [exp 006](../experiments/006-v2-dev-findings.md) |
| [0017](0017-v2-combiners.md) | v2 combiners compared (EW ... C3 fusion) | Superseded by [0032](0032-replace-v1-v2.md) | `v2/combiners.py` | [exp 006](../experiments/006-v2-dev-findings.md) |
| [0018](0018-v2-costs-and-min-adv.md) | v2 fee + sqrt-impact costs; liquidity floor | Accepted | `min_adv` | [exp 006](../experiments/006-v2-dev-findings.md) |
| [0019](0019-v2-cost-aware-smoothing.md) | v2 cost-aware partial adjustment | Superseded by [0032](0032-replace-v1-v2.md) | `--smooth` | — |
| [0020](0020-v2-research-hygiene.md) | Sealed holdout, trial log, deflated Sharpe | Accepted | `--unseal` | — |
| [0021](0021-v2-decentralised-admm.md) | v2 decentralised consensus-ADMM combiner on a ring | Superseded by [0032](0032-replace-v1-v2.md) | `admm_*` | [exp 007](../experiments/007-v2-admm-combiner.md) |

### Phase 1: safety layer and centralised baseline, 2026-11-05
| # | Decision | Status | Flag / where | Evidence |
|---|---|---|---|---|
| [0022](0022-build-on-v1-engine.md) | Build the proposal's system on v1; freeze v2 | Superseded by [0032](0032-replace-v1-v2.md) | — | — |
| [0023](0023-stl-implementation.md) | Hand-written quantitative STL, normalised robustness | Accepted | `safety.py` | tests |
| [0024](0024-monitor-always-shield-opt-in.md) | Monitor always runs; shield opt-in | Superseded by [0032](0032-replace-v1-v2.md) | `safety` | — |
| [0025](0025-shield-mechanism.md) | Shield = scale toward cash | Superseded by [0032](0032-replace-v1-v2.md) | `supervise` | [exp 008](../experiments/008-stl-shield-baseline.md) |
| [0026](0026-safety-thresholds.md) | Safety limits (mandate-based) | Superseded by [0036](0036-risk-model-and-stl-placement.md) | `safety_*` | — |
| [0027](0027-centralised-baseline.md) | Centralised baseline = ADMM's fixed point | Superseded by [0032](0032-replace-v1-v2.md) | `central_mv` | [exp 002](../experiments/002-wmsr-vs-admm.md), [008](../experiments/008-stl-shield-baseline.md) |
| [0028](0028-intra-period-safety-checks.md) | Shield also checks every bar (de-risk only) | Superseded by [0032](0032-replace-v1-v2.md) | `safety_daily` | [exp 009](../experiments/009-intra-period-safety-checks.md) |
| [0029](0029-shield-allocation-across-agents.md) | Shield cuts every agent alike; `risk` option removed | Superseded by [0032](0032-replace-v1-v2.md) | — | [exp 010](../experiments/010-shield-allocation-across-agents.md) |
| [0030](0030-skip-market-wide-dump-holes.md) | Universe skips days missing for every symbol (dump holes) | Accepted | `build_universe` | test, [exp 005](../experiments/005-v1-crypto-benchmark.md) |
| [0031](0031-crypto-drawdown-limit.md) | Crypto drawdown limit 30% (same drawdown/vol ratio as stocks) | Superseded by [0032](0032-replace-v1-v2.md) | `for_tier` | [exp 005](../experiments/005-v1-crypto-benchmark.md) |

### The replacement: 2026-11-06 (branch `engine-rebuild`)
Records 0001-0031 describe the legacy implementation (tag `legacy-v1-v2`). Those marked Superseded are history; 0008, 0009, 0013, 0018, 0020, 0023 and 0030 describe ideas or code that live on in the new system.
| # | Decision | Status | Where | Evidence |
|---|---|---|---|---|
| [0032](0032-replace-v1-v2.md) | Replace v1 and v2 with one new implementation; history only in reports and a git tag | Accepted | whole repo | [exp 001-010](../experiments/) |
| [0033](0033-two-level-mas.md) | Two MAS levels: wealth-staked market of hypothesis agents, ADMM asset cells | Accepted (design) | `market.py`, `cells_admm.py` | simulation (planned) |
| [0034](0034-hypothesis-roster-and-timing.md) | One agent per established hypothesis; timing inside the belief; admission gate | Accepted (design) | `agents/` | literature, planned experiments |
| [0035](0035-drop-wmsr-and-belief-averaging.md) | W-MSR and belief-averaging between agents dropped; model averaging inside agents | Accepted (design) | `agents/averaging.py` | [exp 006](../experiments/006-v2-dev-findings.md) |
| [0036](0036-risk-model-and-stl-placement.md) | Factor risk model, priced limits inside the ADMM, STL placements | Accepted (design) | `risk.py`, `stl.py` | [exp 008-010](../experiments/) |
| [0037](0037-extended-data-store.md) | Extended data store: all kline columns, premium index, spot, hourly metrics; audits | Accepted | `data.py`, `download_data.py` | [exp 011](../experiments/011-data-audit.md) |
| [0038](0038-beliefs-calibrated-to-the-hypothesis-card.md) | Belief scale from the hypothesis card, evidence only switches an agent off (kill rule); volatility limit through risk aversion | Accepted | `agents/base.py`, `engine.py` | [exp 013](../experiments/013-carry-baseline-on-real-data.md) |
| [0039](0039-timing-inside-the-belief-of-h2.md) | Timing inside H2's belief: two mechanism-based states, shrunk and sign-constrained | Rejected (code deleted) | none (commit 394314e) | [exp 016](../experiments/016-timing-inside-h2.md) |
| [0040](0040-reversal-agent-and-admission-gate.md) | H4 residual reversal as the third agent, and the full admission gate (stand-alone Sharpe, IC, alpha vs the others) | Accepted (agent not admitted: loses net of costs; experiments 017/018) | `agents/reversal.py` | [exp 017](../experiments/017-reversal-and-the-market-of-three.md), [018](../experiments/018-rerun-after-volatility-limit-fix.md) |
| [0041](0041-h2-kept-as-provisional-agent.md) | H2 (BTC/ETH momentum) stays in the roster as a provisional agent: not admitted by its own rule after the fix, kept for the coordination experiments, no claim of its edge | Accepted | roster (no code) | [exp 015](../experiments/015-time-series-momentum-and-the-market.md), [018](../experiments/018-rerun-after-volatility-limit-fix.md) |
| [0042](0042-decentralised-cell-admm-over-a-graph.md) | Decentralised cell ADMM over a communication graph: each agent keeps its own estimate of the average position and its own price, mixed with neighbours only (dynamic average consensus); `consensus = hub | graph` | Accepted (implementation) | `graph_admm.py`, `engine.py`, `config.py` | tests; [exp 019](../experiments/019-graph-admm-on-real-data.md) |

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
