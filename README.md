# BHBench-CR

BHBench-CR is a C++/Rust benchmark suite for two-dimensional Barnes-Hut N-body solver variants. It is intended for reproducible implementation experiments, teaching, and comparative studies of data layout, traversal strategy, and parallel force evaluation in C++/OpenMP and Rust/Rayon.

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
    scripts/              Build helper scripts
    results/              Benchmark result workbook
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

## Building the C++ implementations

The recommended C++ build uses CMake:

    cmake -S . -B build
    cmake --build build --config Release

Alternatively, use the helper script:

    ./scripts/build_cpp.sh

Manual Clang build commands are provided in:

    docs/reproducing_results.md

## Building the Rust implementations

From the repository root:

    cd nbody_rust
    cargo build --release --bins

Alternatively, use the helper script:

    ./scripts/build_rust.sh

## Rust binaries

The Rust variants are located in:

    nbody_rust/src/bin/

The current binaries are:

    bh_v1_direct.rs
    bh_v2_pointer_tree.rs
    bh_v3_vector_tree.rs
    bh_v4_threaded_tree.rs
    bh_v5_parallel_force.rs

They can be run with commands such as:

    cd nbody_rust
    cargo run --release --bin bh_v1_direct
    cargo run --release --bin bh_v2_pointer_tree
    cargo run --release --bin bh_v3_vector_tree
    cargo run --release --bin bh_v4_threaded_tree
    cargo run --release --bin bh_v5_parallel_force

## Reproducing results

See:

    docs/reproducing_results.md

The large-scale benchmark data were collected on the workstation described in the associated manuscript. The repository provides source code and result data to support reproducibility and further comparative experiments.

## License

This project is distributed under the MIT License. See:

    LICENSE

## Citation

If you use this software, please cite the associated SoftwareX article and this repository. Citation metadata are provided in:

    CITATION.cff
