# Reproducing the benchmark results

The benchmark results used in the article are provided in:

`results/Results_data.xlsx`

The repository contains both C++ and Rust implementations of the same two-dimensional Barnes-Hut benchmark workload.

## C++ build with CMake

From the repository root, run:

    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
    cmake --build build --config Release

## Manual C++ build with Clang

Alternatively, the C++ files can be compiled manually with Clang:

    clang++ -O3 -std=c++17 cpp/generator.cpp -o bh_generator
    clang++ -O3 -std=c++17 cpp/bh_v1_direct.cpp -o bh_cpp_v1
    clang++ -O3 -std=c++17 cpp/bh_v2_pointer_tree.cpp -o bh_cpp_v2
    clang++ -O3 -std=c++17 cpp/bh_v3_vector_tree.cpp -o bh_cpp_v3
    clang++ -O3 -std=c++17 cpp/bh_v4_threaded_tree.cpp -o bh_cpp_v4
    clang++ -O3 -std=c++17 -fopenmp cpp/bh_v5_parallel_force.cpp -o bh_cpp_v5

## Rust build

From the repository root, run:

    cd nbody_rust
    cargo build --release --bins

## Notes

The large-scale benchmark data reported in the article were collected on the workstation described in the manuscript. The source code, result workbook, and solver variants are provided to support reproducibility and further comparative experiments.

## Input-data generation

The C++ generator can create deterministic Plummer-distribution input files. The default seed is 1337.

Example:

    bash scripts/generate_input.sh 1000 data/start_1000.txt 1337

Equivalent direct command after building the C++ targets:

    ./build/bh_generator 1000 data/start_1000.txt 1337

All variants consume the same explicit input and frame count. Run:

    bash scripts/run_benchmarks.sh --input data/start_1000.txt --particles 1000 --frames 5 --repeats 10 --theta 0.3

The command writes `raw_runs.csv`, `summary.csv`, per-run logs, and
`environment.json` below `results/generated/`. The summary reports the mean and
sample standard deviation across process runs. Generate figures with
`python scripts/plot_results.py results/generated/summary.csv results/generated`
(requires `matplotlib`).
