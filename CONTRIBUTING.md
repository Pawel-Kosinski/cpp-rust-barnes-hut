# Contributing to BHBench-CR

Contributions that improve correctness, reproducibility, portability, or the clarity of matched C++ and Rust variants are welcome.

## Development workflow

1. Create a focused branch and keep unrelated changes out of the same pull request.
2. Preserve the intended correspondence between C++ and Rust variants unless the change explicitly studies a language-specific design.
3. Build all binaries with `bash scripts/build_all.sh`.
4. Run `bash scripts/smoke_test.sh --no-build` and `bash scripts/numerical_regression.sh --no-build`.
5. Describe any benchmark-protocol change and regenerate affected result data in a new directory. Never overwrite publication data.

## Benchmark changes

Timing results are meaningful only when compared within one recorded environment. Keep one independent process per raw CSV row, preserve blocked configuration randomization, and record new protocol parameters in `environment.json` and the raw schema.

Generated inputs must have a documented deterministic mapping from seed to values. Numerical changes should include a direct-summation regression case, especially for tree-boundary, coincident-position, unequal-mass, and self-interaction behavior.

## Pull requests

Explain the user-visible or scientific effect, list the commands used for verification, and identify any result files that were regenerated. Do not include build products, local virtual environments, or temporary benchmark directories.
