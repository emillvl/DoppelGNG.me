"""Controlled destination, redirect, DNS pinning and archive-limit regressions."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import requests

from doppelgng.archive import Archive, ExtractionFailure
from doppelgng.network import DestinationDenied, DestinationPolicy, capture_session
from doppelgng.storage import Store


@contextmanager
def owned_server(redirect=None):
    seen = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append(self.path)
            body = b'owned local fixture'
            self.send_response(302 if redirect else 200)
            if redirect:
                self.send_header('Location', redirect)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/', seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class CaptureNetworkTests(unittest.TestCase):
    def test_direct_capture_preserves_configured_certificate_authorities(self):
        for variable in ('REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE'):
            with self.subTest(variable=variable), patch.dict('os.environ', {variable: 'owned-fixture-ca.pem'}, clear=True), capture_session('https://authorized.test/') as session:
                self.assertEqual(session.verify, 'owned-fixture-ca.pem')
                self.assertFalse(session.trust_env)

    def test_authorized_loopback_origin_still_works(self):
        with owned_server() as (url, seen), capture_session(url) as session:
            self.assertEqual(session.get(url, timeout=2).content, b'owned local fixture')
            self.assertEqual(seen, ['/'])

    def test_redirect_cannot_pivot_to_unrelated_private_service(self):
        with owned_server() as (private, private_seen), owned_server(private) as (target, target_seen), capture_session(target) as session:
            with self.assertRaisesRegex(DestinationDenied, 'not authorized'):
                session.get(target, timeout=2)
            self.assertEqual(target_seen, ['/'])
            self.assertEqual(private_seen, [])

    def test_explicit_additional_origin_allows_private_dependency_but_not_a_further_pivot(self):
        with owned_server() as (other, other_seen), owned_server() as (dependency, dependency_seen), owned_server(dependency) as (target, _):
            with capture_session(target, [dependency]) as session:
                self.assertEqual(session.get(target, timeout=2).content, b'owned local fixture')
                self.assertEqual(dependency_seen, ['/'])
                with self.assertRaises(DestinationDenied):
                    session.get(other, timeout=2)
            self.assertEqual(other_seen, [])
        with owned_server() as (other, other_seen), owned_server(other) as (dependency, _), capture_session('https://authorized.test/', [dependency]) as session:
            with self.assertRaises(DestinationDenied):
                session.get(dependency, timeout=2)
            self.assertEqual(other_seen, [])

    def test_explicit_browser_resource_authorization_remains_origin_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://authorized.test/')
            store.data['policy']['authorized_resource_origins'] = ['http://127.0.0.1:4319/']
            browser = SimpleNamespace(driver=SimpleNamespace(execute_script=lambda *_: 'fixture'), source=lambda url: ({'status': 200, 'url': url, 'headers': {}}, b'authorized dependency'))
            archive = Archive(store, browser)
            self.addCleanup(archive.session.close)
            self.assertEqual(archive.retrieve('http://127.0.0.1:4319/asset')['bytes'], 21)
            with self.assertRaises(DestinationDenied):
                archive.retrieve('http://127.0.0.1:4320/asset')

    def test_private_and_mixed_dns_answers_are_rejected(self):
        policy = DestinationPolicy('https://authorized.test/')
        cases = [['127.0.0.1'], ['10.0.0.1'], ['169.254.169.254'], ['::1'], ['::ffff:127.0.0.1'], ['::ffff:224.0.0.1'], ['fe80::1'], ['224.0.0.1'], ['ff02::1'], ['0.0.0.0'], ['93.184.215.14', '192.168.0.1'], []]
        for addresses in cases:
            with self.subTest(addresses=addresses), patch('doppelgng.network.socket.getaddrinfo', return_value=[(2, 1, 6, '', (ip, 443)) for ip in addresses]):
                with self.assertRaises(DestinationDenied):
                    policy.address('https://unrelated.test/file')

    def test_authorization_is_scoped_to_scheme_host_and_port(self):
        policy = DestinationPolicy('http://localhost:4319/')
        with patch('doppelgng.network.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]) as dns:
            self.assertIsNone(policy.address('http://LOCALHOST:4319/data'))
            dns.assert_not_called()
            for url in ('http://localhost:4320/', 'https://localhost:4319/', 'http://user:pass@localhost:4319/'):
                with self.subTest(url=url), self.assertRaises(DestinationDenied):
                    policy.address(url)

    def test_public_connections_pin_address_and_preserve_host_and_tls_identity(self):
        for scheme in ('http', 'https'):
            with self.subTest(scheme=scheme), capture_session('https://authorized.test/') as session, patch('doppelgng.network.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.215.14', 443))]):
                request = requests.Request('GET', f'{scheme}://cdn.test/asset').prepare()
                adapter = session.get_adapter(request.url)
                with patch.object(adapter.poolmanager, 'connection_from_host') as pool:
                    adapter.get_connection_with_tls_context(request, verify=True)
                kwargs = pool.call_args.kwargs
                self.assertEqual(kwargs['host'], '93.184.215.14')
                self.assertEqual(request.headers['Host'], 'cdn.test')
                if scheme == 'https':
                    self.assertEqual(kwargs['pool_kwargs']['server_hostname'], 'cdn.test')
                    self.assertEqual(kwargs['pool_kwargs']['assert_hostname'], 'cdn.test')
                    self.assertNotEqual(kwargs['pool_kwargs'].get('cert_reqs'), 'CERT_NONE')

    def test_public_http_transport_does_not_resolve_the_original_host_again(self):
        with owned_server() as (url, _seen), capture_session('https://authorized.test/') as session:
            local_port = int(url.split(':')[-1].rstrip('/'))
            destinations = []
            def connect(address, *args, **kwargs):
                destinations.append(address)
                connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                connection.settimeout(2)
                try:
                    connection.connect(('127.0.0.1', local_port))
                    return connection
                except BaseException:
                    connection.close()
                    raise
            with patch('doppelgng.network.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.215.14', 80))]), patch('urllib3.util.connection.create_connection', side_effect=connect):
                # Redirect the socket locally while exercising public DNS policy.
                self.assertEqual(session.get('http://cdn.test/asset', timeout=2).status_code, 200)
            self.assertEqual(destinations, [('93.184.215.14', 80)])

    def test_public_transport_falls_back_to_another_validated_address(self):
        with owned_server() as (url, _seen), capture_session('https://authorized.test/') as session:
            local_port = int(url.split(':')[-1].rstrip('/'))
            destinations = []
            def connect(address, *args, **kwargs):
                destinations.append(address)
                if address[0] == '2606:4700:4700::1111':
                    raise OSError('Controlled unavailable IPv6 route')
                connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                connection.settimeout(2)
                connection.connect(('127.0.0.1', local_port))
                return connection
            answers = [(10, 1, 6, '', ('2606:4700:4700::1111', 80, 0, 0)), (2, 1, 6, '', ('93.184.215.14', 80))]
            with patch('doppelgng.network.socket.getaddrinfo', return_value=answers), patch('urllib3.util.connection.create_connection', side_effect=connect):
                self.assertEqual(session.get('http://cdn.test/asset', timeout=2).status_code, 200)
            self.assertEqual(destinations, [('2606:4700:4700::1111', 80), ('93.184.215.14', 80)])

    def test_browser_observed_private_body_is_not_rehosted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://authorized.test/')
            browser = SimpleNamespace(driver=SimpleNamespace(execute_script=lambda *_: 'fixture'), bidi=SimpleNamespace(body=MagicMock(return_value=b'private')))
            archive = Archive(store, browser)
            self.addCleanup(archive.session.close)
            event = {'method': 'network.responseCompleted', 'params': {'request': {'request': 'one', 'method': 'GET'}, 'response': {'url': 'http://127.0.0.1/private', 'status': 200}}}
            with self.assertRaises(DestinationDenied):
                archive.ingest([event])
            browser.bidi.body.assert_not_called()
            self.assertEqual(store.data['resources'], {})

    def test_evicted_browser_body_refetch_obeys_resource_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://authorized.test/')
            url = 'https://authorized.test/data'
            browser = SimpleNamespace(driver=SimpleNamespace(execute_script=lambda *_: 'fixture'), bidi=SimpleNamespace(body=MagicMock(side_effect=RuntimeError('no such network data'))), source=lambda *_: ({'status': 200, 'url': url, 'headers': {}}, b'12345'))
            archive = Archive(store, browser, max_bytes=4)
            self.addCleanup(archive.session.close)
            event = {'method': 'network.responseCompleted', 'params': {'request': {'request': 'one', 'method': 'GET'}, 'response': {'url': url, 'status': 200}}}
            with self.assertRaisesRegex(ExtractionFailure, 'byte limit'):
                archive.ingest([event])
            self.assertNotIn(url, store.data['resources'])
