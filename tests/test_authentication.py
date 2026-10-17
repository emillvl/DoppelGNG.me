from contextlib import redirect_stderr
import getpass
import io
import json
from pathlib import Path
import queue
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import warnings

from doppelgng.authentication import LoginError, LoginSession, SecretGuard, hidden_credentials, login_scope
from doppelgng.__main__ import main
from doppelgng.network import capture_session
from doppelgng.storage import Store
from doppelgng.browser import Bidi
from doppelgng.validation import record_baseline
from fixture_auth_site import login_site


class LoginTests(unittest.TestCase):
    def login(self, target, state, **options):
        login = LoginSession(target, check='#signed-in', **options)
        self.addCleanup(login.close)
        login.authenticate(lambda: (state['username'], state['password']))
        return login

    def test_form_login_and_protected_native_get_and_head(self):
        with login_site() as (target, state):
            login = self.login(target, state)
            self.assertTrue(login.active)
            self.assertEqual(state['posts'], 1)
            with capture_session(target, authentication=login) as session:
                response = session.get(target)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn('Cookie', response.request.headers)
                self.assertEqual(session.head(target + 'download.bin').status_code, 200)
            self.assertGreater(state['protected_gets'], 0)
            self.assertGreater(state['protected_heads'], 0)

    def test_wrong_password_stops_without_revealing_it(self):
        with login_site() as (target, state):
            login = LoginSession(target, check='#signed-in')
            try:
                with self.assertRaises(LoginError) as error:
                    login.authenticate(lambda: (state['username'], 'wrong-secret-value'))
                self.assertNotIn('wrong-secret-value', str(error.exception))
                self.assertFalse(login.active)
            finally:
                login.close()

    def test_cross_origin_form_action_is_rejected_before_prompt(self):
        with login_site() as (target, state), login_site() as (other, foreign):
            state['action'] = other + 'login'
            login = LoginSession(target, check='#signed-in')
            try:
                with patch('builtins.input') as prompt, self.assertRaises(LoginError):
                    login.authenticate(prompt)
                prompt.assert_not_called()
                self.assertEqual(foreign['posts'], 0)
            finally:
                login.close()

    def test_login_redirect_does_not_forward_to_another_origin(self):
        with login_site() as (target, state), login_site() as (other, foreign):
            state['post_redirect'] = other
            login = LoginSession(target, check='#signed-in')
            try:
                with self.assertRaises(LoginError):
                    login.authenticate(lambda: (state['username'], state['password']))
                self.assertEqual(foreign['posts'], 0)
                self.assertEqual(foreign['protected_gets'], 0)
            finally:
                login.close()

    def test_307_does_not_resend_the_password(self):
        with login_site() as (target, state):
            state['post_status'] = 307
            login = LoginSession(target, check='#signed-in')
            try:
                with self.assertRaises(LoginError):
                    login.authenticate(lambda: (state['username'], state['password']))
                self.assertEqual(state['posts'], 1)
            finally:
                login.close()

    def test_session_cookie_is_not_sent_to_another_port(self):
        with login_site() as (target, state), login_site() as (other, foreign):
            login = self.login(target, state)
            foreign['cookie'] = state['cookie']
            with capture_session(target, [other], authentication=login) as session:
                response = session.get(other, allow_redirects=False)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(foreign['protected_gets'], 0)

    def test_echoed_password_aborts_and_can_never_be_written(self):
        with login_site() as (target, state):
            state['echo'] = True
            login = LoginSession(target, check='#signed-in')
            try:
                with self.assertRaises(LoginError):
                    login.authenticate(lambda: (state['username'], state['password']))
                with tempfile.TemporaryDirectory() as directory:
                    store = Store(directory, target)
                    store.authentication = login
                    with self.assertRaises(LoginError):
                        store.resource(target, state['password'].encode())
                    self.assertEqual(list((store.root / 'raw').iterdir()), [])
                    self.assertEqual(list((store.root / 'site').iterdir()), [])
            finally:
                login.close()

    def test_guard_blocks_credentials_and_common_encodings(self):
        guard = SecretGuard()
        guard.add('unique secret&value')
        for value in ('unique secret&value', 'unique+secret%26value', 'unique%20secret%26value', 'unique secret&amp;value'):
            with self.subTest(value=value), self.assertRaises(LoginError):
                guard.check(value)
        for encoding in ('utf-16-le', 'utf-16-be'):
            with self.assertRaises(LoginError):
                guard.check('unique secret&value'.encode(encoding))
        buffers = list(guard.patterns)
        guard.close()
        self.assertEqual(guard.patterns, [])
        self.assertTrue(all(not any(buffer) for buffer in buffers))

    def test_login_scope_discards_session_after_error(self):
        with login_site() as (target, state):
            args = SimpleNamespace(login_url=None, login_check='#signed-in', login_form=None, login_user_field=None, login_password_field=None)
            with patch('getpass.getpass', side_effect=[state['username'], state['password']]):
                with self.assertRaises(LoginError):
                    with login_scope(target, args) as login:
                        raise ValueError('sensitive arbitrary error')
            self.assertFalse(login.active)
            self.assertEqual(list(login.cookies), [])
            self.assertEqual(login.guard.patterns, [])

    def test_expected_signed_in_marker_and_expiry_are_required(self):
        with login_site() as (target, state):
            login = self.login(target, state)
            for source in ('<h1>Public page</h1>', '<h1 id="signed-in">x</h1><input type="password">'):
                with self.assertRaises(LoginError):
                    login.check_page(target, source)

    def test_login_uses_https_except_loopback(self):
        with self.assertRaises(LoginError):
            LoginSession('http://example.test/', check='#signed-in')

    def test_hidden_input_refuses_echo_fallback(self):
        def fallback(*_):
            warnings.warn('No terminal', getpass.GetPassWarning)
        with patch('getpass.getpass', side_effect=fallback), self.assertRaises(LoginError):
            hidden_credentials()

    def test_password_argument_is_rejected_without_echoing_it(self):
        for flag in (['--login', 'account:secret-command-value'], ['--login=account:secret-command-value']):
            with redirect_stderr(io.StringIO()) as output, self.assertRaises(SystemExit):
                main(['capture', '--url', 'https://example.test', '--authorized', *flag])
            self.assertNotIn('secret-command-value', output.getvalue())

    def test_login_requires_an_expected_state_and_flags_require_login(self):
        for flags in (['--login'], ['--login-url', 'https://example.test/login'], ['--login-check', '#signed-in']):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit), patch('doppelgng.__main__.capture') as capture:
                main(['capture', '--url', 'https://example.test/', '--authorized', *flags])
            capture.assert_not_called()

    def test_existing_capture_is_refused_before_a_login_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://example.test/')
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit), patch('getpass.getpass') as prompt:
                main(['capture', '--url', 'https://example.test/', '--authorized', '--output', directory, '--login', '--login-check', '#signed-in'])
            prompt.assert_not_called()

    def test_authenticated_validation_requires_a_new_login(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, 'https://example.test/')
            store.data['authentication'] = {'required': True, 'method': 'html-form'}
            store.save()
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit), patch('doppelgng.__main__.Waterfox') as browser:
                main(['validate', '--output', directory])
            browser.assert_not_called()

    def test_browser_evidence_drops_headers_and_blocks_secret_console_output(self):
        login = LoginSession('https://example.test/', check='#signed-in')
        try:
            login.guard.add('private-cookie-example')
            bidi = Bidi.__new__(Bidi)
            bidi.authentication, bidi.failure = login, None
            event = {'method': 'network.responseCompleted', 'params': {'request': {'cookies': ['private-cookie-example'], 'headers': [{'name': 'Cookie', 'value': {'type': 'string', 'value': 'private-cookie-example'}}]}, 'response': {'headers': [{'name': 'Set-Cookie', 'value': {'type': 'string', 'value': 'private-cookie-example'}}]}}}
            self.assertNotIn('private-cookie-example', json.dumps(bidi._clean_event(event)))
            cleaned = bidi._clean_event({'method': 'log.entryAdded', 'params': {'text': 'private-cookie-example'}})
            self.assertEqual(cleaned['method'], 'recorder.error')
            self.assertNotIn('private-cookie-example', json.dumps(cleaned))
            self.assertIsInstance(bidi.failure, LoginError)
        finally:
            login.close()

    def test_browser_interception_cookie_origin_and_post_rejection(self):
        login = LoginSession('https://example.test/', check='#signed-in')
        try:
            login.cookies.set('sid', 'private-cookie-example', domain='example.test', path='/')
            for url, method, cookie_expected in [('https://example.test/page', 'GET', True), ('https://example.test:444/page', 'GET', False), ('https://external.test/page', 'GET', False), ('https://example.test/page', 'POST', False)]:
                with self.subTest(url=url, method=method):
                    bidi = Bidi.__new__(Bidi)
                    bidi.authentication, bidi.failure, bidi.closed = login, None, False
                    bidi.interceptions = queue.Queue()
                    bidi.interceptions.put({'method': 'network.beforeRequestSent', 'params': {'request': {'request': 'test', 'url': url, 'method': method, 'headers': [{'name': 'Cookie', 'value': {'type': 'string', 'value': 'untrusted'}}]}}})
                    bidi.interceptions.put(None)
                    calls = []
                    bidi.command = lambda name, params: calls.append((name, params))
                    bidi._intercept()
                    self.assertEqual(calls[0][0], 'network.failRequest' if method == 'POST' else 'network.continueRequest')
                    if method == 'GET':
                        self.assertEqual(bool(calls[0][1]['cookies']), cookie_expected)
                        self.assertEqual(calls[0][1]['headers'], [])
        finally:
            login.close()

    def test_cookie_response_is_kept_only_in_memory(self):
        login = LoginSession('https://example.test/', check='#signed-in')
        try:
            login.receive_browser_cookies('https://example.test/page', [{'name': 'Set-Cookie', 'value': {'type': 'string', 'value': 'sid=private-cookie-example; Path=/; Secure; HttpOnly'}}])
            self.assertIn('sid=private-cookie-example', login.cookie_header('https://example.test/'))
            self.assertEqual(login.cookie_header('https://example.test:444/'), '')
            with self.assertRaises(LoginError):
                login.guard.check('private-cookie-example')
        finally:
            login.close()

    def test_cleanup_clears_secrets_even_if_transport_close_fails(self):
        login = LoginSession('https://example.test/', check='#signed-in')
        login.cookies.set('sid', 'cleanup-example', domain='example.test')
        login.guard.add('cleanup-example')
        with patch.object(login.session, 'close', side_effect=OSError('transport close failure')), self.assertRaises(OSError):
            login.close()
        self.assertEqual(list(login.cookies), [])
        self.assertEqual(login.guard.patterns, [])

    def test_browser_cookie_expiry_and_default_path_are_honored(self):
        login = LoginSession('https://example.test/', check='#signed-in')
        try:
            login.receive_browser_cookies('https://example.test/app/page', [{'name': 'Set-Cookie', 'value': {'type': 'string', 'value': 'sid=scoped-cookie-example; Max-Age=3600; HttpOnly'}}])
            self.assertIn('sid=', login.cookie_header('https://example.test/app/next'))
            self.assertEqual(login.cookie_header('https://example.test/other'), '')
            login.receive_browser_cookies('https://example.test/app/page', [{'name': 'Set-Cookie', 'value': {'type': 'string', 'value': 'sid=expired; Max-Age=0; HttpOnly'}}])
            self.assertEqual(login.cookie_header('https://example.test/app/next'), '')
        finally:
            login.close()

    def test_new_secret_response_stops_before_baseline_screenshot(self):
        browser = MagicMock()
        browser.authentication = True
        def reject():
            raise LoginError('Response contains login data')
        with tempfile.TemporaryDirectory() as temporary, patch('doppelgng.validation.exercise_discovery'), patch('doppelgng.validation.scroll'), self.assertRaises(LoginError):
            record_baseline(browser, 'https://example.test/', Path(temporary), [[800, 600]], reject)
        browser.driver.save_screenshot.assert_not_called()
