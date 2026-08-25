#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

raw="$tmp_dir/raw_runs.csv"
summary="$tmp_dir/summary.csv"
printf '%s\n' \
    'language,variant,run,particles,frames,theta,threads,tree_ms_per_frame,force_ms_per_frame,total_ms,log' \
    'cpp,v1,1,8,1,0.3,0,1,10,11,run1.log' \
    'cpp,v1,2,8,1,0.3,0,3,14,17,run2.log' > "$raw"

awk -F, -f scripts/summarize_results.awk "$raw" > "$summary"

awk -F, '
    $1 == "cpp" && $2 == "v1" {
        tolerance = 1e-6
        expected_sd = sqrt(2)
        valid = $3 == 2 && $4 == 2 && ($5 - expected_sd)^2 < tolerance && \
                $6 == 12 && ($7 - (2 * expected_sd))^2 < tolerance && \
                $8 == 14 && ($9 - (3 * expected_sd))^2 < tolerance
    }
    END { exit valid ? 0 : 1 }
' "$summary"

echo "Summary statistics test passed."
