#!/usr/bin/env python3
"""Reproduce the supplementary workload, scaling, accuracy and dynamics campaign."""
import argparse
import csv
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import time

import numpy as np

from run_suite import implementations, run_case, sha256
import collect_environment as environment

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['direct', 'pointer_tree', 'vector_tree', 'threaded_tree', 'parallel_force']


def source_commit():
    if not (ROOT / '.git').exists():
        return 'source archive; computational identity is recorded in source_identity.json'
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return 'source archive; computational identity is recorded in source_identity.json'


def table(path, rows):
    with Path(path).open('w', newline='', encoding='utf-8') as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def setup(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    suffix = '.exe' if os.name == 'nt' else ''
    manifest = {'implementations': []}
    for language in ('cpp', 'rust'):
        for variant, name in enumerate(NAMES, 1):
            binary = args.cpp_dir / f'bh_cpp_v{variant}{suffix}' if language == 'cpp' else args.rust_dir / f'bh_v{variant}_{name}{suffix}'
            manifest['implementations'].append({'id': f'{language}_v{variant}', 'cwd': str(ROOT),
                'command': [str(binary.resolve()), '--input', '{input}', '--frames', '{frames}',
                            '--warmup-frames', '{warmup}', '--theta', '{theta}', '--threads', '{threads}', '--dt', '{dt}']})
    sources = [*ROOT.glob('cpp/*.cpp'), *ROOT.glob('cpp/*.hpp'), *ROOT.glob('nbody_rust/src/**/*.rs'),
               ROOT / 'CMakeLists.txt', ROOT / 'nbody_rust/Cargo.toml', ROOT / 'nbody_rust/Cargo.lock']
    identity = {str(p.relative_to(ROOT)): sha256(p) for p in sorted(sources)}
    identity['generator_binary'] = sha256(args.cpp_dir / ('bh_generator' + suffix))
    identity['sampled_reference_binary'] = sha256(args.cpp_dir / ('bh_sampled_direct' + suffix))
    lock = output / 'source_identity.json'
    if lock.exists() and json.loads(lock.read_text()) != identity:
        raise RuntimeError('Computational source changed; use a new campaign directory')
    manifest_path = output / 'manifest.json'
    if manifest_path.exists() and json.loads(manifest_path.read_text()) != manifest:
        raise RuntimeError('Implementation paths changed; use a new campaign directory')
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    solvers = {x['id']: x for x in implementations(manifest_path)}
    lock.write_text(json.dumps(identity, indent=2), encoding='utf-8')
    metadata_path = output / 'environment.json'
    if not metadata_path.exists():
        metadata = {'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'system': platform.platform(), 'cpu': environment.cpu_model(),
                    'physical_cores': environment.physical_core_count(), 'logical_cores': os.cpu_count(),
                    'memory_bytes': environment.physical_memory_bytes(), 'affinity': environment.process_affinity(),
                    'power': environment.power_state(), 'python': platform.python_version(), 'numpy': np.__version__,
                    'cpp': environment.command_version(['c++', '--version']),
                    'rust': environment.command_version(['rustc', '--version']),
                    'compile_commands': environment.compile_commands(args.cpp_dir),
                    'cargo_profile': 'release, lto=true, codegen-units=1',
                    'base_commit': source_commit(),
                    'source_identity': 'source_identity.json (includes uncommitted computational changes)',
                    'timing_scope': 'phase sum excluding I/O, diagnostics, warm-up and process startup',
                    'order_seed': 20261008, 'workload_repeats': 3, 'scaling_repeats': 5,
                    'workload_frames': 2, 'scaling_frames': 3, 'warmup_frames': 1}
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return output, solvers, suffix


def input_file(args, output, suffix, n, distribution, seed):
    path = output / f'input_{distribution}_{n}_{seed}.txt'
    if not path.exists():
        subprocess.run([str((args.cpp_dir / ('bh_generator' + suffix)).resolve()), str(n), str(path), str(seed), distribution], check=True, capture_output=True)
    return path


def parameters(path, frames=1, warmup=0, threads=1, theta=0.3, dt=0.016):
    return dict(input=str(path), frames=frames, warmup=warmup, threads=threads, theta=theta, dt=dt)


def timings(args, output, solvers, suffix):
    rows = []
    rng = random.Random(20261008)
    for group in ('baseline', 'workload', 'scaling'):
        if args.section not in ('all', group):
            continue
        configurations = []
        if group == 'baseline':
            for n in (1000, 10000):
                configurations.append((n, 'plummer', 1337, 3, [(s, 16 if s.endswith('v5') else 1) for s in solvers]))
        elif group == 'workload':
            for distribution in ('plummer', 'uniform', 'clustered'):
                for seed in (1337, 42, 2026):
                    configurations.append((100000, distribution, seed, 3, [(s, 16 if s.endswith('v5') else 1) for s in solvers if not s.endswith('v1')]))
        else:
            for n in (100000, 1000000):
                configurations.append((n, 'plummer', 1337, 5, [(f'{lang}_v5', t) for lang in ('cpp', 'rust') for t in (1, 2, 4, 8, 16)] + [(f'{lang}_v4', 1) for lang in ('cpp', 'rust')]))
        for n, distribution, seed, repeats, cases in configurations:
            path = input_file(args, output, suffix, n, distribution, seed)
            for repeat in range(repeats):
                order = cases.copy()
                rng.shuffle(order)
                for solver, threads in order:
                    key = f'{group}_{n}_{distribution}_{seed}_r{repeat}_{solver}_t{threads}'
                    print(key, flush=True)
                    record = run_case(solvers[solver], parameters(path, 3 if group == 'scaling' else 2, 1, threads), output / 'logs' / key)
                    rows.append(dict(group=group, n=n, distribution=distribution, seed=seed, repeat=repeat,
                                     solver=solver, threads=threads, **record['metrics']))
        table(output / f'{group}.csv', [r for r in rows if r['group'] == group])


def force_metrics(reference_path, actual_path):
    reference = np.atleast_1d(np.genfromtxt(reference_path, delimiter=',', names=True))
    actual = np.atleast_1d(np.genfromtxt(actual_path, delimiter=',', names=True))
    if not np.array_equal(reference['index'], actual['index']):
        raise ValueError('Force sample indices differ')
    ref = np.column_stack([reference['acc_x'], reference['acc_y']])
    measured = np.column_stack([actual['acc_x'], actual['acc_y']])
    difference = np.linalg.norm(measured - ref, axis=1)
    norm = np.linalg.norm(ref, axis=1)
    if not np.isfinite(measured).all() or np.any(norm == 0):
        raise ValueError('Non-finite force or zero reference norm')
    return dict(samples=len(ref), rms_relative=float(np.linalg.norm(measured-ref) / np.linalg.norm(ref)),
                p95_particle_relative=float(np.percentile(difference / norm, 95)),
                max_particle_relative=float(np.max(difference / norm)))


def accuracy(args, output, solvers, suffix):
    rows, memory = [], []
    cases = [(10000, d, seed, 0) for d in ('plummer', 'uniform', 'clustered') for seed in (1337, 42, 2026)]
    cases += [(n, 'plummer', 1337, 256) for n in (1000000, 5000000)]
    reference_binary = str((args.cpp_dir / ('bh_sampled_direct' + suffix)).resolve())
    reference_solver = dict(id='double_reference', cwd=str(ROOT), command=[reference_binary, '--input', '{input}'], executable_sha256=sha256(reference_binary), artifact_sha256={})
    for n, distribution, seed, samples in cases:
        if args.section == 'accuracy-small' and n > 10000:
            continue
        if args.section == 'accuracy-large' and n == 10000:
            continue
        path = input_file(args, output, suffix, n, distribution, seed)
        reference = output / 'forces' / f'reference_{n}_{distribution}_{seed}.csv'
        reference.parent.mkdir(exist_ok=True)
        print(f'direct reference {n} {distribution} {seed}', flush=True)
        run_case(reference_solver, parameters(path), output / 'logs' / reference.stem,
                 ['--dump-forces', reference, '--force-samples', samples], timing=False)
        for theta in ((0.1, 0.3, 0.7) if n == 10000 else (0.3,)):
            for solver in solvers:
                if solver.endswith('v1'):
                    continue
                key = f'accuracy_{n}_{distribution}_{seed}_{solver}_theta{theta}'
                dump = output / 'forces' / (key + '.csv')
                print(key, flush=True)
                run_case(solvers[solver], parameters(path, theta=theta, threads=16 if solver.endswith('v5') else 1),
                         output / 'logs' / key, ['--dump-forces', dump, '--force-samples', samples])
                rows.append(dict(n=n, distribution=distribution, seed=seed, solver=solver, theta=theta, **force_metrics(reference, dump)))
    if rows:
        name = 'accuracy' if args.section == 'all' else args.section
        table(output / f'{name}.csv', rows)
    if args.section == 'accuracy-large':
        return
    for distribution in ('plummer', 'uniform', 'clustered'):
        path = input_file(args, output, suffix, 100000, distribution, 1337)
        for solver in solvers:
            if solver.endswith('v1'):
                continue
            key = f'memory_{distribution}_{solver}'
            report = output / (key + '.csv')
            run_case(solvers[solver], parameters(path, threads=16 if solver.endswith('v5') else 1), output / 'logs' / key, ['--memory-report', report])
            with report.open() as stream:
                counts = next(csv.DictReader(stream))
            memory.append(dict(distribution=distribution, solver=solver, **counts))
    table(output / 'memory.csv', memory)


def acceleration(state):
    delta = state[None, :, :2] - state[:, None, :2]
    r2 = (delta * delta).sum(axis=2)
    valid = r2 >= 1e-5
    factor = np.zeros_like(r2)
    factor[valid] = 1 / ((r2[valid] + 1) * np.sqrt(r2[valid]))
    return (delta * (factor * state[None, :, 4])[:, :, None]).sum(axis=1)


def rk4(initial, dt, steps):
    state = initial.copy()
    def derivative(p):
        out = np.zeros_like(p)
        out[:, :2], out[:, 2:4] = p[:, 2:4], acceleration(p)
        return out
    for _ in range(steps):
        k1 = derivative(state)
        k2 = derivative(state + dt * k1 / 2)
        k3 = derivative(state + dt * k2 / 2)
        k4 = derivative(state + dt * k3)
        state += dt * (k1 + 2*k2 + 2*k3 + k4) / 6
    return state


def dynamics(args, output, solvers):
    rng = np.random.Generator(np.random.PCG64(1337))
    initial = np.zeros((256, 5))
    initial[:, :2] = rng.normal(0, 3, (256, 2))
    initial[:, :2] -= initial[:, :2].mean(axis=0)
    initial[:, 2] = -0.4 * initial[:, 1]
    initial[:, 3] = 0.4 * initial[:, 0]
    initial[:, 4] = 1
    path = output / 'input_dynamics_256.txt'
    if not path.exists():
        np.savetxt(path, initial, fmt='%.9g')
    initial = np.loadtxt(path).astype(np.float32).astype(np.float64)
    # A step-halved double-precision RK4 reference, independent of solver code.
    reference = rk4(initial, 0.000125, 2048)
    reference_coarse = rk4(initial, 0.00025, 1024)
    norms = np.array([np.linalg.norm(initial[:, :2]), np.linalg.norm(initial[:, 2:4])])
    ref_error = [float(np.linalg.norm(reference[:, i:i+2] - reference_coarse[:, i:i+2]) / norms[i//2]) for i in (0, 2)]
    (output / 'dynamics_reference.json').write_text(json.dumps(dict(method='double RK4', final_time=0.256, step=0.000125,
        step_halving_relative_position_velocity=ref_error), indent=2), encoding='utf-8')
    np.savetxt(output / 'dynamics_reference.txt', reference, fmt='%.17g')
    rows, direct = [], {}
    for dt in (0.016, 0.008, 0.004):
        for solver in solvers:
            for theta in ((0.3,) if solver.endswith('v1') else (0.1, 0.3, 0.7)):
                key = f'dynamics_{solver}_dt{dt}_theta{theta}'
                history, final = output / (key + '.csv'), output / (key + '.txt')
                run_case(solvers[solver], parameters(path, frames=round(0.256/dt), dt=dt, theta=theta, threads=4 if solver.endswith('v5') else 1),
                         output / 'logs' / key, ['--diagnostics', history, '--dump-state', final])
                state = np.loadtxt(final)
                h = np.genfromtxt(history, delimiter=',', names=True)
                if not np.isfinite(state).all() or not all(np.isfinite(h[name]).all() for name in h.dtype.names):
                    raise ValueError('Non-finite dynamics result')
                if solver.endswith('v1'):
                    direct[(solver.split('_')[0], dt)] = state
                baseline = direct[(solver.split('_')[0], dt)]
                pscale = np.linalg.norm(initial[:, 2:4], axis=1).sum()
                rows.append(dict(solver=solver, dt=dt, theta=theta,
                    position_error_rk4=float(np.linalg.norm(state[:, :2]-reference[:, :2])/norms[0]),
                    velocity_error_rk4=float(np.linalg.norm(state[:, 2:4]-reference[:, 2:4])/norms[1]),
                    position_difference_direct=float(np.linalg.norm(state[:, :2]-baseline[:, :2])/norms[0]),
                    velocity_difference_direct=float(np.linalg.norm(state[:, 2:4]-baseline[:, 2:4])/norms[1]),
                    max_momentum_drift=float(np.max(np.hypot(h['momentum_x']-h['momentum_x'][0],h['momentum_y']-h['momentum_y'][0]))/pscale),
                    max_angular_drift=float(np.max(np.abs(h['angular_momentum']-h['angular_momentum'][0]))/abs(h['angular_momentum'][0])),
                    max_energy_drift=float(np.max(np.abs(h['total_energy']-h['total_energy'][0]))/abs(h['total_energy'][0]))))
    table(output / 'dynamics.csv', rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cpp-dir', type=Path, default=ROOT / 'build')
    parser.add_argument('--rust-dir', type=Path, default=ROOT / 'nbody_rust/target/release')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--section', choices=['all', 'baseline', 'workload', 'scaling', 'accuracy-small', 'accuracy-large', 'dynamics'], default='all')
    args = parser.parse_args()
    output, solvers, suffix = setup(args)
    timings(args, output, solvers, suffix)
    if args.section in ('all', 'accuracy-small', 'accuracy-large'):
        accuracy(args, output, solvers, suffix)
    if args.section in ('all', 'dynamics'):
        dynamics(args, output, solvers)
    table(output / 'input_manifest.csv', [dict(file=p.name, sha256=sha256(p), bytes=p.stat().st_size) for p in sorted(output.glob('input_*.txt'))])
    print('Completed section:', args.section, flush=True)


if __name__ == '__main__':
    main()
