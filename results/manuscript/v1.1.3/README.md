# BHBench-CR v1.1.3 manuscript results

These results were generated from code commit
`ab17547228b0f7440793c9014bfda41d076a239e` on one AMD Ryzen 7 5800X3D
host. No measurements from another machine or release are included.

## Protocols

- Figure 1: 10,000 particles, V3, theta 0.1/0.2/0.3/0.5/0.7, three
  measured frames after one warm-up frame, and five independent processes.
- Figure 2: 100,000 particles, V2-V5, theta 0.3, five measured frames after
  two warm-up frames, and ten independent processes.
- Figure 3: 1, 2, and 5 million particles, V3-V5, theta 0.3, three measured
  frames after one warm-up frame, and five independent processes.
- Every repeat is a deterministically shuffled block containing each selected
  language/variant configuration once; the order seed is 20260826.
- Parallel V5 runs use 16 threads; V2-V4 are serial.
- All deterministic Plummer inputs use seed 1337.

Each result set contains raw process-level rows, sample-statistics summaries,
individual logs, and `environment.json`. Figure 1 also contains force dumps and
direct-summation error metrics. Generated input files are omitted from Git
because they are deterministically recreated by the workflow; each environment
record stores the generated input's SHA-256 hash.

## Reproduction

From a clean repository checkout with the documented toolchains installed:

```bash
THREADS=16 bash scripts/reproduce_all_figures.sh results/reproduced/v1.1.3
```

The output directory must not already exist. An interrupted individual runner
invocation can be continued with the same arguments plus `--resume`. See
`docs/reproducing_results.md` for selective runs and build options.
