from pathlib import Path
import tempfile
import unittest

from doppelgng.export import default_output, export_project
from doppelgng.storage import Store


class ExportTests(unittest.TestCase):
    def test_default_names_are_website_plus_copied_and_safe_for_windows(self):
        self.assertEqual(str(default_output('https://example.com/path')), 'example.com+copied')
        self.assertEqual(str(default_output('http://localhost:4319/')), 'localhost_4319+copied')

    def test_delivery_is_separate_and_preserves_all_resource_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            store = Store(directory / 'capture', 'https://example.test/')
            store.resource('https://example.test/', b'<title>Copied</title>', headers={'content-type': 'text/html'})
            store.data['status'] = 'complete'
            store.save()
            (store.root / 'package.json').write_text('{"scripts":{"dev":"node server.mjs"}}')
            (store.root / 'server.mjs').write_text('// generated project entry')
            target = export_project(store, directory / 'example.test+copied')
            self.assertEqual(Store(target).verify(['https://example.test/']), [])
            self.assertTrue((target / 'package.json').is_file())
            self.assertTrue((store.root / 'manifest.json').is_file())
            with self.assertRaisesRegex(ValueError, 'already exists'):
                export_project(store, target)

    def test_unvalidated_work_cannot_be_exported_as_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'capture', 'https://example.test/')
            with self.assertRaisesRegex(ValueError, 'completed and validated'):
                export_project(store, Path(directory) / 'example.test+copied')
