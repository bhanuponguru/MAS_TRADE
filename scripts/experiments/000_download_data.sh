#!/bin/bash
# The data cache of every real-data experiment (data/crypto/, about 1.9 GB): klines 1d/4h/1h, funding, premium index, spot.
#   bash scripts/experiments/000_download_data.sh [--with-metrics]
# --with-metrics also fetches open interest / long-short (about 1,800 files per symbol; only the carry-ladder rungs that
# were never run need it).
# The results were made on a snapshot ending 2026-11-05 (last BTC daily bar). The sealed final year is the 12 months
# before the LAST downloaded bar, so a later download moves the split and changes every number (docs/REPRODUCING.md).
source "$(dirname "$0")/common.sh"
DS="klines funding premium spot"
[ "${1:-}" = "--with-metrics" ] && DS="$DS metrics"
uv run python download_data.py --bars 1d 4h 1h --top 50 --datasets $DS
uv run python download_data.py --coverage
