#!/usr/bin/env python3
"""Check a complete campaign and preserve its exact computational source bytes."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import zipfile

from extended_validation import force_metrics, ROOT
from run_suite import sha256
from frozen_sources import verify_frozen_sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data', type=Path)
    parser.add_argument('--report', type=Path, help='Write the new audit outside the frozen campaign')
    args = parser.parse_args()
    data = args.data.resolve()
    records = list((data / 'logs').glob('*.json'))
    assert len(records) == 766, ('Expected 741 campaign and 25 probe records', len(records))
    hashes = {}
    def cached_hash(path):
        path = Path(path).resolve()
        if path not in hashes:
            hashes[path] = sha256(path)
        return hashes[path]
    for path in records:
        r = json.loads(path.read_text(encoding='utf-8'))
        assert r['returncode'] == 0, path
        assert Path(r['parameters']['input']).resolve().is_relative_to(data)
        assert cached_hash(r['parameters']['input']) == r['input_sha256'], path
        assert cached_hash(r['command'][0]) == r['executable_sha256'], path
        for suffix in ('.stdout.log', '.stderr.log'):
            assert path.with_suffix(suffix).exists(), path
        keys = ('implementation', 'parameters', 'command', 'cwd', 'input_sha256', 'executable_sha256', 'artifact_sha256')
        identity = {k: r[k] for k in keys}
        if 'environment' in r:
            identity['environment'] = r['environment']
        assert hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest() == r['fingerprint'], path
    with (data / 'input_manifest.csv').open() as stream:
        inputs = list(csv.DictReader(stream))
    for r in inputs:
        path = data / r['file']
        assert path.resolve().parent == data
        assert cached_hash(path) == r['sha256']
        with path.open('rb') as stream:
            count = sum(chunk.count(b'\n') for chunk in iter(lambda: stream.read(1024*1024), b''))
        assert count == int(path.stem.split('_')[2]), path
    with (data / 'accuracy.csv').open() as stream:
        accuracy = list(csv.DictReader(stream))
    assert len(accuracy) == 232
    for row in accuracy:
        n, distribution, seed = row['n'], row['distribution'], row['seed']
        prefix = f'accuracy_{n}_{distribution}_{seed}_{row["solver"]}_theta{row["theta"]}'
        metrics = force_metrics(data / 'forces' / f'reference_{n}_{distribution}_{seed}.csv', data / 'forces' / (prefix+'.csv'))
        for key, value in metrics.items():
            assert abs(value-float(row[key])) < 1e-12, (prefix, key)
    identity = json.loads((data / 'source_identity.json').read_text())
    paths = [p for p in identity if not p.endswith('_binary')]
    metadata_changes = []
    if (data / 'computational_source.zip').exists():
        metadata_changes = verify_frozen_sources(ROOT, data)
    else:
        for relative in paths:
            assert cached_hash(ROOT / relative) == identity[relative], relative
        with zipfile.ZipFile(data / 'computational_source.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for relative in paths:
                archive.write(ROOT / relative, relative)
            archive.write(ROOT / 'LICENSE', 'LICENSE')
            archive.write(data / 'source_identity.json', 'source_identity.json')
    report = dict(status='passed', process_records=len(records), input_files=len(inputs),
                  force_comparisons=len(accuracy), source_files=len(paths),
                  checks=['successful return codes', 'input and executable SHA-256', 'cache fingerprints',
                          'stdout/stderr present', 'input row counts', 'force metrics recomputed',
                          'computational source identities'],
                  release_package_version_labels=metadata_changes,
                  computational_source_zip_sha256=sha256(data / 'computational_source.zip'))
    report_path = args.report or data / 'audit.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
