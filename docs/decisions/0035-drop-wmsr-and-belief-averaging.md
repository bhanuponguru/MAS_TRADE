# 0035. W-MSR and belief-averaging between agents dropped; model averaging inside agents

Status: **Accepted (design)**   Date: 2026-11-06   Where: `agents/averaging.py` (not yet built)

## Context
Options considered for the consensus content: (a) W-MSR / DeGroot consensus on beliefs between agents; (b) estimator sub-agents fused by consensus inside an agent; (c) plain model averaging inside an agent; (d) nothing.

## Decision
(c). Reasons:
- Averaging beliefs between agents would erase selection (all agents would bet the same blended belief and earn the same) and changes nothing at system level on a complete graph.
- W-MSR protects against faulty or malicious values in decentralised averaging. Our agents are our own code on a central machine; a trimmed mean, median or belief-magnitude STL spec gives the same protection. Trimming across different hypotheses can remove a legitimate specialist.
- Model variants inside an agent (model class, horizon, refit window, seeds) are averaged, error-weighted and shrunk toward equal weights; forecast error is measured over about 60 coins per period, so these weights are far less noisy than P&L-based ones.
- The effective number of independent voters matters more than the voter count (our four v2 agents were nearly uncorrelated, effective number 3.5 of 4, yet failed because each had about zero net skill).

## Consequences
The W-MSR resilience demonstration exists only at the tag (experiment 003).

## Rollback
Re-add a trimmed mean inside `averaging.py` if a fault-injection test shows a need.
