#!/bin/bash
# Experiment 021, resilience: link failures, an offline agent, a liar, detect-and-isolate.
#   bash scripts/experiments/021_resilience.sh [partA|partA5|partB|tables|all]      default all (not partA5)
# Part A: simulated problems, about 3.5 hours (docs/experiments/data/021/partA.csv). partA5: the rows of the rejected
# W-MSR trimmed mixing, which only the code at commit 4194d43 can make (output inside results/historic/4194d43).
# Part B: eight agents on 1d (eight runs; reads the 020 hub/complete/ring runs too), then partB_runs.csv. Run 7, the
# undefended liar (021_liar_none), never finished (amendment 1); it is only started with WITH_UNDEFENDED_LIAR=1.
# Original batch: scripts/experiments/original/021_partB.sh.
source "$(dirname "$0")/common.sh"
what=${1:-all}
if [ "$what" = partA ] || [ "$what" = all ]; then uv run python -u run_resilience.py --workers 3; fi
if [ "$what" = partA5 ]; then exec bash scripts/experiments/historic.sh 4194d43 -- uv run python -u run_resilience.py --workers 3; fi
if [ "$what" = partB ] || [ "$what" = all ]; then
  B="--bar 1d --agents $EIGHT"
  OFF="--offline RankCarry7 2022-05-01 2022-08-31"
  spawn bench 020_eight_hub $B --label "020 eight agents, hub"
  spawn bench 020_eight_complete_r1 $B --consensus graph --topology complete --rounds 1 --label "020 eight agents, graph complete r1"
  spawn bench 020_eight_ring_r3 $B --consensus graph --topology ring --rounds 3 --label "020 eight agents, graph ring r3"
  spawn bench 021_links_complete_r1 $B --consensus graph --topology complete --rounds 1 --link-fail 0.3 --label "021 link failures 0.3, complete r1"
  spawn bench 021_links_ring_r3 $B --consensus graph --topology ring --rounds 3 --link-fail 0.3 --label "021 link failures 0.3, ring r3"
  spawn bench 021_offline_hub $B $OFF --label "021 RankCarry7 offline, hub"
  spawn bench 021_offline_complete_r1 $B $OFF --consensus graph --topology complete --rounds 1 --label "021 RankCarry7 offline, complete r1"
  spawn bench 021_offline_ring_r3 $B $OFF --consensus graph --topology ring --rounds 3 --label "021 RankCarry7 offline, ring r3"
  spawn bench 021_detect_clean $B --consensus graph --topology complete --rounds 1 --detect 50 --label "021 detector on, no liar, complete r1"
  if [ -n "${WITH_UNDEFENDED_LIAR:-}" ]; then     # amendment 1: stopped after 3 h 40 min without output, never finished
    spawn bench 021_liar_none $B --consensus graph --topology complete --rounds 1 --faulty TSMomentum30 --attack 0.01 --label "021 liar, no defence, complete r1"
  fi
  spawn bench 021_liar_detect $B --consensus graph --topology complete --rounds 1 --faulty TSMomentum30 --attack 0.01 --detect 50 --label "021 liar, detector, complete r1"
  spawn bench 021_liar_hub $B --faulty TSMomentum30 --label "021 hub without TSMomentum30"
  wait
fi
if [ "$what" = partB ] || [ "$what" = tables ] || [ "$what" = all ]; then
  uv run python experiment_tables.py 021                 # docs/experiments/data/021/partB_runs.csv
fi
