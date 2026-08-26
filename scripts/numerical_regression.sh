#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

build_dir="${BUILD_DIR:-build}"
rust_target_dir="${CARGO_TARGET_DIR:-nbody_rust/target}"
output_dir=""
no_build=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --output-dir) output_dir="$2"; shift 2 ;;
        --no-build) no_build=1; shift ;;
        --help)
            echo "Usage: bash scripts/numerical_regression.sh [--output-dir DIR] [--no-build]"
            exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [ -z "$output_dir" ]; then
    output_dir="$(mktemp -d)"
    trap 'rm -rf "$output_dir"' EXIT
elif [ -e "$output_dir" ]; then
    echo "Output directory already exists: $output_dir" >&2
    exit 1
else
    mkdir -p "$output_dir"
fi

if [ "$no_build" -eq 0 ]; then
    bash scripts/build_all.sh
fi

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

resolve_binary() {
    local language="$1"
    local variant="$2"
    local candidate
    if [ "$language" = cpp ]; then
        for candidate in \
            "$build_dir/bh_cpp_$variant" \
            "$build_dir/bh_cpp_$variant.exe" \
            "$build_dir/Release/bh_cpp_$variant" \
            "$build_dir/Release/bh_cpp_$variant.exe"; do
            if [ -f "$candidate" ]; then printf '%s\n' "$candidate"; return 0; fi
        done
    else
        case "$variant" in
            v1) name=bh_v1_direct ;;
            v2) name=bh_v2_pointer_tree ;;
            v3) name=bh_v3_vector_tree ;;
            v4) name=bh_v4_threaded_tree ;;
            v5) name=bh_v5_parallel_force ;;
        esac
        for candidate in "$rust_target_dir/release/$name" "$rust_target_dir/release/$name.exe"; do
            if [ -f "$candidate" ]; then printf '%s\n' "$candidate"; return 0; fi
        done
    fi
    echo "Binary not found for $language $variant" >&2
    return 1
}

medium_input="$output_dir/generated_256_seed4242.txt"
BUILD_DIR="$build_dir" bash scripts/generate_input.sh 256 "$medium_input" 4242 > "$output_dir/generator.log"
medium_input_repeat="$output_dir/generated_256_seed4242_repeat.txt"
BUILD_DIR="$build_dir" bash scripts/generate_input.sh 256 "$medium_input_repeat" 4242 >> "$output_dir/generator.log"
if ! cmp -s "$medium_input" "$medium_input_repeat"; then
    echo "Generator determinism check failed for seed 4242" >&2
    exit 1
fi

printf '%s\n' 'case,language,variant,particles,theta,rms_relative,p95_relative,rms_threshold,p95_threshold,passed' > "$output_dir/numerical_regression.csv"

run_case() {
    local case_name="$1"
    local case_input="$2"
    local case_particles="$3"
    local case_theta="$4"
    local rms_threshold="$5"
    local p95_threshold="$6"

    for language in cpp rust; do
        for variant in v1 v2 v3 v4 v5; do
            binary="$(resolve_binary "$language" "$variant")"
            dump="$output_dir/${case_name}_${language}_${variant}_forces.csv"
            log="$output_dir/${case_name}_${language}_${variant}.log"
            args=(--input "$case_input" --particles "$case_particles" --frames 1 --warmup-frames 0 --theta "$case_theta" --dump-forces "$dump")
            if [ "$variant" = v5 ]; then args+=(--threads 2); fi
            "$binary" "${args[@]}" > "$log" 2>&1
        done

        for variant in v2 v3 v4 v5; do
            comparison="$("$python_cmd" scripts/compare_force_dumps.py \
                "$output_dir/${case_name}_${language}_v1_forces.csv" \
                "$output_dir/${case_name}_${language}_${variant}_forces.csv" \
                --language "$language" --variant "$variant" --theta "$case_theta" \
                --rms-threshold "$rms_threshold" --p95-threshold "$p95_threshold")"
            printf '%s,%s\n' "$case_name" "$comparison" >> "$output_dir/numerical_regression.csv"
        done
    done

    comparison="$("$python_cmd" scripts/compare_force_dumps.py \
        "$output_dir/${case_name}_cpp_v1_forces.csv" \
        "$output_dir/${case_name}_rust_v1_forces.csv" \
        --language cross-language --variant direct --theta "$case_theta" \
        --rms-threshold 0.0001 --p95-threshold 0.0001)"
    printf '%s,%s\n' "$case_name" "$comparison" >> "$output_dir/numerical_regression.csv"
}

run_case smoke data/smoke_input.txt 8 0.3 0.05 0.15
run_case medium-theta-0.3 "$medium_input" 256 0.3 0.05 0.15
run_case medium-theta-0.7 "$medium_input" 256 0.7 0.05 0.25
run_case self-interaction data/self_interaction_input.txt 3 10 0.00001 0.00001
run_case coincident data/coincident_input.txt 4 10 0.00001 0.00001

echo "Numerical regression passed; results: $output_dir/numerical_regression.csv"
