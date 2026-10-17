from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import requests

from doppelgng.archive import Archive, ExtractionFailure
from doppelgng.reconstruct import reconstruct
from doppelgng.storage import Store


class DependencyEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.store = Store(temporary.name, 'https://app.test/')
        self.browser = SimpleNamespace(driver=SimpleNamespace(execute_script=lambda *_: 'test browser'))
        self.archive = Archive(self.store, self.browser)
        self.addCleanup(self.archive.session.close)
        # Synthetic public asset names have no real DNS/network dependency.
        dns = patch('doppelgng.network.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.215.14', 443))])
        dns.start()
        self.addCleanup(dns.stop)

    def test_computed_asset_closure_uses_observed_full_url_without_inventing_requests(self):
        loader = 'https://cdn.test/tag/loader.js'
        payload = 'https://cdn.test/managed/version-1/payload.js'
        source = b'const parts=["https://cdn.test/managed/", "/payload.js"];const src=parts[0]+"version-1"+parts[1];'
        record = self.store.resource(loader, source, headers={'content-type': 'application/javascript'})
        self.store.resource(payload, b'window.runtimeLoaded=true;', headers={'content-type': 'application/javascript'}, source='waterfox-bidi')
        with patch.object(self.archive.session, 'get', side_effect=AssertionError('No invented HTTP request')), patch.object(self.browser, 'source', side_effect=AssertionError('No invented browser request'), create=True):
            resources = self.archive.closure([loader, payload])
        self.assertEqual(set(resources), {loader, payload})
        reconstruct(self.store, resources)
        self.assertEqual((self.store.root / record['raw']).read_bytes(), source)
        self.assertEqual((self.store.root / record['local']).read_bytes(), source)
        self.assertEqual(self.store.verify(resources), [])

    def test_real_missing_import_or_external_script_still_fails(self):
        cases = [
            ('https://app.test/app.js', b'import "./missing.js";', 'application/javascript', 'https://app.test/missing.js'),
            ('https://app.test/', b'<script src="https://cdn.test/missing.js"></script>', 'text/html', 'https://cdn.test/missing.js'),
        ]
        for parent, source, mime, missing in cases:
            with self.subTest(missing=missing):
                self.store.resource(parent, source, headers={'content-type': mime})
                response = MagicMock()
                response.__enter__.return_value = response
                response.raise_for_status.side_effect = requests.HTTPError('404 Not Found')
                with patch.object(self.browser, 'source', side_effect=RuntimeError('Browser resource missing'), create=True), patch.object(self.archive.session, 'get', return_value=response) as request:
                    with self.assertRaisesRegex(ExtractionFailure, '404 Not Found'):
                        self.archive.closure([parent])
                self.assertEqual(request.call_args.args[0], missing)

    def test_identical_browser_body_with_changed_response_metadata_invalidates_pass(self):
        url = 'https://app.test/data'
        self.store.resource(url, b'unchanged', headers={'content-type': 'text/plain'})
        page = self.store.page(self.store.data['target'])
        page.update(state='complete', resources=[url], validation={'passed': True})
        self.browser.bidi = SimpleNamespace(body=lambda _: b'unchanged')
        event = {'method': 'network.responseCompleted', 'params': {'request': {'request': 'metadata-change', 'method': 'GET'}, 'response': {'url': url, 'status': 200, 'headers': [{'name': 'Content-Type', 'value': {'type': 'string', 'value': 'text/html'}}]}}}
        self.archive.ingest([event])
        self.assertEqual(self.store.data['resources'][url]['content_type'], 'text/html')
        self.assertFalse(page['validation']['passed'])
        self.assertEqual(page['state'], 'reconstructed')
