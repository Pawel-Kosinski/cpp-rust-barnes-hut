#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

output_dir="${1:-results/manuscript/$(date -u +%Y%m%dT%H%M%SZ)/fig1}"
particles="${PARTICLES:-10000}"
frames="${FRAMES:-3}"
warmup_frames="${WARMUP_FRAMES:-1}"
repeats="${REPEATS:-5}"
seed="${SEED:-1337}"
threads="${THREADS:-0}"
thetas="${THETAS:-0.1 0.2 0.3 0.5 0.7}"
build_dir="${BUILD_DIR:-build}"
rust_target_dir="${CARGO_TARGET_DIR:-nbody_rust/target}"

if [ -e "$output_dir" ]; then
    echo "Output directory already exists: $output_dir" >&2
    exit 1
fi
mkdir -p "$output_dir/forces"

if [ "${SKIP_BUILD:-0}" != 1 ]; then
    bash scripts/build_all.sh
fi

if [ -n "${PYTHON:-}" ]; then python_cmd="$PYTHON"; elif command -v python3 >/dev/null 2>&1; then python_cmd=python3; else python_cmd=python; fi
input="$output_dir/input_${particles}_seed${seed}.txt"
bash scripts/generate_input.sh "$particles" "$input" "$seed"

resolve_binary() {
    local language="$1"
    local variant="$2"
    local candidate
    if [ "$language" = cpp ]; then
        for candidate in "$build_dir/bh_cpp_$variant" "$build_dir/bh_cpp_$variant.exe" "$build_dir/Release/bh_cpp_$variant" "$build_dir/Release/bh_cpp_$variant.exe"; do
            if [ -f "$candidate" ]; then printf '%s\n' "$candidate"; return 0; fi
        done
    else
        case "$variant" in v1) name=bh_v1_direct ;; v3) name=bh_v3_vector_tree ;; esac
        for candidate in "$rust_target_dir/release/$name" "$rust_target_dir/release/$name.exe"; do
            if [ -f "$candidate" ]; then printf '%s\n' "$candidate"; return 0; fi
        done
    fi
    echo "Binary not found for $language $variant" >&2
    return 1
}

for language in cpp rust; do
    direct="$(resolve_binary "$language" v1)"
    "$direct" --input "$input" --particles "$particles" --frames 1 --warmup-frames 0 --theta 0.3 \
        --dump-forces "$output_dir/forces/${language}_direct.csv" \
        > "$output_dir/forces/${language}_direct.log" 2>&1
done

printf '%s\n' 'language,variant,particles,theta,rms_relative,p95_relative,rms_threshold,p95_threshold,passed' > "$output_dir/accuracy.csv"
raw_inputs=()
for theta in $thetas; do
    theta_slug="${theta//./p}"
    timing_dir="$output_dir/timing_theta_${theta_slug}"
    bash scripts/run_benchmarks.sh \
        --no-build --input "$input" --particles "$particles" \
        --frames "$frames" --warmup-frames "$warmup_frames" --repeats "$repeats" \
        --theta "$theta" --threads "$threads" --seed "$seed" \
        --languages cpp,rust --variants v3 --output-dir "$timing_dir"
    raw_inputs+=("$timing_dir/raw_runs.csv")

    for language in cpp rust; do
        candidate="$(resolve_binary "$language" v3)"
        dump="$output_dir/forces/${language}_v3_theta_${theta_slug}.csv"
        "$candidate" --input "$input" --particles "$particles" --frames 1 --warmup-frames 0 --theta "$theta" \
            --dump-forces "$dump" > "$output_dir/forces/${language}_v3_theta_${theta_slug}.log" 2>&1
        "$python_cmd" scripts/compare_force_dumps.py \
            "$output_dir/forces/${language}_direct.csv" "$dump" \
            --language "$language" --variant v3 --theta "$theta" \
            --rms-threshold 1 --p95-threshold 2 >> "$output_dir/accuracy.csv"
    done
done

"$python_cmd" scripts/combine_raw_results.py "$output_dir/raw_runs.csv" "${raw_inputs[@]}"
"$python_cmd" scripts/summarize_results.py "$output_dir/raw_runs.csv" "$output_dir/summary.csv"
echo "Figure 1 source data written to $output_dir"
