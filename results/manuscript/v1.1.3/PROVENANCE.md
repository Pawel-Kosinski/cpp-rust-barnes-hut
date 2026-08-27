# Measurement provenance

The v1.1.3 publication measurements were generated from commit
`ab17547228b0f7440793c9014bfda41d076a239e`. Every `environment.json` and raw CSV
row records that commit.

The v1.1.3 GitHub release points to merge commit
`32a27f73351786448cb5a44e0fa34c7e1e673371`. Between the measurement and release
commits, the solver sources, input generator, CMake and Cargo release profiles,
summary-statistics script, and manuscript plotting formulas were unchanged.
The intervening changes added the recorded result files and documentation,
allowed `collect_environment.py` to honor `CMAKE_COMMAND`, and added a validated
`--resume` path to the runner. A fresh non-resumed run retained the measurement
protocol and executable invocations.

Release v1.1.4 corrects only the interpretation and plotting of V4/V5 parallel
speedup, adds archival input documentation, and updates packaging metadata. It
does not alter the recorded timings or claim that they were regenerated from a
later commit.

Release v1.1.5 synchronizes the version-specific DOI, release date, citation,
package, repository, and manuscript metadata. The solver sources, benchmark
measurements, publication inputs, and figures remain unchanged.
