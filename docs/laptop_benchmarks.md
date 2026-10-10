# Windows laptop campaign

`scripts/build_laptop_kit.py` freezes a separate, Windows x64 kit from the
audited `results/manuscript/extended-2026-10-08` campaign. It verifies source,
input and executable identities and copies (never rebuilds) the ten solvers,
their non-system DLL dependency closure, licenses, exact input files, double
precision force references, source provenance and a deterministic run plan.
The portable runner uses Windows PowerShell 5.1/.NET, not Python or a compiler.

```powershell
python scripts/build_laptop_kit.py --output ..\Laptop-BHBench-CR
```

An existing output is refused. Build only from verified campaign binaries.
The full profile deliberately requires an i7-11370H, 4 cores / 8 threads,
AC power and at least 8 GB nominal RAM. Adaptation to a different laptop
requires a new, explicitly identified profile, not disabling the checks.

The plan comprises 54 force regression checks, 60 baseline, 216 workload and
100 scaling processes. Timing definitions and per-process warmup/frame counts
match the Ryzen campaign. Thread counts stop at eight. A separate ten-process
smoke profile tests deployment and is never included in scientific tables.
See the kit's `START_HERE.txt` for complete use and limitations.

Executables and inputs are staged outside the synced directory, under
`%LOCALAPPDATA%/BHBench-CR/laptop-r1`. Completed attempts, errors and a heartbeat
are mirrored into `_wyniki/<computer-name>/` in the kit. The local cache is the
resume authority; a mirror is for sharing/diagnosis, not automatic recovery
on a different computer. A Windows file lock prevents concurrent launchers,
and a kill-on-close job terminates children if the launcher exits. No global
power, security, or execution-policy setting is modified.

Runner revision `sync-fix-1` tolerates Windows cloud-drive file locks. It first
tries atomic replacement of a mirrored file, then overwrite if rename/delete
is denied, with bounded retries. This fallback applies only to the diagnostic
mirror: local authoritative writes remain atomic. A persistent local queue
retries unavailable mirrors between cases and on relaunch. `complete_sync_pending`
means computation succeeded locally but delivery is incomplete; relaunch the
same mode rather than repeating measurements or removing the local cache.
The Status launcher prefers the local status over a possibly stale mirror.

Resume requires matching hardware, OS, power scheme, affinity, kit and case
fingerprints, and verifies successful artifact hashes. Failed/interrupted
attempts are retained and rerun. Numerical CSVs, logs and timings stay separate
from the original machine. Timings are sums of measured solver phases, not
process wall time. No temperature or hardware-counter claims are made.

## Separate Performance repetition

The first completed laptop run records the Windows plan label `Turbo`; this
is not an independent readout of Armoury Crate's internal operating mode.
Use `scripts/laptop/prepare_performance_kit.ps1` with `-SourceKit` pointing
at the verified original kit and `-Destination` a new directory. It copies
identical solvers, DLLs, inputs, references and the exact 430-case order, but
gives the experiment a new manifest identity and result namespace.

Runner `profile-guard-1` rejects the previously recorded Turbo GUID or a
Turbo-labelled plan and requests an explicit operator declaration of
Performance mode after AC is connected. The Windows plan and operator
declaration are recorded separately; no settings are changed automatically.
Status now selects this kit's namespace rather than the newest run of any kit.
The original completed run and archived payload are never modified.

Keep both series, report variability, and do not pool or select only the
faster observations. A sequential repetition does not isolate power mode
from background load or unmeasured thermal conditions.

Both full series completed on 9 October 2026. Their independently audited
snapshots are `results/manuscript/laptop-2026-10-09/` and
`results/manuscript/laptop-performance-2026-10-09/`, each with 430 successful
processes. `scripts/compare_laptop_profiles.py` verifies matched payloads,
plans and force outputs, retains all 112 timing-configuration pairs, and
generates separate statistics plus a comparison plot and tables. Both
archives document commands and scope. `scripts/test_laptop_profiles.py`
checks the statistical helpers, including retention of slow observations
and use of within-block speedup ratios.
