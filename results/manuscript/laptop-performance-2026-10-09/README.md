# Separate laptop Performance repetition: 9 October 2026

This archive preserves the second complete i7-11370H campaign, separately
from `../laptop-2026-10-09/`. The operator declared Armoury Crate Performance
mode, and Windows reported its Performance power plan. Neither is an
independent sensor readout of the internal Armoury Crate mode. The first
series records a Windows Turbo-labelled plan, with no operator confirmation
of its internal Armoury Crate mode.

The second run completed at 10:12 UTC with 430 successful processes and no
pending mirrored files: 376 timing runs and 54 numerical checks. Both the
independent Python audit and the PowerShell fingerprint audit pass. The
runner's original audit remains unchanged under `raw/`.

- `payload/`: the 67 manifest-listed files, original manifest and SHA256SUMS.
- `raw/`: original complete plan, records, attempts, environment and logs.
- `analysis/audit.json`: recomputed force/timing metrics and 914 artifact hashes.
- `analysis/fingerprint-audit.txt`: environment and all 430 case fingerprints.
- `analysis/profile_comparison.json`: both series, all descriptive statistics,
  environment declarations, source CSV hashes and 54 matched force hashes.
- `analysis/matched_configurations.csv`: all 112 configuration comparisons.

Kit manifest SHA-256:
`daecf39f668dec183e5b241761d481b6331182c8473c1f4f817c893ac62455cb`.
Environment fingerprint:
`0896dc58aa966c76267717d66f2b35888898c47819037a536653271bf3ab8d14`.
The ten executables, four DLLs, 14 inputs and three references match the
first series, as does the explicit case order. No recompilation took place.
All 54 force files match between laptop series, including V1; all 48
approximate force files in each series also match Ryzen byte for byte.

## Interpretation

The V2 > V3 > V4 > V5 mean ordering holds for all nine workload inputs in
both languages in both series. This is not a significance test of every gap.
The median change in configuration mean frame time is -0.32%, with 59 lower
and 53 higher means. Overall median CV is 4.61% versus 4.71% initially;
maximum CV is 20.44% versus 33.74%. Median CV improves in scaling but rises
in the small-system baseline. Exactly 56 of 112 configurations have lower CV.
All observations are retained, including slow processes.

At one million particles and eight workers, frame self-speedups are
3.91 +/- 0.04 (C++) and 3.71 +/- 0.13 (Rust); kernel self-speedups are
4.56 +/- 0.10 and 4.28 +/- 0.18. These are means of five within-block ratios
with 95% Student-t CI half-widths, not ratios of mean times.

The two series were sequential, not a randomized power-mode crossover.
Thermal conditions, frequencies and instantaneous background interference
were not measured. Do not infer causal profile effects, population-level
uncertainty, statistical equivalence or a universal improvement. The first
series is neither discarded nor pooled with this repetition.

## Reproduction

From the repository root, with Python/NumPy/Matplotlib installed:

```powershell
python scripts/audit_laptop.py --kit results/manuscript/laptop-performance-2026-10-09/payload --run results/manuscript/laptop-performance-2026-10-09/raw --ryzen results/manuscript/extended-2026-10-08 --output results/generated/performance-audit
powershell -File scripts/audit_laptop_fingerprints.ps1 -Kit results/manuscript/laptop-performance-2026-10-09/payload -Run results/manuscript/laptop-performance-2026-10-09/raw
python scripts/compare_laptop_profiles.py --first results/manuscript/laptop-2026-10-09 --performance results/manuscript/laptop-performance-2026-10-09 --output results/generated/profile-comparison --figures results/generated/profile-comparison/figures --tables results/generated/profile-comparison/tables.tex
python scripts/test_laptop_profiles.py
```

These analysis commands do not rerun solver benchmarks. This campaign
accompanies version 1.2.0, DOI https://doi.org/10.5281/zenodo.23286007.
The frozen payload retains its original pre-release source/build labels.
Extract the companion data archive before running the audits, as described
in `docs/release_archive.md`.
