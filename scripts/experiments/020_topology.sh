#!/bin/bash
# Experiment 020, topology and communication budget.
#   bash scripts/experiments/020_topology.sh [partA|partB|tables|all]      default all
# Part A: simulated problems, about 3 hours (writes docs/experiments/data/020/partA_*.csv).
# Part B: eight agents on 1d, hub against graph per topology and iteration cap (eight runs), then partB_runs.csv.
# Original batch: scripts/experiments/original/020_partB.sh.
source "$(dirname "$0")/common.sh"
what=${1:-all}
if [ "$what" = partA ] || [ "$what" = all ]; then uv run python -u run_topology.py --workers 4; fi
if [ "$what" = partB ] || [ "$what" = all ]; then
  B="--bar 1d --agents $EIGHT"
  spawn bench 020_eight_hub $B --label "020 eight agents, hub"
  spawn bench 020_eight_complete_r1 $B --consensus graph --topology complete --rounds 1 --label "020 eight agents, graph complete r1"
  spawn bench 020_eight_ring_r1 $B --consensus graph --topology ring --rounds 1 --label "020 eight agents, graph ring r1"
  spawn bench 020_eight_ring_r3 $B --consensus graph --topology ring --rounds 3 --label "020 eight agents, graph ring r3"
  spawn bench 020_eight_line_r3 $B --consensus graph --topology line --rounds 3 --label "020 eight agents, graph line r3"
  spawn bench 020_eight_star_r3 $B --consensus graph --topology star --rounds 3 --label "020 eight agents, graph star r3"
  spawn bench 020_eight_hub_cap200 $B --iters 200 --label "020 eight agents, hub, 200 iterations"
  spawn bench 020_eight_ring_r3_cap200 $B --consensus graph --topology ring --rounds 3 --iters 200 --label "020 eight agents, graph ring r3, 200 iterations"
  wait
fi
if [ "$what" = partB ] || [ "$what" = tables ] || [ "$what" = all ]; then
  uv run python experiment_tables.py 020                 # docs/experiments/data/020/partB_runs.csv
fi
