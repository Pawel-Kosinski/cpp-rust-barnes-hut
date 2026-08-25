#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

echo "Building C++ variants..."
bash scripts/build_cpp.sh

echo "Building Rust variants..."
bash scripts/build_rust.sh

echo "All builds completed successfully."
