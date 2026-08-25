# BHBench-CR

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22102924.svg)](https://doi.org/10.5281/zenodo.22102924)

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
- Force-based accuracy metrics against direct summation.
- Benchmark data used in the associated manuscript.

## Repository structure

    cpp/                  C++ implementations and generator
    nbody_rust/           Rust implementations
    docs/                 Documentation of variants and reproduction notes
    scripts/              Build, benchmark, and plotting scripts
    results/              Archived workbook and generated raw results
    CMakeLists.txt        CMake build configuration for C++
    CITATION.cff          Citation metadata
    LICENSE               MIT license

## Solver variants

The solver variants are described in:

    docs/variants.md

The intended SoftwareX scope and limitations are described in:

    docs/softwarex_scope.md

## Benchmark data

The benchmark data used to generate the manuscript figures and tables are provided in:

    results/Results_data.xlsx

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

Every solver accepts the same `--input`, `--particles`, and `--frames` options.
V5 also accepts `--threads N`.

    cd nbody_rust
    cargo run --release --bin bh_v1_direct -- --input ../data/start_1000.txt --particles 1000 --frames 5

## Reproducing results

Generate a deterministic input and run the complete 10-repeat benchmark:

    bash scripts/generate_input.sh 1000 data/start_1000.txt 1337
    bash scripts/run_benchmarks.sh --input data/start_1000.txt --particles 1000 --frames 5 --repeats 10
    python scripts/plot_results.py results/generated/summary.csv results/generated

The benchmark protocol is summarized in:

    docs/benchmark_protocol.md

The runner writes raw measurements, summary statistics, logs, and environment
metadata to `results/generated/`. Historical workbook values are retained as an
archive and should not be treated as a replacement for raw run data.

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

If you use this software, please cite the associated SoftwareX article and the archived v1.1.1 release:

    https://doi.org/10.5281/zenodo.22102924

Citation metadata are provided in:

    CITATION.cff
