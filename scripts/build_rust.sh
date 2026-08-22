#!/usr/bin/env bash
set -e

cd nbody_rust
cargo build --release --bins
