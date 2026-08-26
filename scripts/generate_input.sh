#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

PARTICLES="${1:-50000}"
OUTPUT="${2:-data/start_${PARTICLES}.txt}"
SEED="${3:-1337}"
build_dir="${BUILD_DIR:-build}"

generator=""
for candidate in \
    "$build_dir/bh_generator" \
    "$build_dir/bh_generator.exe" \
    "$build_dir/Release/bh_generator" \
    "$build_dir/Release/bh_generator.exe"; do
    if [ -f "$candidate" ]; then generator="$candidate"; break; fi
done

if [ -z "$generator" ]; then
    echo "Generator binary not found. Building C++ targets first..."
    bash scripts/build_cpp.sh
fi

if [ -z "$generator" ]; then
    for candidate in "$build_dir/bh_generator" "$build_dir/bh_generator.exe" "$build_dir/Release/bh_generator" "$build_dir/Release/bh_generator.exe"; do
        if [ -f "$candidate" ]; then generator="$candidate"; break; fi
    done
fi

"$generator" "$PARTICLES" "$OUTPUT" "$SEED"
