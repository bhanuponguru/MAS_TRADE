#!/bin/bash
# Experiment 023, the final comparison on the dev period, from the saved runs of 018-022 and results/trials.jsonl
# (no engine run). Needs 018_rerun_all.sh, 019, 020 partB, 021 partB and 022 first.
source "$(dirname "$0")/common.sh"
uv run python final_table.py                           # docs/experiments/data/023/T1..T5
