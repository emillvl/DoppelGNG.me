from pathlib import Path
import tempfile
import unittest

from doppelgng.resources import html_process, css_process, js_process
from doppelgng.storage import Store, workspace_lock
from doppelgng.reconstruct import reconstruct


class ResourceTests(unittest.TestCase):
    def test_collects_nested_css_imports_fonts_and_fragment_exclusion(self):
        text = '@import "base.css"; @font-face{src:url(../font.woff2)} .x{background:url("a.png")} .y{filter:url(#shape)}'
        urls, modified = css_process(text, 'https://a.test/css/site.css', lambda x: '/local/' + x.split('/')[-1])
        self.assertEqual(urls, ['https://a.test/css/base.css', 'https://a.test/font.woff2', 'https://a.test/css/a.png'])
        self.assertIn('/local/font.woff2', modified)
        self.assertIn('url(#shape)', modified.replace('"', ''))

    def test_rendered_html_dependencies_srcset_inline_and_base(self):
        text = '<base href="/sub/"><link rel="stylesheet" href="x.css"><link rel="canonical" href="/"><img srcset="a.webp 1x, b.webp 2x"><style>.x{background:url(bg.svg)}</style><script type="module">import "./a.js"</script>'
        urls, _ = html_process(text, 'https://a.test/')
        self.assertEqual(set(urls), {'https://a.test/sub/x.css', 'https://a.test/sub/a.webp', 'https://a.test/sub/b.webp', 'https://a.test/sub/bg.svg', 'https://a.test/sub/a.js'})

    def test_js_literal_modules_workers_and_assets(self):
        urls, _ = js_process('import x from "./x.js"; import("./lazy.mjs"); new URL("./worker.js", import.meta.url); fetch("/api/items"); const logo="/a.svg";', 'https://a.test/js/main.js')
        self.assertEqual(set(urls), {'https://a.test/js/x.js', 'https://a.test/js/lazy.mjs', 'https://a.test/js/worker.js', 'https://a.test/a.svg'})

    def test_url_parser_probes_and_unexecuted_services_are_not_downloads(self):
        urls, _ = js_process('new URL("https://тест");fetch("/delete-account");', 'https://a.test/polyfill.js')
        self.assertEqual(urls, [])

    def test_inline_style_declarations_preserve_rendered_transform_values(self):
        urls, output = css_process('opacity: 1; transform: translate3d(0px, 2px, 0px); background: url(a.png)', 'https://a.test/', lambda _: '/a.png')
        self.assertEqual(urls, ['https://a.test/a.png'])
        self.assertIn('translate3d(0px, 2px, 0px)', output)

    def test_storage_is_collision_safe_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://a.test/')
            a = store.resource('https://a.test/p?q=1', b'one')
            b = store.resource('https://a.test/p?q=2', b'two')
            self.assertNotEqual(a['local'], b['local'])
            self.assertEqual(store.verify([a['url'], b['url']]), [])
            (Path(directory) / a['raw']).write_bytes(b'corrupt')
            self.assertEqual(store.verify([a['url']]), [a['url']])

    def test_resume_preserves_validated_state_and_original_code(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://a.test/')
            body = b'<script src="https://cdn.test/app.js"></script><a href="https://a.test/nested/#x">link</a>'
            resource = store.resource('https://a.test/', body, headers={'Content-Type': 'text/html'})
            reconstruct(store, ['https://a.test/'])
            self.assertEqual((store.root / resource['raw']).read_bytes(), body)
            self.assertIn('/__doppelgng__/asset/', (store.root / resource['local']).read_text())
            self.assertIn('/nested/#x', (store.root / resource['local']).read_text())
            store.page('https://a.test/')['state'] = 'complete'
            store.save()
            self.assertEqual(Store(directory).page('https://a.test/')['state'], 'complete')

    def test_target_mismatch_does_not_reuse_another_site(self):
        with tempfile.TemporaryDirectory() as directory:
            Store(directory, 'https://a.test/')
            with self.assertRaisesRegex(ValueError, 'another target'):
                Store(directory, 'https://b.test/')

    def test_concurrent_captures_cannot_overwrite_the_same_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            with workspace_lock(directory):
                with self.assertRaisesRegex(RuntimeError, 'Another capture'):
                    with workspace_lock(directory):
                        pass
            with workspace_lock(directory):
                self.assertTrue((Path(directory) / 'capture.lock').is_file())
