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

printf '%s\n' 'language,variant,particles,theta,rms_relative,p95_relative,rms_threshold,p95_threshold,passed' > "$output_dir/numerical_regression.csv"
for language in cpp rust; do
    for variant in v1 v2 v3 v4 v5; do
        binary="$(resolve_binary "$language" "$variant")"
        dump="$output_dir/${language}_${variant}_forces.csv"
        log="$output_dir/${language}_${variant}.log"
        args=(--input data/smoke_input.txt --particles 8 --frames 1 --warmup-frames 0 --theta 0.3 --dump-forces "$dump")
        if [ "$variant" = v5 ]; then args+=(--threads 2); fi
        "$binary" "${args[@]}" > "$log" 2>&1
    done

    for variant in v2 v3 v4 v5; do
        "$python_cmd" scripts/compare_force_dumps.py \
            "$output_dir/${language}_v1_forces.csv" \
            "$output_dir/${language}_${variant}_forces.csv" \
            --language "$language" --variant "$variant" --theta 0.3 \
            >> "$output_dir/numerical_regression.csv"
    done
done

"$python_cmd" scripts/compare_force_dumps.py \
    "$output_dir/cpp_v1_forces.csv" \
    "$output_dir/rust_v1_forces.csv" \
    --language cross-language --variant direct --theta 0.3 \
    --rms-threshold 0.0001 --p95-threshold 0.0001 \
    >> "$output_dir/numerical_regression.csv"

echo "Numerical regression passed; results: $output_dir/numerical_regression.csv"
