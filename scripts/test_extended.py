#!/usr/bin/env python3
"""Small, dependency-free tests for diagnostics, timing and external adapters."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

from run_suite import implementations, parse_metrics, run_case, sha256

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cpp-dir', type=Path, default=ROOT / 'build')
    parser.add_argument('--rust-dir', type=Path, default=ROOT / 'nbody_rust/target/release')
    parser.add_argument('--skip-external-build', action='store_true')
    args = parser.parse_args()
    suffix = '.exe' if os.name == 'nt' else ''
    names = ['direct', 'pointer_tree', 'vector_tree', 'threaded_tree', 'parallel_force']
    binaries = [args.cpp_dir / f'bh_cpp_v{i}{suffix}' for i in range(1, 6)]
    binaries += [args.rust_dir / f'bh_v{i}_{name}{suffix}' for i, name in enumerate(names, 1)]
    (ROOT / 'tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bhbench-test-', dir=ROOT / 'tmp') as temporary:
        folder = Path(temporary)
        assert folder.resolve().is_relative_to((ROOT / 'tmp').resolve())
        initial = folder / 'two bodies.txt'
        initial.write_text('-1 0 0 -1 5\n1 0 0 1 5\n', encoding='utf-8')
        for binary in binaries:
            binary = binary.resolve()
            errors = []
            for dt in (0.016, 0.008, 0.004):
                history, final = folder / 'history.csv', folder / 'state.txt'
                command = [str(binary), '--input', str(initial), '--frames', str(round(1.024/dt)),
                           '--threads', '2', '--dt', str(dt), '--diagnostics', str(history),
                           '--dump-state', str(final), '--dump-forces', str(folder / 'forces.csv'),
                           '--force-samples', '1', '--memory-report', str(folder / 'memory.csv')]
                process = subprocess.run(command, check=True, capture_output=True, text=True)
                metrics = parse_metrics(process.stdout, round(1.024/dt))
                assert abs(metrics['kernel_ms'] + metrics['update_ms'] - metrics['force_update_ms']) < 0.001
                with history.open() as stream:
                    rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(stream)]
                assert len(rows) == round(1.024/dt) + 1
                assert abs(rows[0]['potential'] + 25*math.atan(0.5)) < 1e-12
                assert max(abs(r['angular_momentum']-10) for r in rows) < 5e-5
                assert max(math.hypot(r['momentum_x'], r['momentum_y']) for r in rows) < 1e-6
                assert all(math.isfinite(v) for r in rows for v in r.values())
                states = [[float(x) for x in line.split()] for line in final.read_text().splitlines()]
                errors.append(math.hypot(states[1][0]-math.cos(1.024), states[1][1]-math.sin(1.024)))
                assert len((folder / 'forces.csv').read_text().splitlines()) == 2
            assert errors[0] / errors[1] > 1.8 and errors[1] / errors[2] > 1.8, (binary, errors)
            for flag, value in (('--dt', '0'), ('--dt', 'nan'), ('--theta', 'nan'), ('--diagnostic-stride', '0')):
                result = subprocess.run([str(binary), flag, value], capture_output=True)
                assert result.returncode != 0, (binary, flag, value)
            print('PASS', binary.name, 'two-body invariants, first-order refinement, timing, output, CLI', flush=True)

        if not args.skip_external_build:
            build = folder / 'external build'
            executable = build / ('multifile_adapter' + suffix)
            if os.name == 'nt':
                generator = ['-G', 'Ninja']
            else:
                generator = []
            manifest = {'implementations': [{'id': 'multifile', 'cwd': str(folder),
                'build': [['cmake', '-S', str(ROOT / 'tests/external_multifile'), '-B', str(build), '-DCMAKE_BUILD_TYPE=Release', *generator],
                          ['cmake', '--build', str(build), '--config', 'Release']],
                'command': [os.path.relpath(executable, folder), '--input', '{input}', '--frames', '{frames}', '--warmup-frames', '{warmup}']} ]}
            path = folder / 'manifest.json'
            path.write_text(json.dumps(manifest), encoding='utf-8')
            solver = implementations(path, build=True)[0]
            params = dict(input=str(initial), frames=2, warmup=1)
            first = run_case(solver, params, folder / 'run.theta0.3')
            cached = run_case(solver, params, folder / 'run.theta0.3')
            assert first == cached
            assert (folder / 'run.theta0.3.json').is_file()
            other = run_case(solver, params, folder / 'run.theta0.7')
            assert (folder / 'run.theta0.7.json').is_file()
            initial.write_text('-1 0 0 -1 6\n1 0 0 1 6\n', encoding='utf-8')
            try:
                run_case(solver, params, folder / 'run.theta0.3')
            except RuntimeError:
                pass
            else:
                raise AssertionError('Stale input was accepted')
            assert other['input_sha256'] != sha256(initial)
            print('PASS multi-file build, path spaces, manifest, cached resume, stale-input rejection')


if __name__ == '__main__':
    main()
