#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
archive_root="$tmp_dir/source"
mkdir -p "$archive_root"

build_dir="${BUILD_DIR:-build}"
rust_target_dir="${CARGO_TARGET_DIR:-nbody_rust/target}"

git archive --format=tar HEAD -o "$tmp_dir/source.tar"
tar -xf "$tmp_dir/source.tar" -C "$archive_root"
cp -R "$build_dir" "$archive_root/build"
mkdir -p "$archive_root/nbody_rust"
cp -R "$rust_target_dir" "$archive_root/nbody_rust/target"

cd "$archive_root"
bash scripts/run_benchmarks.sh \
    --no-build \
    --input data/smoke_input.txt \
    --particles 8 \
    --frames 1 \
    --warmup-frames 1 \
    --repeats 1 \
    --theta 0.3 \
    --threads 2 \
    --languages cpp,rust \
    --variants v3 \
    --output-dir results/archive-runner-test

test "$(wc -l < results/archive-runner-test/raw_runs.csv)" -eq 3
test "$(wc -l < results/archive-runner-test/summary.csv)" -eq 3
grep -q '"commit": "not-applicable-source-archive"' results/archive-runner-test/environment.json

echo "Standalone archive runner test passed."
