from contextlib import redirect_stdout
import base64
import hashlib
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from doppelgng.__main__ import main
from doppelgng.crawler import crawler_identity, load_crawler
from doppelgng.dependencies import default_crawler
from doppelgng.pipeline import build_adapter, capture
from doppelgng.reconstruct import reconstruct, public_url
from doppelgng.storage import Store, workspace_lock


class RecoveryRegressions(unittest.TestCase):
    def test_export_cannot_read_a_workspace_owned_by_another_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            Store(directory, 'https://example.test/')
            with workspace_lock(directory), patch('doppelgng.__main__.export_project') as export:
                with self.assertRaisesRegex(RuntimeError, 'Another capture'):
                    main(['export', '--output', directory])
            export.assert_not_called()

    def test_capture_startup_failure_is_checkpointed_as_incomplete(self):
        with tempfile.TemporaryDirectory() as directory, patch('doppelgng.pipeline.Preview', side_effect=RuntimeError('Preview port unavailable')), patch('doppelgng.pipeline.atomic_json'):
            with self.assertRaisesRegex(RuntimeError, 'port unavailable'):
                capture('https://example.test/', default_crawler(), directory)
            store = Store(directory)
            self.assertEqual(store.data['status'], 'incomplete')

    def test_interrupted_validation_leaves_a_failed_page_and_incomplete_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://example.test/')
            page = store.page(store.data['target'])
            page.update(kind='page', state='complete', resources=[])
            store.data.update(status='complete', policy={'allowed_visual_ratio': 0.01})
            (store.artifact_dir(page['url']) / 'baseline.json').write_text('[{}]')
            store.save()
            with patch('doppelgng.__main__.Preview'), patch('doppelgng.__main__.Waterfox'), patch('doppelgng.__main__.local_validate', side_effect=RuntimeError('Browser disconnected')), redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, 'disconnected'):
                    main(['validate', '--output', directory])
            resumed = Store(directory)
            self.assertEqual(resumed.data['status'], 'incomplete')
            self.assertEqual(resumed.page(page['url'])['state'], 'failed')

    def test_rewritten_resources_keep_valid_subresource_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://example.test/')
            source = b'body{background:url(/image.svg)}'
            sri = 'sha384-' + base64.b64encode(hashlib.sha384(source).digest()).decode()
            page = store.resource('https://example.test/', f'<link rel="stylesheet" href="/style.css" integrity="{sri}">'.encode(), headers={'content-type': 'text/html'})
            style = store.resource('https://example.test/style.css', source, headers={'content-type': 'text/css'})
            reconstruct(store, [page['url'], style['url']])
            integrity = BeautifulSoup((store.root / page['local']).read_text(), 'html.parser').link['integrity']
            expected = 'sha384-' + base64.b64encode(hashlib.sha384((store.root / style['local']).read_bytes()).digest()).decode()
            self.assertEqual(integrity, expected)
            self.assertEqual((store.root / style['raw']).read_bytes(), source)

    def test_download_capture_works_when_head_is_not_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://example.test/')
            url = 'https://example.test/download.bin'
            browser = SimpleNamespace(driver=SimpleNamespace(execute_script=lambda *_: 'fixture'), bidi=SimpleNamespace(events=[]))
            crawler = build_adapter(load_crawler(default_crawler()), store, browser, SimpleNamespace(origin='http://127.0.0.1:4173'), viewports=[[1440, 900]], allowed_ratio=0.01, scenarios={}, quiet=True)
            self.addCleanup(crawler.archive.session.close)
            record = store.resource(url, b'fixture download', headers={'content-type': 'application/octet-stream'})
            head = MagicMock(status_code=405, headers={})
            head.raise_for_status.side_effect = RuntimeError('HEAD method is not supported')
            get = MagicMock(status_code=200, headers={'content-type': 'application/octet-stream'})
            with patch.object(crawler.archive.session, 'head', return_value=head), patch.object(crawler.archive.session, 'get', return_value=get), patch.object(crawler.archive, 'retrieve', return_value=record), patch('doppelgng.pipeline.requests.get', return_value=SimpleNamespace(status_code=200, content=b'fixture download')):
                crawler._fetch(url)
            self.assertEqual(store.page(url)['state'], 'download_validated')

    def test_original_integrity_failure_is_not_silently_repaired(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://example.test/')
            source = b'body{background:url(/image.svg)}'
            weak = 'sha256-' + base64.b64encode(hashlib.sha256(source).digest()).decode()
            original = weak + ' sha512-invalid'
            page = store.resource('https://example.test/', f'<link rel="stylesheet" href="/style.css" integrity="{original}">'.encode(), headers={'content-type': 'Text/Html'})
            style = store.resource('https://example.test/style.css', source, headers={'content-type': 'Text/Css'})
            reconstruct(store, [page['url'], style['url']])
            self.assertEqual(BeautifulSoup((store.root / page['local']).read_text(), 'html.parser').link['integrity'], original)

    def test_refetch_repairs_corrupt_content_addressed_raw_file(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://example.test/')
            record = store.resource('https://example.test/app.js', b'original')
            (store.root / record['raw']).write_bytes(b'corrupted')
            store.resource(record['url'], b'original')
            self.assertEqual(store.verify([record['url']]), [])

    def test_recapturing_identical_source_keeps_valid_local_bytes_and_pass_state(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://example.test/')
            url = 'https://example.test/style.css'
            source = b'body{background:url(image.svg)}'
            record = store.resource(url, source, headers={'content-type': 'text/css'})
            reconstruct(store, [url])
            local_hash = record['local_sha256']
            page = store.page(store.data['target'])
            page.update(state='complete', resources=[url], validation={'passed': True})
            store.resource(url, source, headers={'content-type': 'text/css'})
            reconstruct(store, [url])
            self.assertEqual(store.data['resources'][url]['local_sha256'], local_hash)
            self.assertEqual(page['state'], 'complete')

    def test_changed_shared_resources_invalidate_both_validated_and_complete_pages(self):
        for state in ('validated', 'complete'):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as directory:
                store = Store(directory, 'https://example.test/')
                resource = store.resource('https://example.test/app.js', b'const version=1;', headers={'content-type': 'application/javascript'})
                page = store.page('https://example.test/')
                page.update(state=state, resources=[resource['url']], validation={'passed': True})
                store.data['status'] = 'complete'
                store.resource(resource['url'], b'const version=2;', headers={'content-type': 'application/javascript'})
                reconstruct(store, [resource['url']])
                self.assertNotIn(page['state'], ('complete', 'validated'))
                self.assertFalse(page['validation'].get('passed', False))
                self.assertNotEqual(store.data['status'], 'complete')

    def test_other_scheme_on_same_host_is_replayed_as_external_asset(self):
        url = 'https://example.test/image.svg'
        self.assertTrue(public_url(url, 'http://example.test/').startswith('/__doppelgng__/asset/'))

    def test_equivalent_default_ports_remain_first_party(self):
        self.assertEqual(public_url('https://EXAMPLE.test:443/image.svg', 'https://example.test/'), '/image.svg')
        self.assertEqual(public_url('http://example.test:80/image.svg', 'http://example.test/'), '/image.svg')
        self.assertTrue(public_url('https://example.test:444/image.svg', 'https://example.test/').startswith('/__doppelgng__/asset/'))

    def test_integrity_rewriting_respects_relative_base_and_multiple_algorithms(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://example.test/')
            source = b'body{background:url(image.svg)}'
            original = ' '.join(algorithm + '-' + base64.b64encode(hashlib.new(algorithm, source).digest()).decode() for algorithm in ('sha256', 'sha512'))
            page = store.resource('https://example.test/', f'<base href="/assets/"><link rel="stylesheet" href="style.css" integrity="{original}">'.encode(), headers={'content-type': 'text/html'})
            style = store.resource('https://example.test/assets/style.css', source, headers={'content-type': 'text/css'})
            reconstruct(store, [page['url'], style['url']])
            local = (store.root / style['local']).read_bytes()
            expected = ' '.join(algorithm + '-' + base64.b64encode(hashlib.new(algorithm, local).digest()).decode() for algorithm in ('sha256', 'sha512'))
            self.assertEqual(BeautifulSoup((store.root / page['local']).read_text(), 'html.parser').link['integrity'], expected)

    def test_html_preloads_keep_integrity_after_dependent_documents_are_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://example.test/')
            def preload(destination, body):
                token = 'sha384-' + base64.b64encode(hashlib.sha384(body).digest()).decode()
                return f'<link rel="preload" as="fetch" href="{destination}" integrity="{token}">'.encode()
            leaf = b'<img src="relative.svg">'
            middle = preload('leaf.html', leaf)
            outer = preload('middle.html', middle)
            urls = ['https://example.test/outer.html', 'https://example.test/middle.html', 'https://example.test/leaf.html']
            for url, body in zip(urls, (outer, middle, leaf)):
                store.resource(url, body, headers={'content-type': 'text/html'})
            reconstruct(store, urls)
            for parent, child in zip(urls, urls[1:]):
                document = store.data['resources'][parent]
                dependency = store.data['resources'][child]
                actual = BeautifulSoup((store.root / document['local']).read_text(), 'html.parser').link['integrity']
                expected = 'sha384-' + base64.b64encode(hashlib.sha384((store.root / dependency['local']).read_bytes()).digest()).decode()
                self.assertEqual(actual, expected)

    def test_resume_retains_explicit_resource_authorizations_and_stricter_existing_pass(self):
        crawler = default_crawler()
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://example.test/', crawler_identity(crawler))
            store.page(store.data['target']).update(state='complete', resources=[], validation={'passed': True})
            authorized = ['http://127.0.0.1:4319/']
            store.data['policy'] = {'allowed_visual_ratio': 0.01, 'viewports': [[1440, 900], [390, 844]], 'authorized_resource_origins': authorized}
            store.save()
            observed = []
            def build(_module, resumed, *_args, **_kwargs):
                observed.append((resumed.page(resumed.data['target'])['state'], resumed.data['policy']['authorized_resource_origins']))
                return SimpleNamespace(crawl=lambda: None, archive=SimpleNamespace(session=SimpleNamespace(close=lambda: None)))
            browser = MagicMock()
            browser.__enter__.return_value.identity = {}
            with patch('doppelgng.pipeline.Preview'), patch('doppelgng.pipeline.Waterfox', return_value=browser), patch('doppelgng.pipeline.build_adapter', side_effect=build), patch('doppelgng.pipeline.navigation_validation'), patch('doppelgng.pipeline.atomic_json'), redirect_stdout(io.StringIO()):
                capture('https://example.test/', crawler, directory, allowed_ratio=0.02)
            self.assertEqual(observed, [('complete', authorized)])

    def test_redirected_document_rewrites_relative_urls_against_final_url(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://example.test/')
            record = store.resource('https://example.test/guide', b'<img src="image.svg">', headers={'content-type': 'text/html'})
            record['final_url'] = 'https://example.test/guide/'
            reconstruct(store, [record['url']])
            self.assertIn('src="/guide/image.svg"', (store.root / record['local']).read_text())

    def test_changing_validation_requirements_does_not_reuse_old_passes(self):
        crawler = default_crawler()
        for change in ('viewports', 'tolerance', 'scenarios'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                store = Store(directory, 'https://example.test/', crawler_identity(crawler))
                store.page(store.data['target']).update(state='complete', resources=[], validation={'passed': True})
                store.data['policy'] = {'allowed_visual_ratio': 0.01, 'viewports': [[1440, 900], [390, 844]]}
                store.data['scenarios'] = {}
                store.save()
                observed = []
                def build(_module, resumed, *_args, **_kwargs):
                    observed.append(resumed.page(resumed.data['target'])['state'])
                    return SimpleNamespace(crawl=lambda: None, archive=SimpleNamespace(session=SimpleNamespace(close=lambda: None)))
                kwargs = {'viewports': [[800, 600]]} if change == 'viewports' else {'allowed_ratio': 0} if change == 'tolerance' else {'scenarios': {'/': [{'action': 'click', 'selector': '#new'}]}}
                browser = MagicMock()
                browser.__enter__.return_value.identity = {}
                with patch('doppelgng.pipeline.Preview'), patch('doppelgng.pipeline.Waterfox', return_value=browser), patch('doppelgng.pipeline.build_adapter', side_effect=build), patch('doppelgng.pipeline.navigation_validation'), patch('doppelgng.pipeline.atomic_json'), redirect_stdout(io.StringIO()):
                    capture('https://example.test/', crawler, directory, **kwargs)
                self.assertNotIn(observed[0], ('validated', 'complete'))

    def test_validate_recovers_download_after_bytes_are_repaired(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://example.test/')
            url = 'https://example.test/download.bin'
            store.resource(url, b'download')
            store.page(url).update(kind='download', state='failed', resources=[url], validation={'passed': False})
            store.save()
            observed = []
            def navigate(resumed, *_args, **_kwargs):
                observed.append(resumed.page(url)['state'])
            with patch('doppelgng.__main__.Preview'), patch('doppelgng.__main__.Waterfox'), patch('doppelgng.__main__.navigation_validation', side_effect=navigate), redirect_stdout(io.StringIO()):
                main(['validate', '--output', directory])
            self.assertEqual(observed, ['download_validated'])
