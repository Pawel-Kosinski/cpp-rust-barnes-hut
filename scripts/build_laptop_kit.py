#!/usr/bin/env python3
"""Freeze a Windows laptop kit from the audited Ryzen campaign, without rebuilding."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import tomllib

from frozen_sources import verify_frozen_sources

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'scripts/laptop'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def make_plan(accuracy):
    solvers = [f'{lang}_v{v}' for lang in ('cpp', 'rust') for v in range(1, 6)]
    full, smoke = [], []
    rng = random.Random(20261009)

    def case(group, n, dist, seed, solver, threads, repeat=0, theta='0.3', frames=2, warmup=1):
        return dict(id=f'{group}_{n}_{dist}_{seed}_{solver}_t{threads}_theta{theta}_r{repeat}',
                    group=group, n=n, distribution=dist, seed=seed, solver=solver,
                    input=f'inputs/input_{dist}_{n}_{seed}.txt', threads=threads, repeat=repeat,
                    theta=theta, dt='0.016', frames=frames, warmup=warmup, timeout_seconds=1800)

    for solver in solvers:
        smoke.append(case('smoke', 1000, 'plummer', 1337, solver,
                          8 if solver.endswith('v5') else 1, frames=1, warmup=0))
    for dist in ('plummer', 'uniform', 'clustered'):
        for solver in solvers:
            for theta in (('0.3',) if solver.endswith('v1') else ('0.3', '0.7')):
                c = case('correctness', 10000, dist, 1337, solver,
                         8 if solver.endswith('v5') else 1, theta=theta, frames=1, warmup=0)
                c['reference'] = f'references/reference_10000_{dist}_1337.csv'
                c['expected_rms'] = 0.0 if solver.endswith('v1') else float(next(
                    r['rms_relative'] for r in accuracy if int(r['n']) == 10000 and
                    r['distribution'] == dist and int(r['seed']) == 1337 and
                    r['solver'] == solver and float(r['theta']) == float(theta)))
                full.append(c)
    for group in ('baseline', 'workload', 'scaling'):
        configurations = []
        if group == 'baseline':
            configurations = [(n, 'plummer', 1337, 3,
                [(s, 8 if s.endswith('v5') else 1) for s in solvers]) for n in (1000, 10000)]
        elif group == 'workload':
            configurations = [(100000, d, seed, 3,
                [(s, 8 if s.endswith('v5') else 1) for s in solvers if not s.endswith('v1')])
                for d in ('plummer', 'uniform', 'clustered') for seed in (1337, 42, 2026)]
        else:
            configurations = [(n, 'plummer', 1337, 5,
                [(f'{lang}_v5', t) for lang in ('cpp', 'rust') for t in (1, 2, 4, 8)] +
                [(f'{lang}_v4', 1) for lang in ('cpp', 'rust')]) for n in (100000, 1000000)]
        for n, dist, seed, repeats, cases in configurations:
            for repeat in range(repeats):
                order = cases.copy()
                rng.shuffle(order)
                for solver, threads in order:
                    full.append(case(group, n, dist, seed, solver, threads, repeat,
                                     frames=3 if group == 'scaling' else 2))
    assert len(full) == 430 and len(smoke) == 10
    assert len({c['id'] for c in full}) == len(full)
    assert max(c['threads'] for c in full) == 8
    return dict(order_seed=20261009, Full=full, Smoke=smoke)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, default=ROOT / 'results/manuscript/extended-2026-10-08')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--runtime-dir', type=Path, default=Path('C:/msys64/ucrt64/bin'))
    args = parser.parse_args()
    source, target = args.campaign.resolve(), args.output.resolve()
    if target.exists():
        raise SystemExit('Output already exists. Use a new directory; never overwrite a deployed kit.')
    version_labels = verify_frozen_sources(ROOT, source)
    audit = json.loads((source / 'audit.json').read_text())
    if audit.get('status') != 'passed':
        raise SystemExit('Reference campaign audit did not pass')
    target.mkdir(parents=True)

    def copy(src, relative):
        dst = target / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        return dst

    with (source / 'accuracy.csv').open(newline='') as stream:
        plan = make_plan(list(csv.DictReader(stream)))
    write_json(target / 'plan.json', plan)
    with (source / 'input_manifest.csv').open(newline='') as stream:
        input_hashes = {r['file']: r['sha256'] for r in csv.DictReader(stream)}
    for name in sorted({c['input'] for c in plan['Full'] + plan['Smoke']}):
        src = source / Path(name).name
        if digest(src) != input_hashes[src.name]:
            raise SystemExit(f'Input hash mismatch: {src}')
        copy(src, name)
    for name in sorted({c['reference'] for c in plan['Full'] if 'reference' in c}):
        copy(source / 'forces' / Path(name).name, name)

    logs = [json.loads(p.read_text()) for p in (source / 'logs').glob('*.json')]
    manifest = json.loads((source / 'manifest.json').read_text())
    binaries = {}
    for item in manifest['implementations']:
        src = Path(item['command'][0])
        expected = {r['executable_sha256'] for r in logs if r['implementation'] == item['id']}
        if expected != {digest(src)}:
            raise SystemExit(f'Binary does not match successful reference records: {src}')
        copy(src, f'bin/{item["id"]}.exe')
        binaries[item['id']] = dict(original_path=str(src), sha256=digest(src))

    env = {**os.environ, 'PATH': str(args.runtime_dir) + os.pathsep + os.environ.get('PATH', '')}
    dependencies = {}
    queue = list((target / 'bin').glob('*.exe'))
    while queue:
        path = queue.pop(0)
        output = subprocess.check_output([str(args.runtime_dir / 'objdump.exe'), '-p', path.name],
                                         cwd=path.parent, env=env, text=True)
        imports = re.findall(r'DLL Name:\s*(\S+)', output)
        if not imports:
            raise SystemExit(f'Could not inspect PE imports: {path}')
        dependencies[path.name] = imports
        for dll in imports:
            if dll.lower().startswith(('api-ms-', 'ext-ms-')) or (Path(os.environ['SystemRoot']) / 'System32' / dll).exists():
                continue
            if not (target / 'bin' / dll).exists():
                src = args.runtime_dir / dll
                if not src.is_file():
                    raise SystemExit(f'Unresolved runtime dependency: {dll}')
                queue.append(copy(src, 'bin/' + dll))
    for folder in ('gcc-libs', 'libwinpthread'):
        for src in (args.runtime_dir.parent / 'share/licenses' / folder).glob('*'):
            if src.is_file():
                copy(src, 'licenses/' + folder + '/' + src.name)
    packages = tomllib.loads((ROOT / 'nbody_rust/Cargo.lock').read_text())['package']
    for package in packages:
        if 'source' not in package:
            continue
        name = f'{package["name"]}-{package["version"]}'
        found = list((Path.home() / '.cargo/registry/src').glob('*/' + name))
        if len(found) != 1:
            raise SystemExit(f'Cannot locate dependency license for {name}')
        licenses = [p for p in found[0].iterdir() if p.is_file() and p.name.upper().startswith(('LICENSE', 'COPYING'))]
        if not licenses:
            raise SystemExit(f'No license found for {name}')
        for src in licenses:
            copy(src, f'licenses/rust-crates/{name}/{src.name}')
    rustroot = Path(subprocess.check_output([str(Path.home()/'.cargo/bin/rustc.exe'), '--print', 'sysroot'], text=True).strip())
    for name in ('COPYRIGHT', 'LICENSE-APACHE', 'LICENSE-MIT'):
        src = rustroot / 'share/doc/rust' / name
        if src.exists():
            copy(src, 'licenses/rust/' + name)
    copy(ROOT / 'LICENSE', 'licenses/BHBench-CR-LICENSE.txt')
    for name in ('source_identity.json', 'computational_source.zip', 'environment.json', 'audit.json', 'input_manifest.csv', 'accuracy.csv'):
        copy(source / name, 'provenance/ryzen-' + name)
    write_json(target / 'provenance/binary-identity.json', binaries)
    write_json(target / 'provenance/pe-imports.json', dependencies)
    write_json(target / 'provenance/kit-build.json', dict(base_commit=manifest.get('base_commit',
        json.loads((source/'environment.json').read_text())['base_commit']),
        campaign=str(source), computational_sources='ryzen-source_identity.json',
        release_package_version_labels=version_labels,
        note='Frozen experimental snapshot. Prebuilt EXEs match the Ryzen campaign byte-for-byte; release package labels do not change measured binary identities.'))
    for name in ('runner.ps1', 'runtime.cs'):
        copy(ENGINE / name, 'engine/' + name)
    copy(ENGINE / 'START_HERE.txt', 'START_HERE.txt')
    for name, mode in [('01_SPRAWDZ.cmd', 'Smoke'), ('02_START_LUB_WZNOW.cmd', 'Full'),
                       ('03_ZATRZYMAJ.cmd', 'Stop'), ('04_STATUS.cmd', 'Status')]:
        text = ('@echo off\nsetlocal\ntitle BHBench-CR laptop - '+mode+'\n'
                '"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoLogo -NoProfile '
                '-ExecutionPolicy Bypass -File "%~dp0engine\\runner.ps1" -Mode '+mode+'\n'
                'set "RESULT=%ERRORLEVEL%"\necho.\necho Exit code: %RESULT% (0=OK, 2=error, 3=paused)\n'
                'pause\nexit /b %RESULT%\n')
        (target / name).write_bytes(text.replace('\n', '\r\n').encode('ascii'))
    files = [dict(path=p.relative_to(target).as_posix(), sha256=digest(p), bytes=p.stat().st_size)
             for p in sorted(target.rglob('*')) if p.is_file()]
    write_json(target / 'kit-manifest.json', dict(schema=1, kit='BHBench-CR-laptop-R1-2026-10-09', runner_revision='profile-guard-1',
        target_cpu='Intel Core i7-11370H', full_processes=430, smoke_processes=10, files=files))
    (target / 'SHA256SUMS.txt').write_text(''.join(f'{r["sha256"]}  {r["path"]}\n' for r in files) +
        f'{digest(target / "kit-manifest.json")}  kit-manifest.json\n', encoding='ascii')
    print(json.dumps(dict(output=str(target), files=len(files), bytes=sum(r['bytes'] for r in files),
                         dlls=list(dependencies), full_cases=len(plan['Full'])), indent=2))


if __name__ == '__main__':
    main()
