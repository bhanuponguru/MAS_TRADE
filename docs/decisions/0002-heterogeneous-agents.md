# 0002. Six simple forecasting agents with long-short portfolios

Status: **Accepted**   Date: 2026-10-18   Commit: `b48056d`   Where: `mas_trade/agents.py`

## Context
The proposal wants autonomous agents with different strategies, so that coordination is actually needed.

## Decision
Six agents, each forecasting expected returns `mu` from the past window only: Momentum (12-1 month), MeanReversion (last 5 days), ShrinkageMean (James-Stein), AR1, EWMATrend (halflife 63), LowVolTilt (mean - variance). Portfolio rule `w = mu / sum|mu|`: sign = long/short, gross exposure 1.
A compromised agent type (`AdversarialAgent`: all-in on one random stock, random side) is part of the model from the start, for resilience tests.

## Rationale (inferred)
Classic, explainable signals that disagree with each other (trend vs reversal), and one portfolio rule for all agents, so differences come from the forecasts only.

## Rollback
`default_agents()`.
