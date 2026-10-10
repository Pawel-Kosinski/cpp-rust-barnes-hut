"""The package-label exception must not permit solver or dependency edits."""
import unittest

from frozen_sources import package_version_only


class VersionLabelTests(unittest.TestCase):
    manifest = b'[package]\nname="nbody_rust"\nversion="1.1.5"\nedition="2024"\n[dependencies]\nrayon="1.11.0"\n'
    lock = b'version=4\n[[package]]\nname="nbody_rust"\nversion="1.1.5"\n[[package]]\nname="rayon"\nversion="1.11.0"\nsource="registry"\nchecksum="abc"\n'

    def test_local_versions_allowed(self):
        for name, old in [('Cargo.toml', self.manifest), ('Cargo.lock', self.lock)]:
            self.assertTrue(package_version_only('nbody_rust/' + name, old, old.replace(b'1.1.5', b'1.2.0')))

    def test_dependency_versions_rejected(self):
        for name, old in [('Cargo.toml', self.manifest), ('Cargo.lock', self.lock)]:
            self.assertFalse(package_version_only('nbody_rust/' + name, old, old.replace(b'1.11.0', b'1.12.0')))

    def test_edition_rejected(self):
        self.assertFalse(package_version_only('nbody_rust/Cargo.toml', self.manifest, self.manifest.replace(b'2024', b'2021')))

    def test_locked_checksum_rejected(self):
        self.assertFalse(package_version_only('nbody_rust/Cargo.lock', self.lock, self.lock.replace(b'abc', b'def')))

    def test_other_sources_never_exempt(self):
        self.assertFalse(package_version_only('cpp/example.cpp', self.manifest, self.manifest))

    def test_invalid_manifest_rejected(self):
        self.assertFalse(package_version_only('nbody_rust/Cargo.toml', self.manifest, b'not TOML'))


if __name__ == '__main__':
    unittest.main()
