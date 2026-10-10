# Extended campaign, 8-9 October 2026

This completed campaign is included with version 1.2.0, whose software/data
DOI is https://doi.org/10.5281/zenodo.23286007. It is not a replacement for
the immutable original results in `../v1.1.3`. The measurements used the
frozen development source based on v1.1.5, not a retrospectively rebuilt
release binary. Source manifests, exact inputs and raw records are unchanged.
See `docs/release_archive.md` for the required companion data archive.

## Provenance

- `environment.json`: measured workstation, compiler flags, runtime versions,
  base commit and timing protocol. One Ryzen 7 5800X3D, 8 physical cores,
  16 logical processors, Windows 11, GCC 16.2.0 and Rust 1.98.0.
- `source_identity.json`: SHA-256 of the exact computational sources, build
  definitions, generator and independent reference binary. The base commit
  alone is NOT the identity of these then-uncommitted computational changes.
- `computational_source.zip`: exact computational files used for this run,
  plus license and identity manifest. Build these files with the surrounding
  repository; this small archive is a provenance snapshot, not the full package.
- `input_manifest.csv`: hashes and sizes of 22 exact input files. Large inputs
  are excluded from Git and must accompany the release as a separate archive.
- `logs/`: 766 successful process JSON records and matching stdout/stderr.
  Absolute paths document the original machine; new runs need a fresh output
  directory and newly generated manifests, not edits to historical records.
- `analysis_environment.json`: versions used for derived figures/tables,
  separate from the NumPy 2.3.5 reference-integration environment.
- `audit.json`: successful local integrity audit, including recomputation of
  all 232 force-comparison summaries. Binary verification uses the original
  recorded paths and therefore requires the original executable files.

## Coverage

| Output | Rows | Protocol |
| --- | ---: | --- |
| `baseline.csv` | 60 | V1-V5, both languages; N=1,000 and 10,000; 3 process repetitions |
| `workload.csv` | 216 | V2-V5, both languages; N=100,000; 3 distributions x 3 seeds x 3 repetitions |
| `scaling.csv` | 120 | V5 at 1, 2, 4, 8, 16 workers plus V4; N=100,000 and 1,000,000; 5 repetitions |
| `wait_policy.csv` | 25 | C++ serial/one-worker controls and default, ACTIVE, PASSIVE at 16 workers; 5 repetitions |
| `accuracy.csv` | 232 | 216 full-target checks at N=10,000 plus 16 sampled checks at N=1M and 5M |
| `memory.csv` | 24 | Structural bytes, node sizes/capacity and live tree heap blocks; 3 distributions |
| `dynamics.csv` | 78 | All variants; 3 timesteps; 3 BH thresholds; N=256, T=0.256 |

The 766 processes comprise 421 timing processes, 232 approximate force runs,
11 direct-reference runs, 24 memory runs and 78 dynamics runs. Float64 RK4
reference integration executes within Python and is not a solver process.
Input workloads use Plummer, uniform-disk and four-cluster distributions,
with seeds 1337, 42 and 2026. They are not equilibrium models.

## Interpretation

The nine tested inputs retain the V2 > V3 > V4 > V5 ordering of mean frame
times in both languages. Three repetitions do not resolve the significance
of every small difference. V5 self-scaling uses five paired within-block
ratios and Student-t 95% intervals; it is not the historical V4/V5 ratio.
The controlled waiting-policy probe does not reproduce a persistent C++ V5
builder slowdown and does not establish the cause of an earlier observation.

Force references use double summation from float32-rounded input. Large-system
results cover 256 fixed indices only, not a full-system bound. Memory reports
exclude allocator and runtime overhead and are not peak RSS. Arena capacity
slack can increase reserved bytes despite drastically fewer live heap blocks.

Dynamics use a force-consistent arctangent pair potential, not Plummer
softening. First-order timestep convergence is distinct from BH approximation
error. The independently refined RK4 trajectory uses dt=0.000125; comparison
with dt=0.00025 gives normalized position/velocity differences of
1.9012e-7 / 9.7190e-6. This is an empirical refinement check, not a rigorous
error bound. Invariant histories are retained as `dynamics_*.csv` and final
states as `dynamics_*.txt` in this directory; force samples are in `forces/`.

See `docs/extended_validation.md` and the supplementary methods for full
definitions, caveats and reproduction commands. No timing rows have been
removed as outliers. These results concern one workstation, not an isolated
HPC node or a portable language-performance ranking.
