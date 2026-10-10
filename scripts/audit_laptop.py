#!/usr/bin/env python3
"""Independently audit a completed laptop campaign without changing its raw files."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath
import platform

import numpy as np

from run_suite import parse_metrics


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def require(condition, context):
    if not condition:
        raise ValueError(context)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def within(root, relative):
    path = (root / Path(relative.replace('\\', '/'))).resolve()
    require(path.is_relative_to(root.resolve()), f'Unsafe path: {relative}')
    return path


def close(a, b, context):
    require(math.isfinite(float(a)) and math.isclose(float(a), float(b), rel_tol=1e-11, abs_tol=1e-12),
            f'Metric mismatch: {context}: {a} != {b}')


def force_array(path):
    values = np.loadtxt(path, delimiter=',', skiprows=1, ndmin=2)
    require(values.shape[1] == 3 and np.isfinite(values).all(), f'Invalid force dump: {path}')
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kit', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--ryzen', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    kit, run, ryzen = [p.resolve() for p in (args.kit, args.run, args.ryzen)]
    manifest = read_json(kit / 'kit-manifest.json')
    hashes = {}
    def cached(path):
        if path not in hashes:
            hashes[path] = sha(path)
        return hashes[path]

    for item in manifest['files']:
        path = within(kit, item['path'])
        require(path.stat().st_size == item['bytes'] and cached(path) == item['sha256'],
                f'Kit identity mismatch: {item["path"]}')
    plan = read_json(run / 'plan.json')
    require(plan == read_json(kit / 'plan.json'), 'Recorded plan differs from kit')
    cases = plan['Full']
    by_id = {c['id']: c for c in cases}
    require(len(cases) == len(by_id) == 430, 'Expected 430 unique full-campaign cases')
    expected_groups = dict(correctness=54, baseline=60, workload=216, scaling=100)
    require(Counter(c['group'] for c in cases) == expected_groups, 'Unexpected group counts')
    records = {p.stem: read_json(p) for p in (run / 'records').glob('*.json')}
    require(records.keys() == by_id.keys(), 'Missing/extra process records')
    env = read_json(run / 'environment.json')
    require(env['identity']['kit_manifest_sha256'] == cached(kit / 'kit-manifest.json'), 'Wrong kit')
    require(env['identity']['power_settings_sha256'] == cached(run / 'powercfg.txt'), 'Power settings changed')
    status = read_json(run / 'status.json')
    require(status['state'] == 'complete' and status['completed'] == 430 and status['mirror_pending_files'] == 0,
            'Run is not fully synchronized')
    binaries = read_json(kit / 'provenance/binary-identity.json')
    ryzen_binaries = {}
    for path in (ryzen / 'logs').glob('*.json'):
        record = read_json(path)
        solver = record['implementation']
        if solver in binaries:
            ryzen_binaries.setdefault(solver, set()).add(record['executable_sha256'])
    for solver, identity in binaries.items():
        require(ryzen_binaries[solver] == {identity['sha256']} == {cached(kit / 'bin' / (solver + '.exe'))},
                f'Cross-host binary mismatch: {solver}')
    source_identity = read_json(ryzen / 'source_identity.json')
    require(source_identity == read_json(kit / 'provenance/ryzen-source_identity.json'), 'Source identities differ')
    ryzen_inputs = {r['file']: r for r in read_csv(ryzen / 'input_manifest.csv')}
    for path in (kit / 'inputs').glob('*.txt'):
        require(cached(path) == ryzen_inputs[path.name]['sha256'], f'Cross-host input mismatch: {path.name}')
    for path in (kit / 'references').glob('*.csv'):
        require(cached(path) == cached(ryzen / 'forces' / path.name), f'Reference mismatch: {path.name}')

    timing_rows = read_csv(run / 'timings.csv')
    accuracy_rows = read_csv(run / 'accuracy.csv')
    timing = {r['case_id']: r for r in timing_rows}
    accuracy = {r['case_id']: r for r in accuracy_rows}
    require(len(timing) == len(timing_rows) == 376 and len(accuracy) == len(accuracy_rows) == 54,
            'Missing/duplicate summary rows')
    require(timing.keys() == {c['id'] for c in cases if c['group'] != 'correctness'}, 'Timing case mismatch')
    require(accuracy.keys() == {c['id'] for c in cases if c['group'] == 'correctness'}, 'Force case mismatch')
    force_comparisons, bit_identical, byte_identical, artifact_count = [], 0, 0, 0
    for case in cases:
        case_id = case['id']
        record = records[case_id]
        require(record['case'] == case and record['state'] == 'success' and record['returncode'] == 0
                and record['error'] is None, f'Failed or altered case: {case_id}')
        require(record['environment_fingerprint'] == env['fingerprint'], f'Mixed environments: {case_id}')
        require(record['input_sha256'] == cached(within(kit, case['input'])), f'Input changed: {case_id}')
        require(record['executable_sha256'] == binaries[case['solver']]['sha256'], f'Executable changed: {case_id}')
        require(PureWindowsPath(record['command'][0]).name == case['solver'] + '.exe', f'Wrong command: {case_id}')
        options = dict(zip(record['command'][1::2], record['command'][2::2]))
        for key, value in [('input', case['input'].replace('/', '\\')), ('frames', case['frames']),
                           ('warmup-frames', case['warmup']), ('theta', case['theta']),
                           ('threads', case['threads']), ('dt', case['dt'])]:
            require(options['--' + key] == str(value), f'Command mismatch: {case_id}/{key}')
        artifacts = {}
        for relative, digest in record['artifacts'].items():
            path = within(run, relative)
            require(cached(path) == digest, f'Log changed: {relative}')
            artifacts[path.name] = path
            artifact_count += 1
        require(artifacts['stderr.log'].stat().st_size == 0, f'Nonempty stderr: {case_id}')
        require(read_json(artifacts['stdout.log'].parent / 'process.json') == record, f'Attempt mismatch: {case_id}')
        measured = parse_metrics(artifacts['stdout.log'].read_text(encoding='utf-8-sig'), case['frames'])
        require(len(measured) == 6, f'Incomplete phase timings: {case_id}')
        # Rust's combined field is rounded to four decimal places in stdout.
        require(math.isclose(measured['kernel_ms'] + measured['update_ms'], measured['force_update_ms'],
                             rel_tol=1e-9, abs_tol=0.00015), f'Force/update sum mismatch: {case_id}')
        for key, value in measured.items():
            close(value, record['metrics'][key], case_id + '/' + key)
            if case['group'] != 'correctness':
                close(value, timing[case_id][key], case_id + '/CSV/' + key)
        row = accuracy[case_id] if case['group'] == 'correctness' else timing[case_id]
        for key in ('n', 'distribution', 'seed', 'solver', 'threads'):
            require(str(case[key]) == row[key], f'CSV identity mismatch: {case_id}/{key}')
        if case['group'] != 'correctness':
            for key in ('group', 'repeat'):
                require(str(case[key]) == row[key], f'CSV identity mismatch: {case_id}/{key}')
            continue
        close(case['theta'], row['theta'], case_id + '/theta')
        reference = force_array(within(kit, case['reference']))
        actual = force_array(artifacts['forces.csv'])
        require(np.array_equal(reference[:, 0], actual[:, 0]) and len(actual) == case['n'], 'Target mismatch')
        ref, acc = reference[:, 1:], actual[:, 1:]
        norms = np.linalg.norm(ref, axis=1)
        require((norms > 0).all(), 'Zero reference norm')
        local_error = np.linalg.norm(acc - ref, axis=1) / norms
        metrics = dict(samples=len(acc), rms_relative=float(np.linalg.norm(acc-ref) / np.linalg.norm(ref)),
                       p95_particle_relative=float(np.quantile(local_error, .95, method='linear')),
                       max_particle_relative=float(np.max(local_error)))
        for key, value in metrics.items():
            close(value, record['accuracy'][key], case_id + '/record/' + key)
            close(value, row[key], case_id + '/CSV/' + key)
        if case['solver'].endswith('_v1'):
            require(metrics['rms_relative'] <= 1e-4, f'Direct reference failure: {case_id}')
        else:
            name = f"accuracy_{case['n']}_{case['distribution']}_{case['seed']}_{case['solver']}_theta{case['theta']}.csv"
            previous = ryzen / 'forces' / name
            identical = np.array_equal(force_array(previous), actual)
            bit_identical += int(identical)
            byte_identical += int(cached(previous) == cached(artifacts['forces.csv']))
            close(metrics['rms_relative'], case['expected_rms'], case_id + '/Ryzen RMS')
        force_comparisons.append(dict(case_id=case_id, **metrics))

    report = dict(status='passed', process_records=len(records), groups=expected_groups, kit_files=len(manifest['files']),
                  timing_rows=376, force_comparisons=54, artifacts_verified=artifact_count,
                  matched_binaries=len(binaries), matched_inputs=len(list((kit / 'inputs').glob('*.txt'))),
                  matched_references=3, cross_host_approximate_force_comparisons=48,
                  identical_parsed_force_arrays=bit_identical, byte_identical_force_files=byte_identical,
                  kit_manifest_sha256=cached(kit / 'kit-manifest.json'), environment_fingerprint=env['fingerprint'],
                  python=platform.python_version(), numpy=np.__version__,
                  direct_rms_range=[min(r['rms_relative'] for r in force_comparisons if '_v1_' in r['case_id']),
                                    max(r['rms_relative'] for r in force_comparisons if '_v1_' in r['case_id'])],
                  checks=['exact planned case coverage', 'process/attempt equality', 'recorded CLI parameters',
                          'kit SHA-256 and sizes', 'input/binary/reference identities across hosts',
                          'raw artifact SHA-256', 'empty stderr and zero exit codes', 'phase timings reparsed',
                          'force metrics recomputed with NumPy', 'force arrays compared across hosts',
                          'CSV identities and values checked'],
                  note='PowerShell JSON fingerprints are verified separately by audit_laptop_fingerprints.ps1.')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (args.output / 'force_metrics_recomputed.json').write_text(json.dumps(force_comparisons, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
