#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

build_dir="${BUILD_DIR:-build}"
mkdir -p "$build_dir"
cmake -S . -B "$build_dir" -DCMAKE_BUILD_TYPE=Release
cmake --build "$build_dir" --config Release
