# Extended validation and timing

These version 1.2.0 workflows supplement, rather than overwrite, the original
v1.1.3 measurement campaign archived with v1.1.5. They require Python 3.11 or
newer; install `requirements.txt` for the NumPy analysis and Matplotlib plots.
The original generators and default solver parameters remain available.

## Common diagnostic options

All ten solvers accept:

| Option | Meaning |
| --- | --- |
| `--dt VALUE` | Positive finite timestep; default 0.016. |
| `--diagnostics FILE` | CSV of momentum, angular momentum, kinetic, potential and total energy. Disabled by default. |
| `--diagnostic-stride N` | Positive sampling stride; always also records initial and final states. |
| `--dump-state FILE` | Final x, y, vx, vy, mass, in the input-compatible format. |
| `--memory-report FILE` | First measured tree's structural sizes, capacities and live heap-block count. |
| `--dump-forces FILE` | Accelerations before the first measured update, as in the original interface. |
| `--force-samples N` | Evenly spaced force-dump indices; 0 (default) means all targets. It does not reduce the solver's force work. |

The state update is first-order kick-drift Euler. For G=epsilon=1 and the
implemented short-distance cutoff, the pair potential is
`-m_i*m_j*atan2(1, max(r, sqrt(1e-5)))`, not the Plummer potential. Its double
precision reduction costs O(N^2): enable it only for small validation systems.
Barnes-Hut's target-dependent aggregation does not ensure momentum or angular
momentum conservation, and reducing the timestep at fixed theta does not remove
force-approximation error. No production astrophysical accuracy is promised.

## Timing and memory definitions

`Force kernel time` excludes integration. `State update time` measures the
kick/drift update. Their sum is the backward-compatible `Force/update time`.
The total measured frame time sums tree, force/update and V2 cleanup. Input
parsing, warm-up, diagnostics, snapshots, process startup and arena destruction
at process exit are excluded. Snapshot writes were previously inside the
force/update interval when requested; they are now outside it. Historical
timing runs did not request snapshots and their data are not modified.

Memory reports are structural accounting, not allocator instrumentation or
peak RSS. V2 has a live heap block per node (except the Rust root, which is on
the stack). Arenas have one live backing block, but may have reallocated while
growing. Reserved bytes include unused vector capacity, particles and the Rust
V5 force buffer; allocator headers and worker stacks are excluded. Cache
locality is a hypothesis requiring hardware counters, not a measurement made
by these reports.

## Reproduction

Build both languages, then run the campaign sequentially on an otherwise quiet
machine. Do not run competing CPU workloads during timing measurements.

```bash
python scripts/extended_validation.py --cpp-dir build \
  --output results/generated/extended
python scripts/probe_wait_policy.py results/generated/extended
python scripts/plot_extended_results.py results/generated/extended \
  --output results/generated/extended/figures
python scripts/test_extended.py --cpp-dir build
```

Use `--section baseline`, `workload`, `scaling`, `accuracy-small`,
`accuracy-large`, or `dynamics` for separate runs. The default `all` produces
the combined accuracy CSV needed by the plotting script. The standalone
small/large sections instead write their own separate CSVs.

The three distributions are generated with `bh_generator N OUTPUT SEED DIST`,
where DIST is `plummer` (unchanged default), `uniform`, or `clustered`. The
additional velocity fields are workloads, not equilibrium initial conditions.
The extended methods specify the exact geometry, sample counts and error
normalizations. Large-system force checks use only 256 fixed targets; their
errors and percentiles must not be reported as full-system bounds.

The source and binary identities are frozen before execution. Resume refuses
to mix changed computational sources or inputs with earlier process records.
Use a fresh output directory after changing the solver, build, input or
hardware environment. Timing repetitions are independent processes and are
randomized in blocks. Raw logs and exact input hashes are retained. The
manuscript's extended records are in
`results/manuscript/extended-2026-10-08/`. The version 1.2.0 software/data DOI
is https://doi.org/10.5281/zenodo.23286007; it is distinct from the historical
v1.1.5 archive. Extract the companion experimental-data archive as described
in `docs/release_archive.md` before auditing the supplied campaigns.

## Second-host evidence

The completed i7-11370H campaign is preserved separately in
`results/manuscript/laptop-2026-10-09/`. It contains 430 audited processes
(376 timing runs and 54 numerical checks), the identical Ryzen executable
bytes and selected inputs, and its own environment/provenance records.
`scripts/audit_laptop.py` recomputes all summaries from raw evidence;
`scripts/audit_laptop_fingerprints.ps1` checks the PowerShell fingerprints.
`scripts/analyze_two_hosts.py` generates separate-host scaling and workload
summaries, including timing variability. Do not pool these data with Ryzen.
See that directory's README and the supplementary methods for scope and
limitations. The Windows plan name `Turbo` is recorded evidence, not an
independent observation of the Armoury Crate operating mode.

The second 430-process series is archived separately under
`results/manuscript/laptop-performance-2026-10-09/`. It records the Windows
Performance plan and an operator declaration of Armoury Crate Performance.
All 54 force outputs match the first laptop series byte for byte. The
comparison script `scripts/compare_laptop_profiles.py` keeps both timing
series, with no pooling or outlier removal. Overall median CV is similar
(4.71% versus 4.61%), with lower scaling variability but higher variability
in small-system baselines. Workload mean ordering is unchanged. The two
sequential series do not establish a causal power-mode effect.
