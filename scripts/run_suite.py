#!/usr/bin/env python3
"""Run independently built implementations through a JSON command manifest.

Commands are argument arrays, never shell strings. The runner does not assume a
language, a build system, or a number of source files. See docs/external_solvers.md.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import time


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def implementations(path, build=False):
    path = Path(path).resolve()
    manifest = json.loads(path.read_text(encoding='utf-8'))
    result = []
    for item in manifest['implementations']:
        item = dict(item)
        if not re.fullmatch(r'[A-Za-z0-9_-]+', item['id']):
            raise ValueError('Implementation id must be a safe filename component')
        item['cwd'] = str((path.parent / item.get('cwd', '.')).resolve())
        for command in [item['command'], *item.get('build', [])]:
            if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
                raise ValueError('Commands must be non-empty JSON string arrays')
        if build:
            for command in item.get('build', []):
                subprocess.run(command, cwd=item['cwd'], check=True)
        executable = Path(item['cwd']) / item['command'][0]
        if not executable.is_file():
            executable = Path(shutil.which(item['command'][0]) or item['command'][0])
        item['executable_sha256'] = sha256(executable)
        # Windows resolves a relative executable before applying the child cwd.
        item['command'] = [str(executable.resolve()), *item['command'][1:]]
        item['artifact_sha256'] = {p: sha256(Path(item['cwd']) / p) for p in item.get('artifacts', [])}
        result.append(item)
    if len({x['id'] for x in result}) != len(result):
        raise ValueError('Duplicate implementation ids')
    return result


def parse_metrics(output, frames):
    labels = {'tree_ms': 'Tree construction time', 'force_update_ms': 'Force/update time',
              'cleanup_ms': 'Cleanup time', 'total_ms': 'Total measured time',
              'kernel_ms': 'Force kernel time', 'update_ms': 'State update time'}
    values = {}
    for key, label in labels.items():
        match = re.search(r'^' + re.escape(label) + r':\s*([0-9.eE+-]+)\s+ms', output, re.M)
        if match:
            value = float(match.group(1))
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'Invalid timing: {label}')
            values[key] = value / frames if key == 'total_ms' else value
        elif key not in ('kernel_ms', 'update_ms'):
            raise ValueError(f'Missing timing: {label}')
    if not math.isclose(values['total_ms'], sum(values[x] for x in ('tree_ms', 'force_update_ms', 'cleanup_ms')), abs_tol=0.01, rel_tol=1e-4):
        raise ValueError('Reported total and phase times disagree')
    return values


def run_case(implementation, parameters, destination, extra=(), timing=True):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    def result_file(suffix):
        return destination.parent / (destination.name + suffix)
    parameters = dict(parameters)
    parameters['input'] = str(Path(parameters['input']).resolve())
    command = [word.format_map(parameters) for word in implementation['command']] + list(map(str, extra))
    record = {'implementation': implementation['id'], 'parameters': parameters,
              'command': command, 'cwd': implementation['cwd'],
              'input_sha256': sha256(parameters['input']),
              'executable_sha256': implementation['executable_sha256'],
              'artifact_sha256': implementation['artifact_sha256']}
    if 'environment' in implementation:
        record['environment'] = implementation['environment']
    fingerprint = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
    target = result_file('.json')
    if target.exists():
        previous = json.loads(target.read_text(encoding='utf-8'))
        if previous.get('fingerprint') != fingerprint:
            raise RuntimeError(f'Refusing to mix changed inputs/binaries with cached results: {target}')
        if previous.get('returncode') == 0 and result_file('.stdout.log').is_file():
            return previous
    started = time.perf_counter()
    process = subprocess.run(command, cwd=implementation['cwd'], text=True, capture_output=True, timeout=7200,
                             env={**os.environ, **implementation.get('environment', {})})
    record.update(fingerprint=fingerprint, returncode=process.returncode,
                  wall_seconds=time.perf_counter() - started, completed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    result_file('.stdout.log').write_text(process.stdout, encoding='utf-8')
    result_file('.stderr.log').write_text(process.stderr, encoding='utf-8')
    if process.returncode:
        target.write_text(json.dumps(record, indent=2), encoding='utf-8')
        raise RuntimeError(f'Failed command, see {result_file(".stderr.log")}')
    if timing:
        record['metrics'] = parse_metrics(process.stdout, int(parameters['frames']))
    target.write_text(json.dumps(record, indent=2), encoding='utf-8')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--frames', type=int, default=5)
    parser.add_argument('--warmup', type=int, default=1)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--theta', type=float, default=0.3)
    parser.add_argument('--dt', type=float, default=0.016)
    parser.add_argument('--order-seed', type=int, default=20261008)
    args = parser.parse_args()
    if args.frames < 1 or args.repeats < 1 or args.warmup < 0 or args.threads < 1:
        parser.error('Invalid repetition, frame, warmup, or thread count')
    solvers = implementations(args.manifest, args.build)
    parameters = {k: getattr(args, k) for k in ('input', 'frames', 'warmup', 'threads', 'theta', 'dt')}
    rng = random.Random(args.order_seed)
    rows = []
    for repeat in range(args.repeats):
        order = solvers.copy()
        rng.shuffle(order)
        for implementation in order:
            record = run_case(implementation, parameters, args.output / f'r{repeat}-{implementation["id"]}')
            rows.append({'repeat': repeat, 'implementation': implementation['id'], **record['metrics']})
    with (args.output / 'timings.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
