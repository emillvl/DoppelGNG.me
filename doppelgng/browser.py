"""Waterfox sessions and browser-protocol event collection."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import queue
import threading
import time

import websocket
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from .dependencies import PROJECT_ROOT
from .authentication import LoginError


class Bidi:
    def __init__(self, url, authentication=None):
        self.socket = websocket.create_connection(url, timeout=2, suppress_origin=True)
        self.events = []
        self.pending = {}
        self.sequence = 0
        self.lock = threading.Lock()
        self.closed = False
        self.authentication = authentication
        self.failure = None
        self.interceptions = queue.Queue()
        self.worker = threading.Thread(target=self._intercept, daemon=True) if authentication else None
        if self.worker:
            self.worker.start()
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()
        try:
            self._subscribe()
        except BaseException:
            self.close()
            raise

    def _subscribe(self):
        events = ['network.beforeRequestSent', 'network.responseCompleted', 'network.fetchError', 'log.entryAdded']
        if self.authentication:
            events.append('network.responseStarted')
        self.command('session.subscribe', {'events': events})
        if self.authentication:
            self.command('network.addIntercept', {'phases': ['beforeRequestSent', 'responseStarted']})
        self.collector = None
        self.body_capture_error = None
        try:
            result = self.command('network.addDataCollector', {'dataTypes': ['response'], 'maxEncodedDataSize': 100_000_000})
            self.collector = result['collector']
        except RuntimeError as error:
            self.body_capture_error = str(error)

    def _read(self):
        while not self.closed:
            try:
                message = json.loads(self.socket.recv())
                if 'id' in message:
                    with self.lock:
                        waiter = self.pending.get(message['id'])
                    if waiter:
                        waiter.put(message)
                else:
                    if self.authentication:
                        if message.get('params', {}).get('isBlocked'):
                            self.interceptions.put(message)
                        message = self._clean_event(message)
                    self.events.append(message)
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                if not self.closed:
                    self.events.append({'method': 'recorder.error', 'params': {'message': 'Browser event connection ended'}})
                return

    def _clean_event(self, message):
        cleaned = json.loads(json.dumps(message))
        for field in ('request', 'response'):
            item = cleaned.get('params', {}).get(field, {})
            for name in ('cookies', 'body', 'postData'):
                item.pop(name, None)
            item['headers'] = [header for header in item.get('headers', []) if header['name'].lower() not in ('cookie', 'set-cookie', 'authorization', 'proxy-authorization')]
        try:
            self.authentication.guard.check(json.dumps(cleaned))
            return cleaned
        except LoginError as error:
            self.failure = error
            return {'method': 'recorder.error', 'params': {'message': 'Login data was excluded from browser evidence'}}

    def _intercept(self):
        while not self.closed:
            message = self.interceptions.get()
            if message is None:
                return
            request = message['params']['request']
            identifier = request['request']
            try:
                url = request['url']
                self.authentication.guard.check(url)
                if self.failure:
                    raise self.failure
                if message['method'] == 'network.beforeRequestSent':
                    if request['method'] not in ('GET', 'HEAD'):
                        raise LoginError('Authenticated capture permits browser GET and HEAD requests only.')
                    headers = [header for header in request.get('headers', []) if header['name'].lower() not in ('cookie', 'authorization', 'proxy-authorization')]
                    self.command('network.continueRequest', {'request': identifier, 'headers': headers, 'cookies': self.authentication.browser_cookies(url)})
                elif message['method'] == 'network.responseStarted':
                    headers = message['params']['response'].get('headers', [])
                    self.authentication.receive_browser_cookies(url, headers)
                    self.command('network.continueResponse', {'request': identifier, 'headers': [header for header in headers if header['name'].lower() != 'set-cookie']})
            except Exception:
                self.failure = LoginError('Authenticated browser request was blocked or session interception failed. No login diagnostics were saved.')
                try:
                    self.command('network.failRequest', {'request': identifier})
                except Exception:
                    pass

    def command(self, method, params, timeout=20):
        with self.lock:
            self.sequence += 1
            number = self.sequence
            waiter = queue.Queue()
            self.pending[number] = waiter
        try:
            self.socket.send(json.dumps({'id': number, 'method': method, 'params': params}))
            response = waiter.get(timeout=timeout)
            if response.get('type') == 'error':
                raise RuntimeError(f'{method}: {response.get("error")}: {response.get("message")}')
            return response.get('result', {})
        except queue.Empty as error:
            raise RuntimeError(f'Browser protocol timed out: {method}') from error
        finally:
            with self.lock:
                self.pending.pop(number, None)

    def body(self, request):
        if self.collector is None:
            return None
        result = self.command('network.getData', {'dataType': 'response', 'request': request, 'collector': self.collector})
        value = result['bytes']
        return base64.b64decode(value['value']) if value['type'] == 'base64' else value['value'].encode('utf-8')

    def close(self):
        self.closed = True
        self.interceptions.put(None)
        with self.lock:
            for waiter in self.pending.values():
                waiter.put({'type': 'error', 'message': 'Browser session closed'})
        self.socket.close()
        self.thread.join(timeout=3)
        if self.worker:
            self.worker.join(timeout=3)
        self.events.clear()
        while True:
            try:
                self.interceptions.get_nowait()
            except queue.Empty:
                break
        with self.lock:
            self.pending.clear()


class Waterfox:
    def __init__(self, artifacts: Path, *, headless=True, timeout=40, authentication=None):
        artifacts.mkdir(parents=True, exist_ok=True)
        binary = Path(os.environ.get('DOPPELGNG_WATERFOX', PROJECT_ROOT / '.tools/waterfox/core/waterfox.exe')).resolve()
        driver = Path(os.environ.get('DOPPELGNG_GECKODRIVER', PROJECT_ROOT / '.tools/geckodriver.exe')).resolve()
        if not binary.is_file() or not driver.is_file():
            raise RuntimeError('Waterfox runtime is missing. Run npm run setup or set DOPPELGNG_WATERFOX and DOPPELGNG_GECKODRIVER.')
        options = Options()
        options.binary_location = str(binary)
        if headless:
            options.add_argument('-headless')
        options.set_capability('webSocketUrl', True)
        options.set_preference('browser.shell.checkDefaultBrowser', False)
        # Waterfox otherwise creates a Private Browsing shortcut even in ZIP builds.
        options.set_preference('browser.privateWindowSeparation.enabled', False)
        self.authentication = authentication
        if authentication:
            for name, value in {'browser.privatebrowsing.autostart': True, 'browser.cache.disk.enable': False,
                                'browser.cache.offline.enable': False, 'signon.rememberSignons': False,
                                'browser.sessionstore.resume_from_crash': False}.items():
                options.set_preference(name, value)
        self.driver = webdriver.Firefox(options=options, service=Service(str(driver), log_output=os.devnull if authentication else str(artifacts / 'geckodriver.log')))
        self.driver.set_page_load_timeout(timeout)
        self.driver.set_script_timeout(timeout)
        try:
            self.bidi = Bidi(self.driver.capabilities['webSocketUrl'], authentication) if authentication else Bidi(self.driver.capabilities['webSocketUrl'])
        except BaseException:
            self.driver.quit()
            raise
        self.timeout = timeout
        self.identity = {'binary': str(binary), 'capabilities': self.driver.capabilities, 'body_capture_error': self.bidi.body_capture_error}

    def navigate(self, url):
        self.driver.get(url)
        self.settle()

    def viewport(self, width, height):
        # Native Windows window widths cannot reach the mobile viewport size.
        context = self.bidi.command('browsingContext.getTree', {})['contexts'][0]['context']
        self.bidi.command('browsingContext.setViewport', {'context': context, 'viewport': {'width': width, 'height': height}, 'devicePixelRatio': 1})
        if self.driver.execute_script('return [innerWidth, innerHeight]') == [width, height]:
            return
        self.driver.set_window_rect(width=width, height=height)
        for _ in range(3):
            actual = self.driver.execute_script('return [innerWidth, innerHeight]')
            if actual == [width, height]:
                return
            rect = self.driver.get_window_rect()
            self.driver.set_window_rect(width=rect['width'] + width-actual[0], height=rect['height'] + height-actual[1])
        raise RuntimeError(f'Could not establish the requested content viewport: expected {[width, height]}, measured {actual}')

    def settle(self):
        WebDriverWait(self.driver, self.timeout).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        self.driver.execute_async_script('const done=arguments[arguments.length-1]; document.fonts.ready.then(()=>done(true),()=>done(false));')
        time.sleep(0.4)
        if self.authentication:
            if self.bidi.failure:
                raise self.bidi.failure
            self.authentication.check_page(self.driver.current_url, self.driver.page_source)
            from .network import origin
            if origin(self.driver.current_url) == self.authentication.origin:
                visible = any(element.is_displayed() for element in self.driver.find_elements(By.CSS_SELECTOR, self.authentication.check_selector))
                if not visible:
                    raise LoginError('The signed-in page selector is not visible. Capture remains incomplete.')

    def source(self, url, request_headers=None):
        result = self.driver.execute_async_script('''
            const url=arguments[0], headers=arguments[1], done=arguments[arguments.length-1];
            fetch(url, {cache:'no-store',headers}).then(async r=>{
                const bytes=new Uint8Array(await r.arrayBuffer()); let s='';
                for(let i=0;i<bytes.length;i+=32768) s+=String.fromCharCode(...bytes.subarray(i,i+32768));
                done({status:r.status,url:r.url,headers:Object.fromEntries(r.headers),base64:btoa(s)});
            }).catch(e=>done({error:String(e)}));
        ''', url, request_headers or {})
        if 'error' in result or result.get('status', 500) >= 400:
            if self.authentication:
                raise LoginError('Authenticated resource retrieval failed or the session expired.')
            raise RuntimeError(f'Waterfox source retrieval failed for {url}: {result}')
        body = base64.b64decode(result.pop('base64'))
        if self.authentication:
            self.authentication.guard.check(result.get('url', url))
            self.authentication.guard.check(body)
        return result, body

    def close(self):
        try:
            self.bidi.close()
        finally:
            self.driver.quit()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
