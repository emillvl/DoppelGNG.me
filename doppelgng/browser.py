"""Headless Waterfox and a lossless browser-protocol event recorder."""
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
from selenium.webdriver.support.ui import WebDriverWait


class Bidi:
    def __init__(self, url):
        self.socket = websocket.create_connection(url, timeout=2, suppress_origin=True)
        self.events = []
        self.pending = {}
        self.sequence = 0
        self.lock = threading.Lock()
        self.closed = False
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()
        self.command('session.subscribe', {'events': ['network.beforeRequestSent', 'network.responseCompleted', 'network.fetchError', 'log.entryAdded']})
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
                    self.events.append(message)
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                if not self.closed:
                    self.events.append({'method': 'recorder.error', 'params': {'message': 'Browser event connection ended'}})
                return

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
        self.socket.close()
        self.thread.join(timeout=3)


class Waterfox:
    def __init__(self, artifacts: Path, *, headless=True, timeout=40):
        artifacts.mkdir(parents=True, exist_ok=True)
        binary = Path(os.environ.get('DOPPELGNG_WATERFOX', '.tools/waterfox/core/waterfox.exe')).resolve()
        driver = Path(os.environ.get('DOPPELGNG_GECKODRIVER', '.tools/geckodriver.exe')).resolve()
        if not binary.is_file() or not driver.is_file():
            raise RuntimeError('Waterfox runtime is missing. Run npm run setup or set DOPPELGNG_WATERFOX and DOPPELGNG_GECKODRIVER.')
        options = Options()
        options.binary_location = str(binary)
        if headless:
            options.add_argument('-headless')
        options.set_capability('webSocketUrl', True)
        options.set_preference('browser.shell.checkDefaultBrowser', False)
        self.driver = webdriver.Firefox(options=options, service=Service(str(driver), log_output=str(artifacts / 'geckodriver.log')))
        self.driver.set_page_load_timeout(timeout)
        self.driver.set_script_timeout(timeout)
        try:
            self.bidi = Bidi(self.driver.capabilities['webSocketUrl'])
        except BaseException:
            self.driver.quit()
            raise
        self.timeout = timeout
        self.identity = {'binary': str(binary), 'capabilities': self.driver.capabilities, 'body_capture_error': self.bidi.body_capture_error}

    def navigate(self, url):
        self.driver.get(url)
        self.settle()

    def viewport(self, width, height):
        # Browser-protocol viewport emulation avoids the native Windows minimum
        # window width, which otherwise makes real mobile-width checks fail.
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
            raise RuntimeError(f'Waterfox source retrieval failed for {url}: {result}')
        return result, base64.b64decode(result.pop('base64'))

    def close(self):
        self.bidi.close()
        self.driver.quit()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
