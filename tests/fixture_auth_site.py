"""Owned cookie-login site with in-memory credentials and request counters."""
from contextlib import contextmanager
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import secrets
import threading
from urllib.parse import parse_qs, urlsplit


@contextmanager
def login_site():
    state = {'username': secrets.token_urlsafe(18), 'password': secrets.token_urlsafe(24),
             'cookie': secrets.token_urlsafe(24), 'csrf': secrets.token_urlsafe(18), 'rotated': secrets.token_urlsafe(24),
             'posts': 0, 'protected_gets': 0, 'protected_heads': 0, 'bad_cookie_requests': 0,
             'action': '/login', 'post_redirect': None, 'post_status': 303,
             'echo': False, 'expired': False, 'hidden_marker': False, 'cookie_headers': 0}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.serve(False)

        def do_HEAD(self):
            self.serve(True)

        def send_body(self, status, body=b'', headers=None, head=False):
            self.send_response(status)
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            if not head:
                self.wfile.write(body)

        def do_POST(self):
            state['posts'] += 1
            data = parse_qs(self.rfile.read(int(self.headers.get('Content-Length', '0'))).decode())
            if urlsplit(self.path).path != '/login' or data.get('account') != [state['username']] or data.get('secret') != [state['password']] or data.get('csrf') != [state['csrf']]:
                self.send_body(401, b'Login rejected')
                return
            if state['echo']:
                self.send_body(200, state['password'].encode(), {'Set-Cookie': 'sid=' + state['cookie'] + '; Path=/; HttpOnly'})
            else:
                self.send_body(state['post_status'], headers={'Set-Cookie': 'sid=' + state['cookie'] + '; Path=/; HttpOnly', 'Location': state['post_redirect'] or '/'})

        def serve(self, head):
            route = urlsplit(self.path).path
            if self.headers.get('Cookie'):
                state['cookie_headers'] += 1
            if route == '/login':
                body = ('<form method="post" action="' + state['action'] + '"><input name="csrf" type="hidden" value="' + state['csrf'] + '"><input name="account" autocomplete="username"><input type="password" name="secret"><button>Sign in</button></form>').encode()
                self.send_body(200, body, {'Content-Type': 'text/html'}, head)
                return
            if route in ('/robots.txt', '/sitemap.xml'):
                self.send_body(404, head=head)
                return
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            signed_in = cookies.get('sid') and cookies['sid'].value == state['cookie'] and not state['expired']
            if not signed_in:
                self.send_body(302, headers={'Location': '/login'}, head=head)
                return
            state['protected_heads' if head else 'protected_gets'] += 1
            if route == '/download.bin':
                self.send_body(200, b'owned protected download', {'Content-Type': 'application/octet-stream'}, head)
                return
            if route == '/site.css':
                self.send_body(200, b'body{font:18px Georgia;margin:40px;color:#172522}a{display:block;margin:24px 0}', {'Content-Type': 'text/css'}, head)
                return
            if route == '/favicon.ico':
                self.send_body(200, b'', {'Content-Type': 'image/x-icon'}, head)
                return
            marker = ' style="display:none"' if state['hidden_marker'] else ''
            body = ('<!doctype html><html><head><meta charset="utf-8"><title>Private archive</title><link rel="stylesheet" href="/site.css"></head><body><h1 id="signed-in"' + marker + '>Private archive</h1><p>Recorded account workspace.</p><a href="/">Home</a><a href="/download.bin">Download</a></body></html>').encode()
            headers = {'Content-Type': 'text/html'}
            if route == '/rotate':
                headers['Set-Cookie'] = 'rotated=' + state['rotated'] + '; Path=/; HttpOnly'
            self.send_body(200, body, headers, head)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/', state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
