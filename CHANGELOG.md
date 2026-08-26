# Changelog

## 1.1.3 - unreleased

- Prevented Barnes-Hut nodes that contain the target particle from being accepted as aggregates.
- Added exact leaf handling for coincident particles without modifying their input positions.
- Expanded numerical regression to multiple theta values, unequal masses, coincident positions, and an explicit self-interaction case.
- Changed benchmark execution to deterministic blocked randomization and recorded order, power-state, affinity, and plotting metadata.
- Defined generator sampling directly from `std::mt19937` outputs and added a repeatability check.
- Enabled C++ interprocedural optimization when supported, matching the Rust release LTO policy.
- Removed the unused Rust `rand` dependency and added contribution guidance.

## 1.1.2 - 2026-08-26

- Replaced the historical aggregate-only workflow with raw, one-process-per-row publication data.
- Added warm-up frames, explicit phase units, selective runners, timestamped outputs, and archive-safe environment metadata.
- Added scripts that reproduce manuscript Figures 1-3 and removed timestamp-counter cycle plots.
- Added deterministic force snapshots and RMS/p95 numerical regression for all C++ and Rust variants.
- Split the C++ V3 and V4/V5 node layouts, switched C++ timing to `steady_clock`, and enabled compiler warnings.
- Extended CI to test pushes, tags, numerical correctness, and the standalone source archive.

## 1.1.1 - 2026-08-26

- Corrected benchmark summaries to report sample standard deviations.
- Added regression and smoke tests to the Linux CI job.
- Added the archived Zenodo DOI to citation and software metadata.

## 1.1.0 - 2026-08-25

- Added common benchmark CLI options and a raw-data benchmark runner.
- Added Release CMake configuration, mandatory OpenMP for V5, and Linux/Windows CI.
- Removed unsynchronised timestamp-counter reporting.
