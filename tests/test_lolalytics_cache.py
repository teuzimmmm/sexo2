import json
import os
from pathlib import Path
import tempfile
import unittest

from lolalytics.cache import FileCache


class FileCacheTests(unittest.TestCase):
    def test_round_trip_envelope_and_atomic_files_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = FileCache(tmp, clock=lambda: 123.5)
            cache.put('url?mode=arena', b'payload')
            self.assertEqual(cache.get('url?mode=arena'), {'stored_at': 123.5, 'value': b'payload'})
            paths = list(Path(tmp).iterdir())
            self.assertEqual(len(paths), 1)
            self.assertTrue(paths[0].name.endswith('.json'))
            self.assertFalse(any(p.name.startswith('.lolalytics-') for p in paths))

    def test_corrupt_or_wrong_envelope_is_a_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = FileCache(tmp)
            path = cache._path('bad')
            path.write_text('{broken')
            self.assertIsNone(cache.get('bad'))
            path.write_text(json.dumps({'stored_at': 'wrong', 'value': '%%%'}))
            self.assertIsNone(cache.get('bad'))

    def test_oversized_envelope_is_rejected_and_unrelated_json_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = FileCache(tmp, max_bytes=8, max_entries=2)
            path = cache._path('huge')
            path.write_bytes(b'x' * (cache._max_envelope_bytes + 1))
            unrelated = Path(tmp) / 'metadata.json'
            unrelated.write_text('{}')
            self.assertIsNone(cache.get('huge'))
            cache.put('normal', b'ok')
            self.assertTrue(unrelated.exists())
            self.assertTrue(path.exists())

    def test_timestamp_must_be_finite_numeric_and_not_boolean(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = FileCache(tmp)
            path = cache._path('timestamp')
            for stamp in (True, float('nan'), float('inf'), '123'):
                path.write_text(json.dumps({'stored_at': stamp, 'value': 'eA=='}))
                self.assertIsNone(cache.get('timestamp'))

    def test_constructor_rejects_invalid_limits_and_ttl(self):
        with tempfile.TemporaryDirectory() as tmp:
            for kwargs in (
                {'max_bytes': 0}, {'max_bytes': float('inf')},
                {'max_entries': 0}, {'ttl': float('nan')}, {'ttl': float('inf')},
            ):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    FileCache(tmp, **kwargs)

    def test_entry_size_limit_and_lru_entry_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = FileCache(tmp, max_bytes=4, max_entries=2)
            cache.put('one', b'1111')
            cache.put('two', b'2222')
            cache.get('one')  # Touch one so two is the least recently used.
            cache.put('three', b'3333')
            self.assertIsNotNone(cache.get('one'))
            self.assertIsNone(cache.get('two'))
            self.assertEqual(cache.get('three')['value'], b'3333')
            with self.assertRaises(ValueError):
                cache.put('large', b'12345')

    @unittest.skipUnless(os.name == "posix", "POSIX permission bits are not enforced on Windows")
    def test_file_permissions_are_private_when_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = FileCache(tmp)
            cache.put('secret-key', b'data')
            path = cache._path('secret-key')
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(tmp).st_mode & 0o777, 0o700)


if __name__ == '__main__':
    unittest.main()
