"""Collect browser-observed response bodies and close static dependency graphs."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.parse import urlsplit

import requests

from .resources import absolute, process
from .network import DestinationPolicy, capture_session, origin


def headers(values):
    result = {}
    for item in values:
        value = item['value']
        result[item['name'].lower()] = base64.b64decode(value['value']).decode('latin1') if value['type'] == 'base64' else value['value']
    return result


def sanitized_events(events):
    result = json.loads(json.dumps(events))
    for event in result:
        params = event.get('params', {})
        for field in ('request', 'response'):
            obj = params.get(field, {})
            obj.pop('cookies', None)
            obj['headers'] = [h for h in obj.get('headers', []) if h['name'].lower() not in ('cookie', 'set-cookie', 'authorization', 'proxy-authorization')]
    return result


class ExtractionFailure(RuntimeError):
    pass


class Archive:
    def __init__(self, store, browser, *, max_bytes=256_000_000):
        self.store = store
        self.browser = browser
        self.max_bytes = max_bytes
        authorized = store.data.get('policy', {}).get('authorized_resource_origins', [])
        self.policy = DestinationPolicy(store.data['target'], authorized)
        self.session = capture_session(store.data['target'], authorized)
        self.session.headers['User-Agent'] = browser.driver.execute_script('return navigator.userAgent')
        self.seen_requests = set()

    def ingest(self, events):
        collected = []
        for event in events:
            if event.get('method') != 'network.responseCompleted':
                continue
            params = event['params']
            request, response = params['request'], params['response']
            url = absolute(response['url'], self.store.data['target'])
            identifier = request['request']
            if not url or identifier in self.seen_requests or request['method'] not in ('GET', 'HEAD'):
                continue
            self.policy.address(url)
            self.seen_requests.add(identifier)
            if not 200 <= response['status'] < 300:
                continue
            if request['method'] == 'HEAD':
                # Router HEAD probes can reference documents not yet queued as pages.
                if origin(url) == origin(self.store.data['target']):
                    record = self.retrieve(url)
                    record['head_observed'] = True
                    collected.append(url)
                continue
            request_headers = headers(request.get('headers', []))
            safe_headers = {k: v for k, v in request_headers.items() if k in ('accept', 'rsc', 'next-router-prefetch', 'next-router-segment-prefetch')}
            try:
                body = self.browser.bidi.body(identifier)
            except RuntimeError as error:
                if 'no such network data' not in str(error):
                    raise
                # Evicted bodies need a refetch with the observed representation headers.
                if url in self.store.data['resources'] and self.store.intact(self.store.data['resources'][url]):
                    collected.append(url)
                    continue
                meta, body = self.browser.source(url, safe_headers)
                self.policy.address(meta['url'])
                if len(body) > self.max_bytes:
                    raise ExtractionFailure(f'Resource exceeds configured byte limit: {url}')
                record = self.store.resource(url, body, status=meta['status'], headers=meta['headers'], source='waterfox-refetch-evicted-protocol-body', request_headers=safe_headers)
                record['final_url'] = meta['url']
                collected.append(url)
                continue
            if body is None:
                raise ExtractionFailure('This Waterfox version cannot archive response bodies; upgrade the private runtime')
            # Empty speculative/cache entries must not replace stored document bodies.
            if not body and response.get('bodySize', 0) != 0:
                continue
            if not body and url in self.store.data['resources']:
                collected.append(url)
                continue
            if len(body) > self.max_bytes:
                raise ExtractionFailure(f'Resource exceeds configured byte limit: {url}')
            previous = self.store.data['resources'].get(url)
            kind = previous['kind'] if previous else 'resource'
            observed_headers = headers(response.get('headers', []))
            if (previous and previous['sha256'] == __import__('hashlib').sha256(body).hexdigest()
                    and previous['status'] == response['status']
                    and previous['content_type'] == observed_headers.get('content-type', 'application/octet-stream')
                    and previous.get('headers', {}).get('content-disposition') == observed_headers.get('content-disposition')):
                collected.append(url)
                continue
            self.store.resource(url, body, status=response['status'], headers=observed_headers, source='waterfox-bidi', kind=kind, request_headers=safe_headers)
            collected.append(url)
        return list(dict.fromkeys(collected))

    def retrieve(self, url, *, required=True):
        existing = self.store.data['resources'].get(url)
        if existing and self.store.intact(existing) and (existing['bytes'] or existing.get('empty_verified')):
            return existing
        self.policy.address(url)
        try:
            meta, body = self.browser.source(url)
            source = 'waterfox-fetch'
        except Exception as browser_error:
            # CORS may block browser fetch; record native refetch provenance separately.
            try:
                with self.session.get(url, timeout=40, stream=True, allow_redirects=True) as response:
                    response.raise_for_status()
                    chunks = []
                    count = 0
                    for chunk in response.iter_content(1024 * 1024):
                        count += len(chunk)
                        if count > self.max_bytes:
                            raise ExtractionFailure(f'Resource exceeds configured byte limit: {url}')
                        chunks.append(chunk)
                    body = b''.join(chunks)
                    meta = {'status': response.status_code, 'url': response.url, 'headers': dict(response.headers)}
                    source = 'http-refetch-after-browser-cors-or-fetch-error'
            except Exception as error:
                raise ExtractionFailure(f'Cannot retrieve {url}: browser={browser_error}; refetch={error}') from error
        if len(body) > self.max_bytes:
            raise ExtractionFailure(f'Resource exceeds configured byte limit: {url}')
        self.policy.address(meta['url'])
        record = self.store.resource(url, body, status=meta['status'], headers=meta['headers'], source=source)
        record['final_url'] = meta['url']
        record['empty_verified'] = not bool(body)
        return record

    def closure(self, seeds):
        queue = list(dict.fromkeys(seeds))
        result = []
        visited = set()
        while queue:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            record = self.retrieve(url)
            result.append(url)
            mime = record['content_type'].lower()
            if any(token in mime for token in ('html', 'css', 'javascript')) or urlsplit(url).path.endswith(('.js', '.mjs')):
                raw = (self.store.root / record['raw']).read_bytes()
                text = raw.decode('utf-8-sig')
                dependencies, _ = process(text, mime, record.get('final_url', url))
                record['dependencies'] = dependencies
                queue.extend(dependencies)
        # Check raw bytes here; reconstruction repairs local copies afterward.
        broken = [url for url in result if not self.store.intact(self.store.data['resources'][url])]
        if broken:
            raise ExtractionFailure(f'Integrity check failed: {broken}')
        return result
