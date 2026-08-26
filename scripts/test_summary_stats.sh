#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

if [ -n "${PYTHON:-}" ]; then
    python_cmd="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
    python_cmd=python3
elif command -v python >/dev/null 2>&1; then
    python_cmd=python
else
    echo "Python 3 is required" >&2
    exit 1
fi

raw="$tmp_dir/raw_runs.csv"
summary="$tmp_dir/summary.csv"
printf '%s\n' \
    'run_id,started_utc,language,variant,repeat,order_seed,block_position,particles,measured_frames,warmup_frames,theta,seed,requested_threads,effective_threads,input,tree_ms_per_frame,force_update_ms_per_frame,cleanup_ms_per_frame,total_ms_per_frame,total_run_ms,version,commit,log' \
    'test,2026-01-01T00:00:00Z,cpp,v1,1,20260826,1,8,1,0,0.3,1337,0,1,input.txt,1,10,0.5,11.5,11.5,1.1.3,commit,run1.log' \
    'test,2026-01-01T00:00:01Z,cpp,v1,2,20260826,1,8,1,0,0.3,1337,0,1,input.txt,3,14,1.5,18.5,18.5,1.1.3,commit,run2.log' > "$raw"

"$python_cmd" scripts/summarize_results.py "$raw" "$summary"

awk -F, '
    NR == 2 {
        tolerance = 1e-6
        expected_sd = sqrt(2)
        valid = $9 == 2 && $10 == 2 && ($11 - expected_sd)^2 < tolerance && \
                $12 == 12 && ($13 - (2 * expected_sd))^2 < tolerance && \
                $14 == 1 && ($15 - (0.5 * expected_sd))^2 < tolerance && \
                $16 == 15 && ($17 - (3.5 * expected_sd))^2 < tolerance
    }
    END { exit valid ? 0 : 1 }
' "$summary"

echo "Summary statistics test passed."
