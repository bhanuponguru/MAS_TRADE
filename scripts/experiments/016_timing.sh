#!/bin/bash
# Experiment 016, timing inside H2 (rejected; TimedMomentum and compare_timing.py were deleted). Runs at commit 394314e,
# with that commit's engine (before the volatility-limit fix of 018), including the untimed baselines it compares with,
# in its own results/ (results/historic/394314e/results). Output: docs/experiments/data/016/comparison.csv there.
source "$(dirname "$0")/common.sh"
H="bash scripts/experiments/historic.sh 394314e --"
hb() { local tag=$1; shift; $H bash -c "mkdir -p results/$tag && uv run python run_benchmark.py --boot 500 --tag $tag $* > results/$tag/run.log 2>&1" && echo "done $tag"; }
$H uv sync >/dev/null      # create the worktree and its environment once, before the parallel runs
for b in $BARS; do
  spawn hb "${b}_broad_TSMomentum_restricted" --bar $b --agents TSMomentum
  spawn hb "${b}_broad_RankCarry+TSMomentum_restricted" --bar $b --agents RankCarry TSMomentum
  spawn hb "${b}_broad_TSMomentumTimed" --bar $b --agents TSMomentumTimed --label "'016 timed H2 alone'"
  spawn hb "${b}_broad_RankCarry+TSMomentumTimed" --bar $b --agents RankCarry TSMomentumTimed --label "'016 carry+timed H2'"
done
wait
$H uv run python compare_timing.py
