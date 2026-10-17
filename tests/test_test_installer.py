"""Offline tests for selective packaging; no real personal files or keys."""
import contextlib
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts.build_test_installer import main, write_identity
from sexo2.install.identity import MANIFEST, display_version, test_identity
from sexo2.install.packaging import (
    REQUIRED_NATIVE, member_path, restore_native, snapshot_source, validate_version,
)
from sexo2.update.client import check_release, configuration


def synthetic_pe():
    """Only the header needed by packaging checks; never a runnable executable."""
    body = bytearray(128)
    body[:2] = b'MZ'
    body[60:64] = (64).to_bytes(4, 'little')
    body[64:68] = b'PE\0\0'
    return body


class TestIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_missing_identity_preserves_normal_build_behavior(self):
        self.assertIsNone(test_identity(self.root))
        with patch('sexo2.install.identity.test_identity', return_value=None):
            self.assertEqual(display_version('existing'), 'existing')

    def test_written_identity_is_valid_and_only_uses_public_metadata(self):
        record = write_identity(self.root, '2.0.0.1', 'a' * 40)
        self.assertEqual(test_identity(self.root), record)
        self.assertEqual(set(record), {'schema', 'app', 'channel', 'version', 'sourceCommit'})
        with patch('sexo2.install.identity.test_identity', return_value=record):
            self.assertEqual(display_version('existing'), '2.0.0.1 (teste)')

    def test_invalid_identity_cannot_be_treated_as_a_stable_installation(self):
        for value in ['{broken', '[]', json.dumps({'schema': 1, 'app': 'OTHER'})]:
            with self.subTest(value=value):
                (self.root / MANIFEST).write_text(value)
                with self.assertRaises(ValueError): test_identity(self.root)
        write_identity(self.root, '2.0.0.1', 'a' * 40)
        data = test_identity(self.root)
        data['version'] = 1
        (self.root / MANIFEST).write_text(json.dumps(data))
        with self.assertRaises(ValueError): test_identity(self.root)

    def test_test_channel_never_reads_tokens_or_contacts_stable_releases(self):
        identity = write_identity(self.root, '2.0.0.1', 'a' * 40)
        with patch('sexo2.install.identity.test_identity', return_value=identity), \
             patch('sexo2.update.client.requests.get') as get, \
             patch('sexo2.update.client.assets_root', side_effect=AssertionError('Token access')):
            self.assertEqual(configuration(), ('', ''))
            result = check_release('example/example', 'SYNTHETIC_TEST_TOKEN')
        get.assert_not_called()
        self.assertFalse(result['available'])
        self.assertEqual(result['channel'], 'test')
        self.assertNotIn('SYNTHETIC_TEST_TOKEN', str(result))

    def test_only_bounded_test_versions_are_allowed(self):
        self.assertEqual(validate_version('2.0.0.65535'), '2.0.0.65535')
        for value in ['1.6.4', '2.0.0.0', '2.0.0.65536', '2.0.0.1/../x', '2.0.0.1"', 1, None]:
            with self.subTest(value=value), self.assertRaises(ValueError): validate_version(value)


class TestPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / 'baseline.zip'
        self.stage = self.root / 'stage'

    def baseline(self, extra=()):
        with zipfile.ZipFile(self.base, 'w') as archive:
            for name in sorted(REQUIRED_NATIVE):
                archive.writestr('_internal/' + name, synthetic_pe())
            for name, body in extra:
                archive.writestr(name, body)

    def test_only_native_allowlist_is_restored_and_source_plugins_survive(self):
        self.baseline([
            ('_internal/assets/update-access.json', 'SYNTHETIC_PRIVATE'),
            ('_internal/Pengu Loader/config', 'SYNTHETIC_PRIVATE'),
            ('_internal/Pengu Loader/datastore', 'SYNTHETIC_PRIVATE'),
            ('_internal/Pengu Loader/plugins/SEXO2-Builds/index.js', 'old plugin'),
        ])
        plugin = self.stage / 'Pengu Loader/plugins/SEXO2-Builds/index.js'
        plugin.parent.mkdir(parents=True)
        plugin.write_text('current source')
        report = restore_native(self.base, self.stage)
        self.assertEqual({r['file'] for r in report}, REQUIRED_NATIVE)
        self.assertEqual(plugin.read_text(), 'current source')
        for path in ['assets/update-access.json', 'Pengu Loader/config', 'Pengu Loader/datastore']:
            self.assertFalse((self.stage / path).exists())
        self.assertNotIn('SYNTHETIC_PRIVATE', json.dumps(report))

    def test_directory_baseline_is_read_only_and_selective(self):
        original = self.root / 'existing'
        for name in REQUIRED_NATIVE:
            source = original / '_internal' / name
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(synthetic_pe())
        private = original / 'config.ini'
        private.write_text('SYNTHETIC_PRIVATE')
        restore_native(original, self.stage)
        self.assertEqual(private.read_text(), 'SYNTHETIC_PRIVATE')
        self.assertFalse((self.stage / 'config.ini').exists())

    def test_zip_traversal_absolute_paths_and_symlinks_are_rejected(self):
        for name in ['../escape.dll', '/escape.dll', 'C:/escape.dll', '_internal\\escape.dll']:
            with self.subTest(name=name):
                self.baseline([(name, synthetic_pe())])
                with self.assertRaises(ValueError): restore_native(self.base, self.stage)
        self.baseline()
        with zipfile.ZipFile(self.base, 'a') as archive:
            link = zipfile.ZipInfo('_internal/Pengu Loader/link')
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(link, '../other')
        with self.assertRaises(ValueError): restore_native(self.base, self.stage)
        self.assertFalse((self.root / 'escape.dll').exists())

    def test_duplicate_native_targets_are_rejected_case_insensitively(self):
        self.baseline([('_internal/Pengu Loader/CORE.dll', synthetic_pe())])
        with self.assertRaises(ValueError): restore_native(self.base, self.stage)

    def test_missing_invalid_and_oversized_native_payloads_fail(self):
        with zipfile.ZipFile(self.base, 'w') as archive:
            archive.writestr('_internal/Pengu Loader/core.dll', synthetic_pe())
        with self.assertRaisesRegex(ValueError, 'incompleta'): restore_native(self.base, self.stage)
        self.baseline([('_internal/Pengu Loader/extra.dll', b'not a PE file')])
        with self.assertRaises(ValueError): restore_native(self.base, self.stage)
        self.baseline()
        with patch('sexo2.install.packaging.MAX_NATIVE_FILE', 64):
            with self.assertRaises(ValueError): restore_native(self.base, self.stage)

    def test_snapshot_excludes_credentials_datastore_and_logs_before_copying(self):
        source = self.root / 'source'
        files = ['main.py', 'assets/icon.png', 'assets/update-access.json', 'config.ini',
                 'release-secrets/signing.key', 'Pengu Loader/datastore', 'run.log']
        for name in files:
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('SYNTHETIC_PRIVATE' if name not in files[:2] else 'public source')
        snapshot_source(source, self.stage, files)
        self.assertEqual(sorted(str(p.relative_to(self.stage)) for p in self.stage.rglob('*') if p.is_file()),
                         sorted(['main.py', str(Path('assets/icon.png'))]))

    def test_source_links_are_rejected(self):
        source = self.root / 'source'
        source.mkdir()
        target = self.root / 'outside.py'
        target.write_text('outside')
        try:
            (source / 'main.py').symlink_to(target)
        except OSError:
            self.skipTest('Symlink creation unavailable on this Windows account')
        with self.assertRaises(ValueError): snapshot_source(source, self.stage, ['main.py'])

    def test_unsafe_source_members_are_rejected(self):
        for value in ['../private', '/absolute', 'C:/absolute', 'x/./y', 'x//y']:
            with self.subTest(value=value), self.assertRaises(ValueError): member_path(value)

    def test_installer_has_distinct_identity_and_no_legacy_cleanup_or_hook_removal(self):
        text = (Path(__file__).resolve().parents[1] / 'installer-sexo2.iss').read_text(encoding='utf-8-sig')
        self.assertIn('Programs\\SEXO2-2.0-Teste', text)
        self.assertNotIn('B876AA51-DB38-448E-BD13-716F1C9DE750', text)
        self.assertIn('UsePreviousAppDir=no', text)
        self.assertNotIn('[InstallDelete]', text)
        self.assertNotIn('[UninstallRun]', text)
        self.assertNotIn('deltree', text.lower())

    def test_linux_cannot_report_a_windows_installer_as_built(self):
        error = io.StringIO()
        with patch('scripts.build_test_installer.sys.platform', 'linux'), contextlib.redirect_stderr(error):
            result = main(['--base', str(self.base)])
        self.assertEqual(result, 1)
        self.assertIn('exige Windows', error.getvalue())
        self.assertFalse(self.stage.exists())


if __name__ == '__main__':
    unittest.main()
