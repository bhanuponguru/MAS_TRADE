#!/bin/bash
# Experiment 018, the fifteen real-data runs after the volatility-limit fix (5 rosters x 3 bars) and every table read
# from them. The hourly market of three takes about an hour; the full set several hours with JOBS=4.
# Original batch: scripts/experiments/original/018_step0_resume.sh with 018_step0_jobs.txt.
source "$(dirname "$0")/common.sh"
runs_013; runs_015; runs_017; wait
uv run python summarize_runs.py                        # docs/experiments/data/018/runs.csv, yearly.csv
uv run python compare_runs.py --suffix _restricted     # docs/experiments/data/015/comparison_restricted.csv
uv run python compare_blend.py                         # docs/experiments/data/015/blend_control.csv
uv run python compare_reversal.py                      # docs/experiments/data/017/comparison.csv
