#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

output_dir="${1:-results/manuscript/$(date -u +%Y%m%dT%H%M%SZ)/fig2}"
particles="${PARTICLES:-100000}"
frames="${FRAMES:-5}"
warmup_frames="${WARMUP_FRAMES:-2}"
repeats="${REPEATS:-10}"
seed="${SEED:-1337}"
threads="${THREADS:-0}"

if [ -e "$output_dir" ]; then echo "Output directory already exists: $output_dir" >&2; exit 1; fi
mkdir -p "$output_dir"
if [ "${SKIP_BUILD:-0}" != 1 ]; then bash scripts/build_all.sh; fi

input="$output_dir/input_${particles}_seed${seed}.txt"
bash scripts/generate_input.sh "$particles" "$input" "$seed"
bash scripts/run_benchmarks.sh \
    --no-build --input "$input" --particles "$particles" \
    --frames "$frames" --warmup-frames "$warmup_frames" --repeats "$repeats" \
    --theta 0.3 --threads "$threads" --seed "$seed" \
    --languages cpp,rust --variants v2,v3,v4,v5 --output-dir "$output_dir/run"

cp "$output_dir/run/raw_runs.csv" "$output_dir/raw_runs.csv"
cp "$output_dir/run/summary.csv" "$output_dir/summary.csv"
echo "Figure 2 source data written to $output_dir"
