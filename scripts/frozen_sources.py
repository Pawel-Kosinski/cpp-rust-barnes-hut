"""Verify sealed computational sources while distinguishing package labels."""
import hashlib
import json
from pathlib import Path
import tomllib
import zipfile


def package_version_only(name, recorded, current):
    """Allow only the local Rust package version, never a dependency change."""
    name = name.replace('\\', '/')
    if name not in ('nbody_rust/Cargo.toml', 'nbody_rust/Cargo.lock'):
        return False
    try:
        old = tomllib.loads(recorded.decode('utf-8'))
        new = tomllib.loads(current.decode('utf-8'))
        if name.endswith('Cargo.toml'):
            if old['package']['name'] != 'nbody_rust' or new['package']['name'] != 'nbody_rust':
                return False
            old['package'].pop('version')
            new['package'].pop('version')
        else:
            for document in (old, new):
                local = [p for p in document['package'] if p['name'] == 'nbody_rust' and 'source' not in p]
                if len(local) != 1:
                    return False
                local[0].pop('version')
        return old == new
    except (ValueError, KeyError, UnicodeDecodeError):
        return False


def verify_frozen_sources(root, campaign):
    """Read-only validation; return explicitly permitted release-label changes."""
    root, campaign = Path(root), Path(campaign)
    manifest_bytes = (campaign / 'source_identity.json').read_bytes()
    identity = json.loads(manifest_bytes)
    archive_path = campaign / 'computational_source.zip'
    seal = json.loads((campaign / 'audit.json').read_text(encoding='utf-8'))
    with archive_path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != seal['computational_source_zip_sha256']:
        raise ValueError('Frozen computational archive SHA-256 changed')
    metadata_changes = []
    with zipfile.ZipFile(archive_path) as archive:
        if json.loads(archive.read('source_identity.json')) != identity:
            raise ValueError('Frozen source manifest differs from the campaign manifest')
        for name, expected in identity.items():
            if name.endswith('_binary'):
                continue
            relative = name.replace('\\', '/')
            if Path(relative).is_absolute() or '..' in Path(relative).parts:
                raise ValueError(f'Unsafe computational source path: {name}')
            recorded = archive.read(relative)
            if hashlib.sha256(recorded).hexdigest() != expected:
                raise ValueError(f'Frozen source bytes differ: {name}')
            current = (root / relative).read_bytes()
            if hashlib.sha256(current).hexdigest() == expected:
                continue
            if not package_version_only(relative, recorded, current):
                raise ValueError(f'Computational source changed: {name}')
            metadata_changes.append(relative)
    return metadata_changes
