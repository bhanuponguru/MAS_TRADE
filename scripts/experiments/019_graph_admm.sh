#!/bin/bash
# Experiment 019, the graph (hub-free) optimiser on real data against the hub, market of three on 1d.
# Hub reference: the 018 run 1d_broad_RankCarry+TSMomentum+RankReversal (run here if missing). The comparison table is
# T2 of experiment 023 (final_table.py). Original batch: scripts/experiments/original/019_step1_runs.sh.
source "$(dirname "$0")/common.sh"
A="--bar 1d --agents RankCarry TSMomentum RankReversal"
spawn bench 1d_broad_RankCarry+TSMomentum+RankReversal $A --label "017 market of three (vol fix)"
spawn bench 1d_broad_three_graph_complete $A --consensus graph --topology complete --label "019 market of three, graph complete"
spawn bench 1d_broad_three_graph_line $A --consensus graph --topology line --label "019 market of three, graph line"
spawn bench 1d_broad_three_graph_line_r3 $A --consensus graph --topology line --rounds 3 --label "019 market of three, graph line, 3 rounds"
wait
