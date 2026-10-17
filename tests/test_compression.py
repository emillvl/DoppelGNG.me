import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from doppelgng.bootstrap import ensure_browser_runtime, verify_runtime
from doppelgng.compression import compress_runtime
from test_runtime import make_runtime


class BrowserCompressionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        make_runtime(self.root)
        self.marker = self.root / '.tools/runtime-compression.json'
        self.measurement = {'logical_bytes': 28, 'physical_bytes': 28, 'files': 4}
        for target, arguments in [
            ('doppelgng.compression.platform.system', {'return_value': 'Windows'}),
            ('doppelgng.compression._filesystem', {'return_value': 'NTFS'}),
            ('doppelgng.compression._storage', {'side_effect': lambda files: dict(self.measurement)}),
        ]:
            patcher = patch(target, **arguments)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch('doppelgng.compression.subprocess.run', side_effect=self.compress)
        self.compact = patcher.start()
        self.addCleanup(patcher.stop)

    def compress(self, *args, **kwargs):
        self.measurement['physical_bytes'] = 14
        return subprocess.CompletedProcess(args, 0, b'', b'')

    def test_lzx_targets_only_verified_browser_files_and_is_reused(self):
        before = verify_runtime(self.root)
        first = compress_runtime(self.root)
        second = compress_runtime(self.root)
        self.assertEqual(first['status'], 'compressed')
        self.assertEqual(second['status'], 'reused')
        self.assertEqual(first['physical_bytes'], 14)
        self.assertEqual(verify_runtime(self.root), before)
        self.compact.assert_called_once()
        command = self.compact.call_args.args[0]
        self.assertEqual(command[1:6], ['/C', '/F', '/A', '/Q', '/EXE:LZX'])
        self.assertEqual(set(command[6:]), {str(self.root / '.tools' / name) for name in before['files'] if name.startswith('waterfox/core/')})

    def test_changed_storage_is_recompressed_even_with_intact_contents(self):
        compress_runtime(self.root)
        self.measurement['physical_bytes'] = 28
        self.assertEqual(compress_runtime(self.root)['status'], 'compressed')
        self.assertEqual(self.compact.call_count, 2)

    def test_corrupt_receipt_does_not_skip_compression(self):
        self.marker.write_text('{interrupted write')
        self.assertEqual(compress_runtime(self.root)['status'], 'compressed')
        self.assertEqual(json.loads(self.marker.read_text())['algorithm'], 'LZX')

    def test_corrupt_browser_fails_before_compression(self):
        (self.root / '.tools/waterfox/core/xul.dll').write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError, 'integrity failed'):
            compress_runtime(self.root)
        self.compact.assert_not_called()
        self.assertFalse(self.marker.exists())

    def test_non_ntfs_storage_keeps_the_verified_runtime(self):
        with patch('doppelgng.compression._filesystem', return_value='exFAT'):
            self.assertEqual(compress_runtime(self.root)['status'], 'skipped')
        verify_runtime(self.root)
        self.compact.assert_not_called()
        self.assertFalse(self.marker.exists())

    def test_compact_failure_cannot_record_a_success(self):
        self.compact.side_effect = None
        self.compact.return_value = subprocess.CompletedProcess([], 1, b'', b'access denied')
        with self.assertRaisesRegex(RuntimeError, 'LZX compression failed.*access denied'):
            compress_runtime(self.root)
        verify_runtime(self.root)
        self.assertFalse(self.marker.exists())

    def test_altered_contents_during_compression_are_rejected(self):
        def corrupt(*args, **kwargs):
            (self.root / '.tools/waterfox/core/xul.dll').write_bytes(b'changed')
            return subprocess.CompletedProcess([], 0, b'', b'')

        self.compact.side_effect = corrupt
        with self.assertRaisesRegex(RuntimeError, 'integrity failed'):
            compress_runtime(self.root)
        self.assertFalse(self.marker.exists())

    def test_setup_applies_compression_but_offline_check_is_read_only(self):
        before = verify_runtime(self.root)
        self.assertEqual(ensure_browser_runtime(self.root), before)
        self.assertTrue(self.marker.exists())
        self.compact.assert_called_once()
        self.compact.reset_mock()
        self.marker.unlink()
        with patch('doppelgng.bootstrap.compress_runtime', side_effect=AssertionError('Offline must not compress')):
            self.assertEqual(ensure_browser_runtime(self.root, offline=True), before)
        self.compact.assert_not_called()
        self.assertFalse(self.marker.exists())
