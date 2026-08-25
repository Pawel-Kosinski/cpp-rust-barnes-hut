#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

input="data/start_1000.txt"
particles=1000
frames=5
repeats=10
theta=0.3
threads=0
output_dir="results/generated"
build_dir="${BUILD_DIR:-build}"
rust_target_dir="${CARGO_TARGET_DIR:-nbody_rust/target}"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --input) input="$2"; shift 2 ;;
        --particles) particles="$2"; shift 2 ;;
        --frames) frames="$2"; shift 2 ;;
        --repeats) repeats="$2"; shift 2 ;;
        --theta) theta="$2"; shift 2 ;;
        --threads) threads="$2"; shift 2 ;;
        --output-dir) output_dir="$2"; shift 2 ;;
        --help)
            echo "Usage: bash scripts/run_benchmarks.sh [--input FILE] [--particles N] [--frames N] [--repeats N] [--theta VALUE] [--threads N] [--output-dir DIR]"
            exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [ "$repeats" -le 0 ]; then echo "--repeats must be positive" >&2; exit 1; fi
if [ ! -f "$input" ]; then echo "Input file not found: $input" >&2; exit 1; fi

bash scripts/build_all.sh
mkdir -p "$output_dir/logs"

raw="$output_dir/raw_runs.csv"
summary="$output_dir/summary.csv"
environment="$output_dir/environment.json"
printf 'language,variant,run,particles,frames,theta,threads,tree_ms_per_frame,force_ms_per_frame,total_ms,log\n' > "$raw"

variants=(v1 v2 v3 v4 v5)
for language in cpp rust; do
    for variant in "${variants[@]}"; do
        for run in $(seq 1 "$repeats"); do
            if [ "$language" = cpp ]; then
                command=("$build_dir/bh_cpp_${variant}")
            else
                case "$variant" in
                    v1) rust_binary=bh_v1_direct ;;
                    v2) rust_binary=bh_v2_pointer_tree ;;
                    v3) rust_binary=bh_v3_vector_tree ;;
                    v4) rust_binary=bh_v4_threaded_tree ;;
                    v5) rust_binary=bh_v5_parallel_force ;;
                esac
                command=("$rust_target_dir/release/$rust_binary")
            fi
            log="$output_dir/logs/${language}_${variant}_${run}.log"
            args=(--input "$input" --particles "$particles" --frames "$frames" --theta "$theta")
            if [ "$variant" = v5 ] && [ "$threads" -gt 0 ]; then args+=(--threads "$threads"); fi
            "${command[@]}" "${args[@]}" > "$log" 2>&1
            tree=$(awk -F': ' '/Tree construction time:/ {split($2,a," "); print a[1]}' "$log" | tail -n 1)
            force=$(awk -F': ' '/Force calculation time:/ {split($2,a," "); print a[1]}' "$log" | tail -n 1)
            total=$(awk -F': ' '/Total simulation time:/ {split($2,a," "); print a[1]}' "$log" | tail -n 1)
            printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' "$language" "$variant" "$run" "$particles" "$frames" "$theta" "$threads" "${tree:-}" "${force:-}" "${total:-}" "$log" >> "$raw"
        done
    done
done

awk -F, -f scripts/summarize_results.awk "$raw" > "$summary"

commit=$(git rev-parse HEAD)
printf '{\n  "commit": "%s",\n  "date_utc": "%s",\n  "system": "%s",\n  "kernel": "%s",\n  "compiler": "%s",\n  "rustc": "%s",\n  "parameters": {"input": "%s", "particles": %s, "frames": %s, "repeats": %s, "theta": %s, "threads": %s}\n}\n' "$commit" "$(date -u +%FT%TZ)" "$(uname -s)" "$(uname -r)" "$(c++ --version 2>/dev/null | head -n 1 || true)" "$(rustc --version)" "$input" "$particles" "$frames" "$repeats" "$theta" "$threads" > "$environment"
echo "Wrote $raw, $summary, and $environment"
