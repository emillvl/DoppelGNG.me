import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from doppelgng.distribution import SOURCE_FILES, build_distribution
from test_runtime import make_runtime


class DistributionTests(unittest.TestCase):
    def test_bundle_includes_dependencies_and_excludes_local_website_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in SOURCE_FILES:
                (root / name).write_text('application source')
            make_runtime(root)
            lock = json.loads((root / 'runtime-lock.json').read_text())
            lock['crawler'] = {'repository': 'https://github.com/emillvl/webcrawler.git', 'revision': 'a' * 40, 'files': {'webcrawler.py': hashlib.sha256(b'crawler').hexdigest()}}
            (root / 'runtime-lock.json').write_text(json.dumps(lock))
            crawler = root / '.tools/webcrawler'
            crawler.mkdir()
            (crawler / 'webcrawler.py').write_bytes(b'crawler')
            for name in ('waterfox-provenance.json', 'geckodriver-provenance.json'):
                (root / '.tools' / name).write_text('{}')
            for name in ('.env', '.doppelgng/private-page.html', '.tools/waterfox-setup.exe', 'example.test/site/page.html', 'old.example.test+copied/site/page.html'):
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('must remain outside the package')
            result = build_distribution(root)
            with zipfile.ZipFile(result['archive']) as archive:
                names = archive.namelist()
                self.assertIn('DoppelGNG.me/.tools/waterfox/core/xul.dll', names)
                self.assertIn('DoppelGNG.me/.tools/webcrawler/webcrawler.py', names)
                self.assertIn('DoppelGNG.me/THIRD_PARTY_NOTICES.md', names)
                self.assertFalse(any('private-page' in name or '/example.test/' in name or '+copied' in name or 'waterfox-setup.exe' in name or name.endswith('/.env') or '/.git/' in name for name in names))
                manifest = json.loads(archive.read('DoppelGNG.me/bundle-manifest.json'))
                for name, expected in manifest['files'].items():
                    self.assertEqual(hashlib.sha256(archive.read('DoppelGNG.me/' + name)).hexdigest(), expected['sha256'])
