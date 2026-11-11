#!/bin/bash
# Experiment 022, the STL safety monitor and supervisor.
#   bash scripts/experiments/022_safety.sh [runs|tables|all]      default all
# Part A: carry+H2 on 1d/4h/1h with safety off and derisk, and hold on 1d (seven hub runs).
# Part B: market of three on a complete graph, clean and with a noise liar (May-Jul 2022) under hold.
# The undefended liar run (022_three_liar) never finishes (its solves diverge, data/022/liar_solve_divergence.log), so
# it is only started with WITH_UNDEFENDED_LIAR=1. The original batch also re-ran 022_three_liar_hold after a monitor fix
# (amendment 1); the current code already has the fix, so one run suffices.
# Original batch: scripts/experiments/original/022_runs.sh and 022_rerun_hold.sh.
source "$(dirname "$0")/common.sh"
what=${1:-all}
if [ "$what" = runs ] || [ "$what" = all ]; then
  A="--agents RankCarry TSMomentum"
  for b in $BARS; do
    spawn bench 022_${b}_off --bar $b $A --label "022 carry+H2 $b safety off"
    spawn bench 022_${b}_derisk --bar $b $A --safety derisk --label "022 carry+H2 $b safety derisk"
  done
  spawn bench 022_1d_hold --bar 1d $A --safety hold --label "022 carry+H2 1d safety hold"
  B="--bar 1d --agents RankCarry TSMomentum RankReversal --consensus graph --topology complete --rounds 1"
  L="--faulty RankReversal --faulty-window 2022-05-01 2022-07-31 --attack 0.01 --attack-kind noise"
  spawn bench 022_three_clean $B --label "022 three graph complete, no liar"
  spawn bench 022_three_liar_hold $B $L --safety hold --label "022 three graph complete, noise liar May-Jul 2022, hold (rerun after monitor fix, amendment 1)"
  if [ -n "${WITH_UNDEFENDED_LIAR:-}" ]; then
    spawn bench 022_three_liar $B $L --label "022 three graph complete, noise liar May-Jul 2022, no defence"
  fi
  wait
fi
if [ "$what" = tables ] || [ "$what" = all ]; then
  uv run python experiment_tables.py 022                 # docs/experiments/data/022/runs.csv, windows.csv
fi
