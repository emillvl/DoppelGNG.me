import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from doppelgng.bootstrap import download, ensure_browser_runtime, spec_digest, verify_runtime


def make_runtime(root):
    spec = {'waterfox': {'version': 'fixture'}, 'geckodriver': {'version': 'fixture'}}
    (root / 'runtime-lock.json').write_text(json.dumps({'windows-x64': spec}))
    files = {}
    for name in ('waterfox/core/waterfox.exe', 'waterfox/core/application.ini', 'waterfox/core/xul.dll', 'waterfox/core/omni.ja', 'geckodriver.exe', 'licenses/MPL-2.0.txt'):
        path = root / '.tools' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fixture')
        files[name] = {'sha256': hashlib.sha256(b'fixture').hexdigest(), 'bytes': 7}
    receipt = {'schema': 1, 'spec_sha256': spec_digest(spec), 'waterfox_version': 'fixture', 'driver_version': 'fixture', 'files': files}
    (root / '.tools/runtime-manifest.json').write_text(json.dumps(receipt))
    return receipt


class RuntimeCacheTests(unittest.TestCase):
    def test_cached_runtime_needs_no_download_git_or_extractor(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = make_runtime(root)
            with patch('requests.Session.request', side_effect=AssertionError('Network forbidden')), patch('subprocess.run', side_effect=AssertionError('No extractor or Git')):
                self.assertEqual(ensure_browser_runtime(root, offline=True), expected)

    def test_missing_supporting_dll_is_an_integrity_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_runtime(root)
            (root / '.tools/waterfox/core/xul.dll').unlink()
            with self.assertRaisesRegex(RuntimeError, 'xul.dll'):
                verify_runtime(root)

    def test_changed_file_of_same_size_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_runtime(root)
            (root / '.tools/geckodriver.exe').write_bytes(b'changed')
            with self.assertRaisesRegex(RuntimeError, 'geckodriver.exe'):
                verify_runtime(root)

    def test_unrecorded_browser_files_are_not_silently_packaged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_runtime(root)
            (root / '.tools/waterfox/core/unexpected.dll').write_bytes(b'unknown')
            with self.assertRaisesRegex(RuntimeError, 'inventory differs'):
                verify_runtime(root)

    def test_offline_mode_never_falls_back_to_a_download(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch('requests.Session.request', side_effect=AssertionError('No network')):
                with self.assertRaisesRegex(RuntimeError, 'no download was attempted'):
                    ensure_browser_runtime(Path(temporary), offline=True)

    def test_verified_download_cache_is_reused(self):
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / 'runtime.bin'
            file.write_bytes(b'cached archive')
            expected = hashlib.sha256(file.read_bytes()).hexdigest()
            with patch('requests.Session.request', side_effect=AssertionError('No network')):
                download('https://example.test/runtime', file, 'sha256', expected, offline=True)
