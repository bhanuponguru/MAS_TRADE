#!/bin/bash
# Experiment 011, data audit: a four-symbol probe of every dataset into a separate cache, then the coverage report.
#   bash scripts/experiments/011_data_audit.sh [PROBE_DIR]      default PROBE_DIR: results/011_probe
source "$(dirname "$0")/common.sh"
P=${1:-results/011_probe}
uv run python download_data.py --symbols BTCUSDT ETHUSDT SOLUSDT DOGEUSDT --bars 1d 1h \
  --datasets klines funding premium spot metrics --root "$P"
uv run python download_data.py --symbols BTCUSDT ETHUSDT SOLUSDT DOGEUSDT --bars 1d 1h \
  --datasets klines funding premium spot metrics --root "$P" --coverage
