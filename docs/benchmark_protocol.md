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

The benchmark separates the main runtime components:

- tree construction time,
- force-evaluation time,
- total execution time where applicable.

The implementations also include cycle-count measurements for selected experiments.

## Memory measurements

The benchmark records memory-footprint estimates for the solver variants. These measurements are intended to support comparison of data layout and node representation choices.

## C++ implementation

The C++ implementation uses C++17. The parallel force-evaluation variant uses OpenMP.

## Rust implementation

The Rust implementation uses release-mode builds. The parallel force-evaluation variant uses Rayon.

## Result data

The result workbook used for the manuscript is stored in:

    results/Results_data.xlsx

The workbook contains the benchmark measurements used to prepare the article tables and figures.

## Reproducibility notes

The exact large-scale timings depend on hardware, compiler version, operating system, and runtime configuration. The repository therefore provides both the source code and the result workbook used in the manuscript.
