#!/usr/bin/env bash
set -e

PARTICLES="${1:-50000}"
OUTPUT="${2:-start_50k.txt}"
SEED="${3:-1337}"

if [ ! -x "./build/bh_generator.exe" ] && [ ! -x "./build/bh_generator" ]; then
    echo "Generator binary not found. Building C++ targets first..."
    ./scripts/build_cpp.sh
fi

if [ -x "./build/bh_generator.exe" ]; then
    ./build/bh_generator.exe "$PARTICLES" "$OUTPUT" "$SEED"
else
    ./build/bh_generator "$PARTICLES" "$OUTPUT" "$SEED"
fi
