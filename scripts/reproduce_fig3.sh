#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

output_dir="${1:-results/manuscript/$(date -u +%Y%m%dT%H%M%SZ)/fig3}"
particle_counts="${PARTICLE_COUNTS:-1000000 2000000 5000000}"
frames="${FRAMES:-3}"
warmup_frames="${WARMUP_FRAMES:-1}"
repeats="${REPEATS:-5}"
seed="${SEED:-1337}"
threads="${THREADS:-0}"

if [ -e "$output_dir" ]; then echo "Output directory already exists: $output_dir" >&2; exit 1; fi
mkdir -p "$output_dir"
if [ "${SKIP_BUILD:-0}" != 1 ]; then bash scripts/build_all.sh; fi
if [ -n "${PYTHON:-}" ]; then python_cmd="$PYTHON"; elif command -v python3 >/dev/null 2>&1; then python_cmd=python3; else python_cmd=python; fi

raw_inputs=()
for particles in $particle_counts; do
    input="$output_dir/input_${particles}_seed${seed}.txt"
    bash scripts/generate_input.sh "$particles" "$input" "$seed"
    run_dir="$output_dir/n_${particles}"
    bash scripts/run_benchmarks.sh \
        --no-build --input "$input" --particles "$particles" \
        --frames "$frames" --warmup-frames "$warmup_frames" --repeats "$repeats" \
        --theta 0.3 --threads "$threads" --seed "$seed" \
        --languages cpp,rust --variants v3,v4,v5 --output-dir "$run_dir"
    raw_inputs+=("$run_dir/raw_runs.csv")
done

"$python_cmd" scripts/combine_raw_results.py "$output_dir/raw_runs.csv" "${raw_inputs[@]}"
"$python_cmd" scripts/summarize_results.py "$output_dir/raw_runs.csv" "$output_dir/summary.csv"
echo "Figure 3 source data written to $output_dir"
