# SoftwareX scope

BHBench-CR is a compact benchmark suite for studying implementation-level trade-offs in two-dimensional Barnes-Hut N-body solvers.

The purpose of the repository is to support reproducible comparison of:

- pointer-based and contiguous tree representations,
- recursive and iterative tree traversal,
- serial and parallel force evaluation,
- C++/OpenMP and Rust/Rayon implementations.

The software is intentionally scoped as a benchmark and research/teaching codebase. It is not intended to be:

- a production astrophysical simulator,
- a state-of-the-art three-dimensional tree code,
- a replacement for highly optimized N-body libraries,
- a Fast Multipole Method implementation,
- a full physical modelling package.

The benchmark focuses on implementation trade-offs, memory layout, traversal structure, and parallel runtime effects under a controlled workload. The manuscript figures are generated from one-process-per-row raw CSV data, with the exact protocol and execution environment stored alongside each experiment.
