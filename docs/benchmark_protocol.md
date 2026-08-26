# Benchmark protocol

This document summarizes the benchmark protocol used by BHBench-CR.

## Problem setting

BHBench-CR evaluates two-dimensional N-body solver variants based on the Barnes-Hut approximation. The benchmark is designed to study implementation-level trade-offs rather than to provide a production astrophysical simulator.

The main implementation dimensions are:

- tree node representation,
- memory layout,
- recursive versus iterative traversal,
- serial versus parallel force evaluation,
- C++/OpenMP versus Rust/Rayon implementation choices.

## Physical and numerical parameters

The benchmark uses a simple two-dimensional gravitational N-body model with:

- gravitational constant G = 1.0,
- time step dt = 0.016,
- softening term used in the force calculation,
- single-precision floating-point arithmetic for the simulation state,
- double-precision arithmetic for selected diagnostic calculations.

The default Barnes-Hut multipole acceptance threshold used in the manuscript experiments is theta = 0.3.

## Multipole acceptance criterion

The benchmark uses a radius-based multipole acceptance criterion. The cell radius is based on the cell size, and the acceptance test compares this radius with the distance from the particle to the node center of mass.

## Accuracy reference

The direct summation implementation is used as the reference for force-accuracy measurements. Accuracy is evaluated by comparing Barnes-Hut forces with direct-summation forces.

The manuscript reports force-based error metrics, including:

- global RMS relative force error,
- 95th percentile of local relative force error.

## Timing measurements

All C++ timers use `std::chrono::steady_clock`; Rust uses `Instant`. Each process
executes the requested warm-up frames before timing values are accumulated. The
measured region is then reported as:

- `tree_ms_per_frame`: tree construction and arena reset,
- `force_update_ms_per_frame`: force evaluation and the common state update,
- `cleanup_ms_per_frame`: explicit recursive tree destruction in V2,
- `total_ms_per_frame`: the sum of the measured phases per frame,
- `total_run_ms`: the sum of the measured phases across all measured frames.

Input parsing, process startup, diagnostics, and warm-up frames are outside these
values. Processor timestamp-counter values are not reported because they are not
synchronised CPU-cycle measurements across cores or platforms.

## Memory measurements

The benchmark records memory-footprint estimates for the solver variants. These measurements are intended to support comparison of data layout and node representation choices.

## C++ implementation

The C++ implementation uses C++17. The parallel force-evaluation variant uses OpenMP.

## Rust implementation

The Rust implementation uses release-mode builds. The parallel force-evaluation variant uses Rayon.

## Result data

`scripts/run_benchmarks.sh` writes one raw CSV row for every independent process.
Each row includes language, variant, particle count, measured and warm-up frames,
theta, seed, requested and effective thread counts, phase timings, total timings,
source version and commit, and the corresponding log path. `summary.csv` stores
numeric means and sample standard deviations in separate columns.

`environment.json` records the input SHA-256 hash, CPU model, physical and
logical cores, physical memory, OS, compiler and tool versions, C++ compile
commands/flags, the effective parallel thread count, and all protocol parameters.
The runner uses an archive-safe source identifier when `.git` is absent.

The old aggregate workbook is retained only as
`results/historical/Results_data_v1.0_historical.xlsx`; it is not an input to the
v1.1.2 manuscript figures.

## Manuscript experiments

The release provides one script per figure:

- `reproduce_fig1.sh`: V3 timing and direct-force RMS/p95 over a theta sweep,
- `reproduce_fig2.sh`: V2-V5 at N=100,000,
- `reproduce_fig3.sh`: V3-V5 at N=1M, 2M, and 5M,
- `plot_manuscript_figures.py`: figures generated only from the resulting CSVs.

Compared points within an experiment use the same seed, warm-up count, measured
frame count, repeat count, and thread policy. Defaults are embedded in each
script and are also written into the result metadata.

## Reproducibility notes

The exact timings depend on hardware, compiler version, operating system, and
runtime configuration. Comparisons are therefore valid within one recorded
environment; results from different workstations must not be merged into one
series. Force snapshots and `scripts/numerical_regression.sh` provide a separate
deterministic correctness check for V2-V5 against direct summation in both
languages.
