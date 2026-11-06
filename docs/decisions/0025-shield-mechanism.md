# 0025. Shield mechanism: scale the portfolio toward cash

Status: **Superseded by 0032** (was: Accepted)   Date: 2026-11-05   Where: `safety.supervise`

## Context
When a spec is about to be violated, the supervisor must change the portfolio. It may only use information from before the rebalance (no-lookahead is a tested invariant).

## Options
1. **Scale toward cash**: multiply exposures by a factor <= 1, the rest earns 0. Simple, never adds risk, keeps the consensus portfolio's direction.
2. Re-solve the consensus with risk constraints (constrained ADMM): tighter coupling between optimisation and safety, much more complex. Kept as a possible later step (proposal Week 7).
3. Switch to a fixed safe portfolio (e.g. equal weight): crude.

## Decision
Option 1, three parts:
- per-stock cap `m_k = min(1, max_weight/|w_k|)`, so phi_conc holds by construction at rebalances
- ex-ante vol target `lam_vol = min(1, max_vol/sigma_ex)`, with sigma_ex from the lookback covariance
- drawdown de-risking `lam_dd`: falls linearly from 1 to `safety_min_scale` as the drawdown margin goes from `safety_buffer` to 0, so it acts before the limit is hit
Exposure multiplier = `min(lam_vol, lam_dd) * m_k`.

## Consequences
Phase 1 result (US stocks, 2017–2025): violations of drawdown spec 13.8% -> 5.1% of days, vol spec 17.7% -> 11.1%, max drawdown -26% -> -21%, Sharpe 0.81 -> 0.79. Breaches that start between rebalances are not caught (see 0028).

## Rollback
`Config.safety=False`.
