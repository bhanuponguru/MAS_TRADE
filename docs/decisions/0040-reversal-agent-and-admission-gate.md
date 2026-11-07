# 0040. H4, residual reversal as the third agent, and the full admission gate

Status: **Accepted**   Date: 2026-11-07   Where: `agents/reversal.py` (`RankReversal`)   Evidence: [exp 017](../experiments/017-reversal-and-the-market-of-three.md)

## Context
The market of carry and H2 was not distinguishable from a fixed blend of the two stand-alone runs (experiment 015): with two agents holding almost disjoint books the structure has nothing to do. Residual reversal trades the same coins as carry, so shared limits and netting start to matter, which makes it the natural next test of the multi-agent structure. Evidence on the development period from the legacy implementation (experiment 006): positive rank IC (0.025 / 0.039 / 0.049 on 1d / 4h / 1h, t = 1.6 / 4.1 / 7.9), net Sharpe negative after costs in the legacy engine (-0.68 on 1d). So this tests whether the engine's cost handling (cost on the NET trade, a cost term inside the joint problem) changes that.

## Decision
- Card: see the docstring of `agents/reversal.py`. Residual (beta-removed) trailing 7-day return in units of the coin's volatility, negated, rank-gauss; neutral book; card IC 0.02 (assumption, below the legacy measured ICs, which come from the data we decide on); kill rule as in the base class.
- Admission (all three, each on at least two of three bar sizes; 90% block-bootstrap intervals, 7-day blocks), written before any run of the agent: (a) the stand-alone net Sharpe has a lower bound above 0; (b) the rank IC has t > 2; (c) the intercept of its stand-alone net return regressed on BTC and on the stand-alone returns of carry and H2 has a lower bound above 0.
- Market acceptance: the market of three (carry, H2, reversal) against the market of two, paired Sharpe difference, with the ladder rule of experiment 014.
- The test of the structure itself, reported with the same weight as the gate: the market of three against a fixed inverse-volatility blend of the three stand-alone runs, and the cost of the market against the blended cost.
- Diagnostic, not a gate: rank IC by liquidity tercile of the tradable coins.

## Consequences
One new hypothesis trial. If reversal fails admission it holds the 2% floor in the market only if the market is run with it; the market of three is run regardless, as the planned test of the structure, and reported as such.

## Rollback
Delete `agents/reversal.py` and its tests.
