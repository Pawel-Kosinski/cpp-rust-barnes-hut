#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

build_dir="${BUILD_DIR:-build}"
rust_target_dir="${CARGO_TARGET_DIR:-nbody_rust/target}"
bash scripts/build_all.sh
for binary in "$build_dir"/bh_cpp_v{1,2,3,4,5}; do
    "$binary" --input data/smoke_input.txt --particles 8 --frames 1 --theta 0.3 --threads 2 > /dev/null
done
for binary in "$rust_target_dir"/release/bh_v{1_direct,2_pointer_tree,3_vector_tree,4_threaded_tree,5_parallel_force}; do
    "$binary" --input data/smoke_input.txt --particles 8 --frames 1 --theta 0.3 --threads 2 > /dev/null
done
echo "Smoke test passed."
