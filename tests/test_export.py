from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from doppelgng.export import default_output, export_project
from doppelgng.storage import Store


class ExportTests(unittest.TestCase):
    def test_default_names_use_each_websites_actual_domain(self):
        for url, expected in [('https://example.com/path', 'example.com'), ('https://www.another.org/catalogue', 'www.another.org'), ('http://localhost:4319/', 'localhost_4319')]:
            with self.subTest(url=url):
                self.assertEqual(str(default_output(url)), expected)

    def test_domain_names_remain_safe_for_windows_and_cannot_select_parent_folders(self):
        self.assertEqual(str(default_output('https://example.com./')), 'example.com')
        self.assertEqual(str(default_output('http://CON/')), '_CON')
        self.assertEqual(str(default_output('http://nul.example/')), '_nul.example')
        for url in ('http://./', 'http://../'):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, 'hostname'):
                default_output(url)

    def test_capture_preserves_an_unrelated_existing_domain_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            domain = Path(temporary) / 'example.com'
            domain.mkdir()
            original = domain / 'package.json'
            original.write_text('existing website project')
            with self.assertRaisesRegex(ValueError, 'unrelated files'):
                Store(domain, 'https://example.com/')
            self.assertEqual(original.read_text(), 'existing website project')
            self.assertEqual(list(domain.iterdir()), [original])

    def test_delivery_is_separate_and_preserves_all_resource_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            store = Store(directory / 'capture', 'https://example.test/')
            store.resource('https://example.test/', b'<title>Copied</title>', headers={'content-type': 'text/html'})
            store.data['status'] = 'complete'
            store.save()
            (store.root / 'package.json').write_text('{"scripts":{"dev":"node server.mjs"}}')
            (store.root / 'server.mjs').write_text('// generated project entry')
            with patch('os.getcwd', return_value=str(directory)):
                target = export_project(store)
            self.assertEqual(target, directory / 'example.test')
            self.assertEqual(Store(target).verify(['https://example.test/']), [])
            self.assertTrue((target / 'package.json').is_file())
            self.assertTrue((store.root / 'manifest.json').is_file())
            with self.assertRaisesRegex(ValueError, 'already exists'):
                export_project(store, target)

    def test_unvalidated_work_cannot_be_exported_as_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'capture', 'https://example.test/')
            with self.assertRaisesRegex(ValueError, 'completed and validated'):
                export_project(store, Path(directory) / 'example.test')
