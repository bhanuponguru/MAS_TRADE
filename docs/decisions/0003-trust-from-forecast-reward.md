# 0003. Trust = forecast probability that an agent is profitable

Status: **Accepted**   Date: 2026-10-18   Commit: `b48056d`   Where: `forecasting.trust_scores`; `Config.trust_window`, `trust_halflife`, `trust_power`

## Context
Consensus and capital flows need a weight per agent that reflects how much to listen to it.

## Decision
Each agent's **standalone** portfolio (before consensus) is tracked every day, including a warmup year before trading. Trust `s_i = Phi(m_i * sqrt(H) / sd_i)`, with m and sd the EWMA mean and std (halflife 126 days) of those returns: the normal-approximation probability that the agent makes money over the next holding period. `trust_power` sharpens it.

## Rationale (inferred)
Uses only the agent's own track record (no lookahead), lies in (0,1), and puts mean and risk in one number.

## Rollback
`trust_power=0` makes every trust equal.
