#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

input="data/start_1000.txt"
particles=1000
frames=5
warmup_frames=1
repeats=10
theta=0.3
threads=0
seed=1337
languages_csv="cpp,rust"
variants_csv="v1,v2,v3,v4,v5"
output_dir=""
build_dir="${BUILD_DIR:-build}"
rust_target_dir="${CARGO_TARGET_DIR:-nbody_rust/target}"
no_build=0

usage() {
    cat <<'EOF'
Usage: bash scripts/run_benchmarks.sh [options]

  --input FILE            Deterministic input file
  --particles N           Expected particle count
  --frames N              Number of measured frames
  --warmup-frames N       Frames executed before timing is accumulated
  --repeats N             Independent process runs
  --theta VALUE           Barnes-Hut opening threshold
  --threads N             V5 threads; 0 detects and records the logical CPU count
  --seed N                Input-generator seed recorded in result metadata
  --languages LIST        Comma-separated subset of cpp,rust
  --variants LIST         Comma-separated subset of v1,v2,v3,v4,v5
  --output-dir DIR        New result directory; defaults to a UTC-dated directory
  --no-build              Reuse existing binaries
  --help                  Show this message
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --input) input="$2"; shift 2 ;;
        --particles) particles="$2"; shift 2 ;;
        --frames) frames="$2"; shift 2 ;;
        --warmup-frames) warmup_frames="$2"; shift 2 ;;
        --repeats) repeats="$2"; shift 2 ;;
        --theta) theta="$2"; shift 2 ;;
        --threads) threads="$2"; shift 2 ;;
        --seed) seed="$2"; shift 2 ;;
        --languages) languages_csv="$2"; shift 2 ;;
        --variants) variants_csv="$2"; shift 2 ;;
        --output-dir) output_dir="$2"; shift 2 ;;
        --no-build) no_build=1; shift ;;
        --help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

is_nonnegative_integer() {
    [[ "$1" =~ ^[0-9]+$ ]]
}

if ! is_nonnegative_integer "$particles" || [ "$particles" -eq 0 ]; then
    echo "--particles must be a positive integer" >&2
    exit 1
fi
if ! is_nonnegative_integer "$frames" || [ "$frames" -eq 0 ]; then
    echo "--frames must be a positive integer" >&2
    exit 1
fi
if ! is_nonnegative_integer "$warmup_frames"; then
    echo "--warmup-frames must be a non-negative integer" >&2
    exit 1
fi
if ! is_nonnegative_integer "$repeats" || [ "$repeats" -eq 0 ]; then
    echo "--repeats must be a positive integer" >&2
    exit 1
fi
if ! is_nonnegative_integer "$threads"; then
    echo "--threads must be a non-negative integer" >&2
    exit 1
fi
if [ ! -f "$input" ]; then
    echo "Input file not found: $input" >&2
    exit 1
fi

IFS=',' read -r -a languages <<< "$languages_csv"
IFS=',' read -r -a variants <<< "$variants_csv"
for language in "${languages[@]}"; do
    case "$language" in cpp|rust) ;; *) echo "Unsupported language: $language" >&2; exit 1 ;; esac
done
for variant in "${variants[@]}"; do
    case "$variant" in v1|v2|v3|v4|v5) ;; *) echo "Unsupported variant: $variant" >&2; exit 1 ;; esac
done

if [ -z "$output_dir" ]; then
    output_dir="results/generated/$(date -u +%Y%m%dT%H%M%SZ)-${BASHPID}"
fi
if [ -e "$output_dir" ]; then
    echo "Output directory already exists; refusing to overwrite it: $output_dir" >&2
    exit 1
fi

if [ "$no_build" -eq 0 ]; then
    bash scripts/build_all.sh
fi

detect_threads() {
    local detected=""
    if command -v getconf >/dev/null 2>&1; then
        detected="$(getconf _NPROCESSORS_ONLN 2>/dev/null || true)"
    fi
    if ! is_nonnegative_integer "${detected:-}" || [ "${detected:-0}" -eq 0 ]; then
        if command -v nproc >/dev/null 2>&1; then
            detected="$(nproc 2>/dev/null || true)"
        fi
    fi
    if ! is_nonnegative_integer "${detected:-}" || [ "${detected:-0}" -eq 0 ]; then
        detected="${NUMBER_OF_PROCESSORS:-1}"
    fi
    printf '%s\n' "$detected"
}

if [ "$threads" -gt 0 ]; then
    effective_parallel_threads="$threads"
else
    effective_parallel_threads="$(detect_threads)"
fi
export OMP_NUM_THREADS="$effective_parallel_threads"
export OMP_DYNAMIC=FALSE
export RAYON_NUM_THREADS="$effective_parallel_threads"

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    commit="$(git rev-parse HEAD)"
else
    commit="not-applicable-source-archive"
