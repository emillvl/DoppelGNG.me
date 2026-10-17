"""Prompt for a same-origin form login and keep its session in memory."""
from __future__ import annotations

import base64
from contextlib import contextmanager
import getpass
from email.utils import parsedate_to_datetime
import html
from http.cookies import SimpleCookie
import ipaddress
import json
import threading
import time
from urllib.parse import quote, quote_plus, urljoin, urlsplit
import warnings

from bs4 import BeautifulSoup
import requests

from .network import DestinationDenied, capture_session, origin


class LoginError(RuntimeError):
    pass


class SecretGuard:
    def __init__(self):
        self.patterns = []
        self.lock = threading.RLock()

    def add(self, value):
        if not value:
            return
        variants = {value, quote(value, safe=''), quote_plus(value), html.escape(value),
                    json.dumps(value, ensure_ascii=True)[1:-1], base64.b64encode(value.encode()).decode()}
        with self.lock:
            for variant in variants:
                for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
                    encoded = bytearray(variant.encode(encoding))
                    if encoded not in self.patterns:
                        self.patterns.append(encoded)

    def check(self, value):
        data = value if isinstance(value, bytes) else str(value).encode('utf-8')
        with self.lock:
            if any(pattern in data for pattern in self.patterns):
                raise LoginError('Capture stopped because a response or artifact contains login data. No matching artifact was written.')

    def close(self):
        with self.lock:
            for pattern in self.patterns:
                pattern[:] = b'\0' * len(pattern)
            self.patterns.clear()


def hidden_credentials():
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        try:
            username = getpass.getpass('Login username (hidden): ')
            password = getpass.getpass('Login password (hidden): ')
        except (getpass.GetPassWarning, EOFError, OSError):
            raise LoginError('--login requires a terminal with hidden input. Credentials are not accepted as command arguments or files.') from None
    if not username or not password:
        raise LoginError('Both login fields are required.')
    return username, password


def safe_login_origin(url):
    selected = origin(url)
    if selected[0] != 'https':
        try:
            loopback = ipaddress.ip_address(selected[1]).is_loopback
        except ValueError:
            loopback = selected[1] == 'localhost'
        if not loopback:
            raise LoginError('Login requires HTTPS; HTTP is supported only for local loopback test sites.')
    return selected


