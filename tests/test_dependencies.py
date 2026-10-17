import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from doppelgng.dependencies import default_crawler, ensure_crawler


class CrawlerProvisioningTests(unittest.TestCase):
    def make_cached(self, root):
        directory = root / '.tools/webcrawler'
        directory.mkdir(parents=True)
        content = b'preserved upstream source\n'
        (directory / 'webcrawler.py').write_bytes(content)
        spec = {'repository': 'https://github.com/emillvl/webcrawler.git', 'revision': 'a' * 40, 'files': {'webcrawler.py': hashlib.sha256(content).hexdigest()}}
        (root / 'runtime-lock.json').write_text(json.dumps({'crawler': spec}))
        return directory

    def test_verified_cached_files_work_without_git_or_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = self.make_cached(root)
            with patch('doppelgng.dependencies._git', side_effect=AssertionError('No repeated clone')):
                self.assertEqual(ensure_crawler(root), directory)
                before = (directory / 'upstream.json').stat().st_mtime_ns
                self.assertEqual(ensure_crawler(root), directory)
                self.assertEqual((directory / 'upstream.json').stat().st_mtime_ns, before)

    def test_modified_dependency_is_preserved_and_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = self.make_cached(root)
            (directory / 'webcrawler.py').write_text('local changes')
            with self.assertRaisesRegex(RuntimeError, 'differ from the pinned revision'):
                ensure_crawler(root)
            self.assertEqual((directory / 'webcrawler.py').read_text(), 'local changes')

    def test_packaged_default_is_relative_to_the_project(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(default_crawler(Path('product')).parts[-3:], ('product', '.tools', 'webcrawler'))

    def test_offline_package_with_missing_crawler_does_not_clone(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'runtime-lock.json').write_text(json.dumps({'crawler': {'repository': 'unused', 'revision': 'a' * 40, 'files': {}}}))
            with patch('doppelgng.dependencies._git', side_effect=AssertionError('No network')):
                with self.assertRaisesRegex(RuntimeError, 'packaged crawler is missing'):
                    ensure_crawler(root, offline=True)
