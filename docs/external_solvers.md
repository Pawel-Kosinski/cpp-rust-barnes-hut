# Comparing external and multi-file implementations

`scripts/run_suite.py` accepts a JSON manifest rather than deriving compilation
commands from solver filenames. A solver may use CMake, Cargo, Make, a wrapper,
or a previously compiled executable. The original shell scripts remain shortcuts
for the ten bundled implementations.

Each entry has an `id`, `cwd` (relative to the manifest), optional `build` list of
argument arrays, and one `command` argument array. No command is passed to a
shell. Build commands run only with `--build`, once before the repetitions.
Paths containing spaces are single JSON string elements, not quoted shell code.
Optional `environment` string pairs override variables for the measured process
and are included in its record and cache identity. Inspect these overrides as
carefully as the command itself.

```json
{"implementations": [{
  "id": "external-tree",
  "cwd": "../external-project",
  "build": [["cmake", "-S", ".", "-B", "build", "-DCMAKE_BUILD_TYPE=Release"],
            ["cmake", "--build", "build", "--config", "Release"]],
  "command": ["build/external-tree", "--input", "{input}",
              "--frames", "{frames}", "--warmup-frames", "{warmup}",
              "--theta", "{theta}", "--threads", "{threads}", "--dt", "{dt}"]
}]}
```

Use the appropriate executable path for Windows (for example
`build/Release/external-tree.exe`). Placeholders are `input`, `frames`, `warmup`,
`theta`, `threads`, and `dt`. Literal braces must be escaped as `{{` and `}}`
in command arguments. Adapters may translate these flags or normalize
stdout; they must not silently change the force law, integration scheme, timing
scope, or input. Specify adapter scripts/shared libraries in the optional
`artifacts` list so their hashes participate in resume checks.

The input consists of five whitespace-separated columns: x, y, vx, vy, mass.
The required stdout lines are `Tree construction time: ... ms / frame`,
`Force/update time: ... ms / frame`, `Cleanup time: ... ms / frame`, and
`Total measured time: ... ms` (the sum over all measured frames). Optional
`Force kernel time` and `State update time` lines distinguish traversal from
integration. Timings exclude input, diagnostics, file output, and warm-up frames.
For the bundled V2, cleanup includes tree destruction; arena capacity is reused
by V3--V5, and its final process-exit deallocation is outside frame timing.

```bash
python scripts/run_suite.py --manifest solvers.json --build \
  --input data/smoke_input.txt --output results/generated/external \
  --frames 5 --warmup 1 --repeats 5 --threads 4
```

Results contain separate stdout/stderr logs and JSON command records, input and
executable hashes, process wall time, phase times, and randomized block order.
Process wall time is NOT the frame-time metric. Resume refuses stale results
after input, command, executable, or declared artifact changes. A new output
directory is required for a changed experiment. Build commands run user-supplied
programs: inspect a manifest before running one from an untrusted source.