fi
version="$(awk -F'"' '/^version = / {print $2; exit}' nbody_rust/Cargo.toml)"

if [ -n "${PYTHON:-}" ]; then
    python_cmd="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
    python_cmd=python3
elif command -v python >/dev/null 2>&1; then
    python_cmd=python
else
    echo "Python 3 is required for summaries and environment metadata" >&2
    exit 1
fi

resolve_cpp_binary() {
    local name="$1"
    local candidate
    for candidate in "$build_dir/$name" "$build_dir/$name.exe" "$build_dir/Release/$name" "$build_dir/Release/$name.exe"; do
        if [ -f "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    echo "C++ binary not found for $name below $build_dir" >&2
    return 1
}

resolve_rust_binary() {
    local name="$1"
    local candidate
    for candidate in "$rust_target_dir/release/$name" "$rust_target_dir/release/$name.exe"; do
        if [ -f "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    echo "Rust binary not found for $name below $rust_target_dir" >&2
    return 1
}

extract_metric() {
    local label="$1"
    local log="$2"
    awk -F': ' -v label="$label" '$1 == label {split($2, value, " "); result=value[1]} END {print result}' "$log"
}

mkdir -p "$output_dir/logs"
raw="$output_dir/raw_runs.csv"
summary="$output_dir/summary.csv"
environment="$output_dir/environment.json"
printf '%s\n' 'run_id,started_utc,language,variant,repeat,particles,measured_frames,warmup_frames,theta,seed,requested_threads,effective_threads,input,tree_ms_per_frame,force_update_ms_per_frame,cleanup_ms_per_frame,total_ms_per_frame,total_run_ms,version,commit,log' > "$raw"

run_id="$(basename "$output_dir")"
for language in "${languages[@]}"; do
    for variant in "${variants[@]}"; do
        if [ "$language" = cpp ]; then
            binary="$(resolve_cpp_binary "bh_cpp_$variant")"
        else
            case "$variant" in
                v1) rust_name=bh_v1_direct ;;
                v2) rust_name=bh_v2_pointer_tree ;;
                v3) rust_name=bh_v3_vector_tree ;;
                v4) rust_name=bh_v4_threaded_tree ;;
                v5) rust_name=bh_v5_parallel_force ;;
            esac
            binary="$(resolve_rust_binary "$rust_name")"
        fi

        if [ "$variant" = v5 ]; then
            run_threads="$effective_parallel_threads"
        else
            run_threads=1
        fi

        for repeat in $(seq 1 "$repeats"); do
            started_utc="$(date -u +%FT%TZ)"
            log="$output_dir/logs/${language}_${variant}_${repeat}.log"
            args=(--input "$input" --particles "$particles" --frames "$frames" --warmup-frames "$warmup_frames" --theta "$theta")
            if [ "$variant" = v5 ]; then
                args+=(--threads "$effective_parallel_threads")
            fi
            "$binary" "${args[@]}" > "$log" 2>&1

            tree="$(extract_metric 'Tree construction time' "$log")"
            force="$(extract_metric 'Force/update time' "$log")"
            cleanup="$(extract_metric 'Cleanup time' "$log")"
            total_run="$(extract_metric 'Total measured time' "$log")"
            if [ -z "$tree" ] || [ -z "$force" ] || [ -z "$cleanup" ] || [ -z "$total_run" ]; then
                echo "Could not parse timing output from $log" >&2
                exit 1
            fi
            total_per_frame="$(awk -v total="$total_run" -v count="$frames" 'BEGIN {printf "%.9f", total / count}')"

            printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
                "$run_id" "$started_utc" "$language" "$variant" "$repeat" "$particles" "$frames" \
                "$warmup_frames" "$theta" "$seed" "$threads" "$run_threads" "$input" "$tree" "$force" \
                "$cleanup" "$total_per_frame" "$total_run" "$version" "$commit" "$log" >> "$raw"
        done
    done
done

"$python_cmd" scripts/summarize_results.py "$raw" "$summary"
"$python_cmd" scripts/collect_environment.py \
    --output "$environment" \
    --commit "$commit" \
    --version "$version" \
    --input "$input" \
    --particles "$particles" \
    --frames "$frames" \
    --warmup-frames "$warmup_frames" \
    --repeats "$repeats" \
    --theta "$theta" \
    --seed "$seed" \
    --requested-threads "$threads" \
    --effective-parallel-threads "$effective_parallel_threads" \
    --languages "$languages_csv" \
    --variants "$variants_csv" \
    --build-dir "$build_dir"

echo "Wrote $raw, $summary, logs, and $environment"
