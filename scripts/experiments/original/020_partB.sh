#!/bin/bash
# Experiment 020 part B: eight agents, 1d, dev period. Detached; progress in results/020/partB_done.txt
cd "$(dirname "$(readlink -f "$0")")/../../.."
AG="RankCarry:7 RankCarry:14 RankCarry:30 TSMomentum:15 TSMomentum:30 TSMomentum:60 RankReversal:3 RankReversal:7"
go() { tag=$1; shift; mkdir -p results/$tag; OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 10 uv run python run_benchmark.py --bar 1d \
  --agents $AG --boot 500 --tag $tag "$@" > results/$tag/run.log 2>&1; echo "$(date +%T) exit=$? $tag" >> results/020/partB_done.txt; }
go 020_eight_hub --label "020 eight agents, hub" &
go 020_eight_complete_r1 --consensus graph --topology complete --rounds 1 --label "020 eight agents, graph complete r1" &
go 020_eight_ring_r1 --consensus graph --topology ring --rounds 1 --label "020 eight agents, graph ring r1" &
go 020_eight_ring_r3 --consensus graph --topology ring --rounds 3 --label "020 eight agents, graph ring r3" &
go 020_eight_line_r3 --consensus graph --topology line --rounds 3 --label "020 eight agents, graph line r3" &
go 020_eight_star_r3 --consensus graph --topology star --rounds 3 --label "020 eight agents, graph star r3" &
go 020_eight_hub_cap200 --iters 200 --label "020 eight agents, hub, 200 iterations" &
go 020_eight_ring_r3_cap200 --consensus graph --topology ring --rounds 3 --iters 200 --label "020 eight agents, graph ring r3, 200 iterations" &
wait; echo "$(date +%T) ALL DONE" >> results/020/partB_done.txt