class LoginSession:
    def __init__(self, target, *, login_url=None, check=None, form=None, user_field=None, password_field=None):
        self.target = target
        self.login_url = login_url or target
        try:
            self.origin = safe_login_origin(target)
            if origin(self.login_url) != self.origin:
                raise LoginError('The login URL must have the target scheme, hostname, and port.')
        except DestinationDenied:
            raise LoginError('Login requires valid HTTP(S) URLs without embedded credentials.') from None
        if not check:
            raise LoginError('--login requires --login-check with a CSS selector visible on signed-in pages.')
        self.check_selector, self.form_selector = check, form
        self.user_field, self.password_field = user_field, password_field
        self.guard = SecretGuard()
        self.cookies = requests.cookies.RequestsCookieJar()
        self.lock = threading.RLock()
        self.active = False
        self.session = capture_session(target, authentication=self)

    def cookie_header(self, url):
        self.guard.check(url)
        if origin(url) != self.origin:
            return ''
        request = requests.Request('GET', url).prepare()
        with self.lock:
            return requests.cookies.get_cookie_header(self.cookies, request) or ''

    def observe_cookies(self):
        with self.lock:
            for cookie in self.cookies:
                self.guard.add(cookie.value)

    def browser_cookies(self, url):
        parsed = SimpleCookie()
        parsed.load(self.cookie_header(url))
        return [{'name': name, 'value': {'type': 'string', 'value': item.value}} for name, item in parsed.items()]

    def receive_browser_cookies(self, url, headers):
        if origin(url) != self.origin:
            return
        for header in headers:
            if header['name'].lower() != 'set-cookie':
                continue
            raw = header['value']
            value = base64.b64decode(raw['value']).decode('latin1') if raw['type'] == 'base64' else raw['value']
            parsed = SimpleCookie()
            parsed.load(value)
            with self.lock:
                for name, item in parsed.items():
                    self.guard.add(item.value)
                    expires = None
                    if item['max-age']:
                        expires = int(time.time()) + int(item['max-age'])
                    elif item['expires']:
                        expires = int(parsedate_to_datetime(item['expires']).timestamp())
                    path = item['path'] or (urlsplit(url).path.rsplit('/', 1)[0] or '/')
                    cookie = requests.cookies.create_cookie(name, item.value, domain=self.origin[1], path=path, secure=bool(item['secure']), expires=expires)
                    if cookie.is_expired():
                        if any(c.name == name and c.domain == cookie.domain and c.path == cookie.path for c in self.cookies):
                            self.cookies.clear(domain=cookie.domain, path=cookie.path, name=name)
                    else:
                        self.cookies.set_cookie(cookie)

    def request(self, method, url, data=None):
        for _ in range(11):
            if origin(url) != self.origin:
                raise LoginError('Login stopped before a redirect or form submission could leave the target origin.')
            self.guard.check(url)
            response = None
            try:
                response = self.session.request(method, url, data=data, timeout=30, allow_redirects=False, stream=True)
                body = bytearray()
                for chunk in response.iter_content(65536):
                    body.extend(chunk)
                    if len(body) > 2_000_000:
                        raise LoginError('The login response exceeds the supported size.')
                status, headers, final_url = response.status_code, dict(response.headers), response.url
            finally:
                if data is not None:
                    data.clear()
                    data = None
                if response is not None:
                    response.request.body = None
                    if response.next is not None:
                        response.next.body = None
                    response.close()
            if status in (307, 308) and method == 'POST':
                raise LoginError('Login refused a redirect that would resend the credential POST.')
            if status in (301, 302, 303, 307, 308):
                url = urljoin(final_url, headers.get('Location', ''))
                method = 'GET'
                continue
            if status >= 400:
                raise LoginError('Login was rejected or the protected page is unavailable.')
            return final_url, bytes(body)
        raise LoginError('Login exceeded the redirect limit.')

    def authenticate(self, prompt=hidden_credentials):
        url, body = self.request('GET', self.login_url)
        soup = BeautifulSoup(body, 'html.parser')
        forms = soup.select(self.form_selector) if self.form_selector else [form for form in soup.find_all('form') if form.select('input[type="password"]')]
        if len(forms) != 1 or forms[0].name != 'form':
            raise LoginError('Select one ordinary password form with --login-form. JavaScript login, SSO, and MFA are not supported.')
        form = forms[0]
        passwords = form.find_all('input', attrs={'name': self.password_field}) if self.password_field else form.select('input[type="password"][name]:not([disabled])')
        users = form.find_all('input', attrs={'name': self.user_field}) if self.user_field else form.select('input[autocomplete="username"][name]:not([disabled])')
        if not users and not self.user_field:
            users = form.select('input[type="email"][name]:not([disabled]),input[type="text"][name]:not([disabled]),input:not([type])[name]:not([disabled])')
        if len(users) != 1 or len(passwords) != 1 or users[0] is passwords[0]:
            raise LoginError('The login fields are ambiguous; supply --login-user-field and --login-password-field names.')
        base = soup.find('base', href=True)
        action = urljoin(urljoin(url, base['href']) if base else url, form.get('action') or url)
        if form.get('method', 'get').lower() != 'post' or origin(action) != self.origin:
            raise LoginError('Login requires a POST form whose action stays on the target origin.')
        if form.get('enctype', 'application/x-www-form-urlencoded').lower() != 'application/x-www-form-urlencoded':
            raise LoginError('Login supports URL-encoded HTML forms only.')
        username = password = None
        fields = {item['name']: item.get('value', '') for item in form.select('input[type="hidden"][name]:not([disabled])')}
        try:
            username, password = prompt()
            if not username or not password:
                raise LoginError('Both login fields are required.')
            self.guard.add(username)
            self.guard.add(password)
            fields[users[0]['name']] = username
            fields[passwords[0]['name']] = password
            self.guard.check(url)
            self.session.headers.update({'Origin': f'{urlsplit(action).scheme}://{urlsplit(action).netloc}', 'Referer': url})
            _, result = self.request('POST', action, fields)
            self.guard.check(result)
            if BeautifulSoup(result, 'html.parser').select('input[type="password"]') or not self.cookies:
                raise LoginError('Login did not establish a cookie session. Check the credentials and login flow.')
            self.active = True
        finally:
            username = password = None
            fields.clear()
            self.session.headers.pop('Origin', None)
            self.session.headers.pop('Referer', None)

    def check_page(self, url, source):
        self.guard.check(url)
        self.guard.check(source)
        if origin(url) == self.origin:
            soup = BeautifulSoup(source, 'html.parser')
            if soup.select('input[type="password"]') or not soup.select(self.check_selector):
                raise LoginError('The signed-in page check failed or the session expired. Capture remains incomplete.')

    def close(self):
        self.active = False
        try:
            self.session.close()
        finally:
            with self.lock:
                self.cookies.clear()
            self.guard.close()


@contextmanager
def login_scope(target, args):
    login = LoginSession(target, login_url=args.login_url, check=args.login_check, form=args.login_form,
                         user_field=args.login_user_field, password_field=args.login_password_field)
    try:
        login.authenticate()
        yield login
    except LoginError:
        raise
    except Exception:
        raise LoginError('Authenticated operation failed. Login details have been discarded; no credential diagnostics were saved.') from None
    finally:
        login.close()
