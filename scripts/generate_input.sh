#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

PARTICLES="${1:-50000}"
OUTPUT="${2:-data/start_${PARTICLES}.txt}"
SEED="${3:-1337}"
build_dir="${BUILD_DIR:-build}"

if [ ! -x "$build_dir/bh_generator.exe" ] && [ ! -x "$build_dir/bh_generator" ]; then
    echo "Generator binary not found. Building C++ targets first..."
    bash scripts/build_cpp.sh
fi

if [ -x "$build_dir/bh_generator.exe" ]; then
    "$build_dir/bh_generator.exe" "$PARTICLES" "$OUTPUT" "$SEED"
else
    "$build_dir/bh_generator" "$PARTICLES" "$OUTPUT" "$SEED"
fi
