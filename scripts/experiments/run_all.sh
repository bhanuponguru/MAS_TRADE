#!/bin/bash
# Every experiment of the current system in order (011-023), on the dev period. Many hours (020 and 021 part A about
# 3 hours each, 018 several hours). Assumes data/crypto is downloaded (000_download_data.sh). Historic experiments whose
# code was deleted (014, 016, 021 partA5, 001-010) are not included; run their scripts on their own.
set -euo pipefail
D="$(dirname "$0")"
for s in 012_simulated_markets 018_rerun_all 019_graph_admm 020_topology 021_resilience 022_safety 023_final_table; do
  echo "===== $s"; bash "$D/$s.sh"
done
