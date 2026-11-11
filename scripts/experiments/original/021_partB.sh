#!/bin/bash
# Experiment 021 part B: eight agents, 1d, dev period. Detached; progress in results/021/partB_done.txt
cd "$(dirname "$(readlink -f "$0")")/../../.."
AG="RankCarry:7 RankCarry:14 RankCarry:30 TSMomentum:15 TSMomentum:30 TSMomentum:60 RankReversal:3 RankReversal:7"
go() { tag=$1; shift; mkdir -p results/$tag; OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 10 uv run python run_benchmark.py --bar 1d \
  --agents $AG --boot 500 --tag $tag "$@" > results/$tag/run.log 2>&1; echo "$(date +%T) exit=$? $tag" >> results/021/partB_done.txt; }
OFF="--offline RankCarry7 2022-05-01 2022-08-31"
go 021_links_complete_r1 --consensus graph --topology complete --rounds 1 --link-fail 0.3 --label "021 link failures 0.3, complete r1" &
go 021_links_ring_r3 --consensus graph --topology ring --rounds 3 --link-fail 0.3 --label "021 link failures 0.3, ring r3" &
go 021_offline_hub $OFF --label "021 RankCarry7 offline, hub" &
go 021_offline_complete_r1 $OFF --consensus graph --topology complete --rounds 1 --label "021 RankCarry7 offline, complete r1" &
go 021_offline_ring_r3 $OFF --consensus graph --topology ring --rounds 3 --label "021 RankCarry7 offline, ring r3" &
go 021_detect_clean --consensus graph --topology complete --rounds 1 --detect 50 --label "021 detector on, no liar, complete r1" &
go 021_liar_none --consensus graph --topology complete --rounds 1 --faulty TSMomentum30 --attack 0.01 --label "021 liar, no defence, complete r1" &
go 021_liar_detect --consensus graph --topology complete --rounds 1 --faulty TSMomentum30 --attack 0.01 --detect 50 --label "021 liar, detector, complete r1" &
go 021_liar_hub --faulty TSMomentum30 --label "021 hub without TSMomentum30" &
wait; echo "$(date +%T) ALL DONE" >> results/021/partB_done.txt
