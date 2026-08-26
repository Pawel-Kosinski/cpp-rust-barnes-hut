# BHBench-CR

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22112969.svg)](https://doi.org/10.5281/zenodo.22112969)

BHBench-CR is a C++/Rust benchmark suite for two-dimensional Barnes-Hut N-body solver variants. It is intended for reproducible implementation experiments, teaching, and comparative studies of data layout, traversal strategy, and the way matched solver strategies are expressed in C++/OpenMP and Rust/Rayon.

The software is not intended to be a production astrophysical simulator or a state-of-the-art 3D tree code. Its purpose is to provide a compact and reproducible benchmark workload for studying implementation trade-offs in tree-based N-body solvers.

## Features

- Two-dimensional Barnes-Hut N-body benchmark workload.
- C++ and Rust implementations.
- Five solver variants:
  - V1: direct summation baseline.
  - V2: pointer-based quadtree.
  - V3: contiguous index-based quadtree.
  - V4: iterative threaded-tree traversal.
  - V5: parallel force evaluation.
- C++ parallel implementation using OpenMP.
- Rust parallel implementation using Rayon.
- Radius-based multipole acceptance criterion.
- Force snapshots and RMS/p95 accuracy regression against direct summation.
- One-process-per-row raw data and scripts that reproduce all manuscript figures.

## Repository structure

    cpp/                  C++ implementations and generator
    nbody_rust/           Rust implementations
    docs/                 Documentation of variants and reproduction notes
    scripts/              Build, benchmark, and plotting scripts
    results/              Publication raw data and a clearly marked historical workbook
    CMakeLists.txt        CMake build configuration for C++
    CITATION.cff          Citation metadata
    LICENSE               MIT license

## Solver variants

The solver variants are described in:

    docs/variants.md

The intended SoftwareX scope and limitations are described in:

    docs/softwarex_scope.md

## Benchmark data

The v1.1.3 manuscript results are generated as one row per independent process,
with separate raw data, summaries, logs, and environment metadata. The old
aggregate-only workbook is retained solely for provenance at:

    results/historical/Results_data_v1.0_historical.xlsx

It is not used to generate the v1.1.3 manuscript figures.

## C++ source files

The C++ variants are located in:

    cpp/

The current C++ implementation files are:

    bh_v1_direct.cpp
    bh_v2_pointer_tree.cpp
    bh_v3_vector_tree.cpp
    bh_v4_threaded_tree.cpp
    bh_v5_parallel_force.cpp

## Building the C++ implementations

The recommended C++ build uses CMake:

    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
    cmake --build build --config Release

Alternatively, use the helper script:

    bash scripts/build_cpp.sh

Manual Clang build commands are provided in:

    docs/reproducing_results.md

## Building the Rust implementations

From the repository root:

    cd nbody_rust
    cargo build --release --bins

Alternatively, use the helper script:

    bash scripts/build_rust.sh

## Rust binaries

The Rust variants are located in:

    nbody_rust/src/bin/

The current binaries are:

    bh_v1_direct.rs
    bh_v2_pointer_tree.rs
    bh_v3_vector_tree.rs
    bh_v4_threaded_tree.rs
    bh_v5_parallel_force.rs

Every solver accepts the same `--input`, `--particles`, `--frames`,
`--warmup-frames`, and `--dump-forces` options. V5 also accepts `--threads N`.

    cd nbody_rust
    cargo run --release --bin bh_v1_direct -- --input ../data/start_1000.txt --particles 1000 --frames 5

## Reproducing results

Generate a deterministic input and run a selective 10-repeat benchmark:

    bash scripts/generate_input.sh 1000 data/start_1000.txt 1337
    bash scripts/run_benchmarks.sh --input data/start_1000.txt --particles 1000 \
      --frames 5 --warmup-frames 1 --repeats 10 \
      --languages cpp,rust --variants v2,v3,v4,v5

The benchmark protocol is summarized in:

    docs/benchmark_protocol.md

The runner creates a new UTC-dated directory below `results/generated/` and
refuses to overwrite an existing result directory. Every repeat is a block in
which each selected configuration runs once in a deterministically shuffled
order. The raw data record the order seed and block position together with
unambiguous timings, the input hash and seed, CPU/RAM/OS and power metadata,
process affinity, compiler versions, and the effective V5 thread count.

Reproduce all three manuscript experiments and plots with:

    bash scripts/reproduce_all_figures.sh results/reproduced/$(date -u +%Y%m%dT%H%M%SZ)

The full 1M-5M scaling experiment is intentionally a long-running workload.
Plotting requires Python 3 and the pinned Matplotlib version from
`requirements.txt`. Numerical correctness can be checked independently with
`bash scripts/numerical_regression.sh`.

## Software metadata

Additional software metadata are provided in:

    docs/software_metadata.md

## Authors

The author list is provided in:

    AUTHORS.md

## License

This project is distributed under the MIT License. See:

    LICENSE

## Citation

If you use this software, please cite the associated SoftwareX article and the
software release matching the results. The latest public archive before the
v1.1.3 release is v1.1.2:

    https://doi.org/10.5281/zenodo.22112969

Citation metadata are provided in:

    CITATION.cff
