# Software metadata

## Software name

BHBench-CR

## Prepared release

- Version: 1.1.5
- GitHub release target: https://github.com/Pawel-Kosinski/cpp-rust-barnes-hut/releases/tag/v1.1.5
- Benchmark data: v1.1.3 campaign generated from commit `ab17547228b0f7440793c9014bfda41d076a239e`
- Zenodo archive: https://doi.org/10.5281/zenodo.22134139

## Purpose

BHBench-CR is a C++/Rust benchmark suite for two-dimensional Barnes-Hut N-body solver variants. It supports reproducible comparison of memory layout, tree traversal strategy, and the language/runtime realization of matched algorithms in C++/OpenMP and Rust/Rayon.

## Languages

- C++17
- Rust 1.85 or newer (edition 2024)

## Parallel frameworks

- OpenMP for the C++ parallel force-evaluation variant
- Rayon for the Rust parallel force-evaluation variant

## Main repository contents

- C++ solver variants in `cpp/`
- Rust solver variants in `nbody_rust/src/bin/`
- Raw publication data, summaries, logs, and environment metadata in `results/`
- Documentation in `docs/`
- Build helper scripts in `scripts/`
- Pinned plotting dependency in `requirements.txt`
- Byte-identical publication inputs in the companion Zenodo asset

## Intended use

The software is intended for reproducible implementation experiments, teaching, and comparative benchmarking of Barnes-Hut solver variants.

## Limitations

BHBench-CR is not a production astrophysical simulator, a state-of-the-art 3D tree code, or a Fast Multipole Method implementation. Its purpose is to provide a compact benchmark codebase for studying implementation-level trade-offs.
