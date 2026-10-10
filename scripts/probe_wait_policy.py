#!/usr/bin/env python3
"""Controlled libgomp wait-policy sensitivity probe; no solver source changes."""
import argparse
import json
import os
from pathlib import Path
import random

from extended_validation import table, parameters
from run_suite import implementations, run_case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaign', type=Path)
    args = parser.parse_args()
    root = args.campaign.resolve()
    solvers = {s['id']: s for s in implementations(root / 'manifest.json')}
    captured = {k: v for k, v in os.environ.items() if k.startswith(('OMP_', 'GOMP_', 'KMP_', 'RAYON_'))}
    if any(k in captured for k in ('OMP_WAIT_POLICY', 'GOMP_SPINCOUNT')):
        raise ValueError('Unset ambient OMP_WAIT_POLICY and GOMP_SPINCOUNT for the default-policy control')
    (root / 'runtime_environment.json').write_text(json.dumps(captured, indent=2), encoding='utf-8')
    cases = [('cpp_v4', 1, 'default'), ('cpp_v5', 1, 'default'), ('cpp_v5', 16, 'default'),
             ('cpp_v5', 16, 'ACTIVE'), ('cpp_v5', 16, 'PASSIVE')]
    rows, rng = [], random.Random(20261009)
    for repeat in range(5):
        order = cases.copy()
        rng.shuffle(order)
        for solver, threads, policy in order:
            implementation = dict(solvers[solver])
            implementation['id'] += '_' + policy.lower()
            implementation['environment'] = {} if policy == 'default' else {'OMP_WAIT_POLICY': policy}
            key = f'wait_{solver}_t{threads}_{policy}_r{repeat}'
            print(key, flush=True)
            record = run_case(implementation, parameters(root / 'input_plummer_100000_1337.txt', frames=5,
                warmup=1, threads=threads), root / 'logs' / key)
            rows.append(dict(solver=solver, threads=threads, policy=policy, repeat=repeat, **record['metrics']))
    table(root / 'wait_policy.csv', rows)


if __name__ == '__main__':
    main()
