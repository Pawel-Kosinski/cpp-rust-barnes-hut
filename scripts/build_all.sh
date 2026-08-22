#!/usr/bin/env bash
set -e

echo "Building C++ variants..."
./scripts/build_cpp.sh

echo "Building Rust variants..."
./scripts/build_rust.sh

echo "All builds completed successfully."
