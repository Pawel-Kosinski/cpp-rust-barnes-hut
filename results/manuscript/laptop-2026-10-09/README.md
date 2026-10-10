# Recorded laptop campaign: 9 October 2026

This directory preserves the completed i7-11370H campaign separately from the
Ryzen data. The Windows power-plan label was `Turbo`; the actual internal
Armoury Crate mode was not independently read. No observations were discarded.

- `payload/`: original kit files, identical solver binaries/DLLs, exact inputs,
  stored Ryzen double-precision force references, source provenance and licenses.
- `raw/`: original synchronized complete run, 430 successful process records,
  per-attempt logs/force dumps, commands, environment, power settings and plan.
- `analysis/audit.json`: independent Python audit of records, hashes, CLI and
  summary values, including re-evaluation of all 54 numerical comparisons.
- `analysis/two_host_summary.json`: separate host summaries, within-block V5
  speedup intervals, workload mean ratios, and configuration-level mean/SD/CV.

The kit manifest SHA-256 is
`0c87ef6469e8150fb59ffe8df9dffc3052368e0dbbb73dbc73985f9b8ab8041b`.
The raw environment fingerprint is
`a9a02af061a2f3e0ae59ea516e8affd740c06ad472c352af43f91e217bcebd7e`.
There are 376 timing processes (60 baseline, 216 workload, 100 scaling) and
54 numerical checks. The 48 approximate force dumps match the corresponding
Ryzen dumps byte for byte; this is not a claim about other compilers or inputs.

Recompute the audit without changing raw data:

```powershell
python scripts/audit_laptop.py --kit results/manuscript/laptop-2026-10-09/payload --run results/manuscript/laptop-2026-10-09/raw --ryzen results/manuscript/extended-2026-10-08 --output results/generated/laptop-audit
powershell -File scripts/audit_laptop_fingerprints.ps1 -Kit results/manuscript/laptop-2026-10-09/payload -Run results/manuscript/laptop-2026-10-09/raw
```

Both checks passed on 9 October. The original runner's audit is retained in
`raw/audit.json`; it has not been replaced by the independent audit.

Both hosts are non-isolated Windows workstations. The laptop's median
frame-time CV across 112 timing configurations is 4.71%, maximum 33.74%.
The observed mean ordering is not a significance claim for every small gap.
Temperature, clock frequency, hardware counters and background-load time
series were not measured. Windows builds and power policies differ between
hosts. Do not attribute differences solely to CPU architecture or language.

An operator-declared Performance repetition completed the same 430-case plan
on 9 October. Its independently audited results are preserved separately in
`../laptop-performance-2026-10-09/`, not in this archive. All 54 force files
match between the series. The comparison preserves every observation and
does not establish a causal power-mode effect. The new measurements must not
overwrite, be pooled with, or silently replace these measurements.
This campaign accompanies version 1.2.0, DOI
https://doi.org/10.5281/zenodo.23286007. The frozen payload retains its original
pre-release source/build labels; they are provenance, not current release
metadata. Extract the companion data archive before running these audits
(see `docs/release_archive.md`).
