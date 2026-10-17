"""Strict page gates layered on the existing crawler's discovery loop."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import time
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
import requests

from .archive import Archive, ExtractionFailure, sanitized_events
from .browser import Waterfox
from .crawler import load_crawler, crawler_identity
from .discovery import sitemap_pages
from .reconstruct import reconstruct, public_url
from .resources import html_process
from .storage import Store, atomic_json, now
from .validation import record_baseline, local_validate, interaction_check


class Preview:
    def __init__(self, store, port=4173):
        self.store, self.port = store, port
        self.process = None
        self.origin = f'http://127.0.0.1:{port}'

    def __enter__(self):
        log = (self.store.root / 'artifacts' / 'server.log').open('a', encoding='utf-8')
        self.process = subprocess.Popen(['node', str(Path(__file__).resolve().parents[1] / 'server.mjs'), '--manifest', str(self.store.path), '--port', str(self.port)], stdout=log, stderr=log)
        log.close()
        for _ in range(80):
            if self.process.poll() is not None:
                raise RuntimeError(f'Local server could not start; check {self.store.root / "artifacts/server.log"}')
            try:
                if requests.get(self.origin + '/__doppelgng__/health', timeout=0.5).status_code == 200:
                    return self
            except requests.RequestException:
                pass
            time.sleep(0.1)
        self.__exit__()
        raise RuntimeError('Local preview server did not become ready')

    def __exit__(self, *_):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


def build_adapter(module, store, browser, preview, *, viewports, allowed_ratio, scenarios):
    class ReconstructionCrawler(module.WebCrawler):
        def __init__(self):
            super().__init__(store.data['target'], output_dir=str(store.root / 'crawler'), delay=0.3, checkpoint_every=1, allow_selenium=False, respect_robots=True, resume=True)
            self.archive = Archive(store, browser)

        def _load_robots(self):
            super()._load_robots()
            pages, observations = sitemap_pages(self)
            store.data['discovery'] = {'sitemaps': observations, 'sitemap_pages': pages}
            for url in pages:
                store.page(url)
            store.save()

        def _same_domain(self, url):
            # Preserve the inspected crawler's host policy, narrowed to the
            # authorized origin so alternate ports cannot expand crawl scope.
            return super()._same_domain(url) and (urlsplit(url).scheme, urlsplit(url).netloc) == (urlsplit(self.base_url).scheme, urlsplit(self.base_url).netloc)

        def _prepare_queue(self):
            super()._prepare_queue()
            # The original crawler visits before fetching. Our manifest, rather
            # than that visited flag, determines what is safe to resume.
            pending = []
            for url, page in store.data['pages'].items():
                if page['state'] not in ('validated', 'complete', 'download_validated') or store.verify(page['resources']):
                    self.visited.discard(url)
                    pending.append(url)
                else:
                    self.visited.add(url)
            # The inspected crawler uses a stack. Resume unfinished pages in
            # discovery order so a failed current page is retried first.
            if pending:
                self.stack = list(reversed(list(dict.fromkeys([*pending, *reversed(self.stack)]))))
            if not self.stack and not store.data['pages']:
                self.stack = [self.base_url]

        def _can_fetch(self, url):
            allowed = super()._can_fetch(url)
            if not allowed:
                page = store.page(url)
                page['state'] = 'blocked'
                page['reason'] = 'robots.txt disallows this URL'
                store.save()
                raise ExtractionFailure(f'robots.txt blocks discovered URL: {url}')
            return allowed

        def _fetch(self, url):
            page = store.page(url)
            if page['state'] in ('validated', 'complete', 'download_validated') and not store.verify(page['resources']):
                return module.FetchResult(links=page['links'])
            page['state'] = 'extracting'
            page.pop('error', None)
            store.save()
            print(f'[extract] {url}', flush=True)
            start = len(browser.bidi.events)
            try:
                probe = self.archive.session.head(url, timeout=30, allow_redirects=True)
                probe.raise_for_status()
                mime = probe.headers.get('content-type', '').lower()
                if mime and 'html' not in mime and 'xhtml' not in mime:
                    record = self.archive.retrieve(url)
                    record['kind'] = 'download'
                    page['kind'] = 'download'
                    page['resources'] = [url]
                    page['links'] = []
                    reconstruct(store, [url])
                    local_url = preview.origin + public_url(url, store.data['target'])
                    response = requests.get(local_url, timeout=60)
                    passed = response.status_code == record['status'] and response.content == (store.root / record['raw']).read_bytes()
                    page['validation'] = {'passed': passed, 'bytes_verified': len(response.content), 'checked_at': now(), 'applicable': 'download byte equality and local HTTP loading'}
                    page['state'] = 'download_validated' if passed else 'failed'
                    store.save()
                    if not passed:
                        raise ExtractionFailure(f'Download replay differs: {url}')
                    return module.FetchResult()
                browser.navigate(url)
                meta, body = browser.source(browser.driver.current_url)
                record = store.resource(url, body, headers=meta['headers'], source='waterfox-fetch', kind='page')
                page['kind'] = 'page'
                page['final_url'] = meta['url']
                directory = store.artifact_dir(url)
                original = body.decode('utf-8-sig')
                observed = self.archive.ingest(browser.bidi.events[start:])
                def flush_responses():
                    observed.extend(self.archive.ingest(browser.bidi.events[start:]))
                baselines = record_baseline(browser, url, directory, viewports, flush_responses)
                rendered = browser.driver.page_source
                (directory / 'rendered.html').write_text(rendered, encoding='utf-8')
                page['title'] = browser.driver.title
                links = self._extract_links(BeautifulSoup(original, 'html.parser'), meta['url'])
                links += self._extract_links(BeautifulSoup(rendered, 'html.parser'), meta['url'])
                links = list(dict.fromkeys(links))
                for link in links:
                    store.page(link)
                page['links'] = links
                dom_dependencies, _ = html_process(rendered, meta['url'])
                observed.extend(self.archive.ingest(browser.bidi.events[start:]))
                page['resources'] = self.archive.closure([url, *dom_dependencies, *observed])
                page['state'] = 'extracted'
                (directory / 'network-original.json').write_text(json.dumps(sanitized_events(browser.bidi.events[start:]), ensure_ascii=False, indent=2), encoding='utf-8')
                store.save()
                reconstruct(store, page['resources'])
                broken = store.verify(page['resources'])
                if broken:
                    raise ExtractionFailure(f'Reconstruction integrity failed: {broken}')
                page['state'] = 'reconstructed'
                store.save()
                print(f'[validate] {url} ({len(page["resources"])} resources)', flush=True)
                local_url = preview.origin + public_url(url, store.data['target'])
                validation = local_validate(browser, url, local_url, directory, baselines, allowed_ratio=allowed_ratio)
                def capture_interaction_resources(events):
                    added = self.archive.closure(self.archive.ingest(events))
                    page['resources'] = list(dict.fromkeys([*page['resources'], *added]))
                    reconstruct(store, added)
                actions = interaction_check(browser, url, local_url, directory, scenarios.get(urlsplit(url).path, []), capture_interaction_resources)
                validation['interactions'] = actions
                validation['passed'] = validation['passed'] and all(action['passed'] for action in actions)
                if any(not action['passed'] for action in actions):
                    validation['errors'].append('Interaction scenarios failed or interactive controls remain untested')
                page['validation'] = validation
                page['state'] = 'validated' if validation['passed'] else 'failed'
                if not validation['passed']:
                    raise ExtractionFailure(f'Page validation failed: {url}: {validation["errors"]}')
                print(f'[passed] {url}', flush=True)
                store.save()
                return module.FetchResult(links=links, html=original)
            except BaseException as error:
                page['state'] = 'failed'
                page['error'] = str(error)
                store.data['status'] = 'incomplete'
                store.save()
                raise

    return ReconstructionCrawler()


def navigation_validation(store, browser, preview):
    checks = []
    for url, page in list(store.data['pages'].items()):
        if page.get('kind') != 'page' or page['state'] not in ('validated', 'complete'):
            continue
        local_url = preview.origin + public_url(url, store.data['target'])
        browser.viewport(1440, 900)
        browser.navigate(local_url)
        # Verify every internal link as an HTTP route. Click each page-to-page
        # edge separately to exercise client-side routers as well as refresh.
        anchors = browser.driver.execute_script('return Array.from(document.querySelectorAll("a[href]"),a=>({href:a.href,text:a.innerText}));')
        unique = list(dict.fromkeys(item['href'] for item in anchors if item['href'].startswith(preview.origin + '/')))
        for destination in unique:
            parts = urlsplit(destination)
            source_url = store.data['target'].rstrip('/') + parts.path
            target_page = next((p for u, p in store.data['pages'].items() if urlsplit(u).path.rstrip('/') == parts.path.rstrip('/')), None)
            response = requests.get(destination.split('#')[0], timeout=60)
            result = {'from': url, 'to': destination, 'http_status': response.status_code, 'passed': response.status_code == 200}
            if parts.fragment:
                browser.navigate(local_url)
                anchor = browser.driver.execute_script('return Array.from(document.querySelectorAll("a[href]")).find(a=>a.href===arguments[0]);', destination)
                if anchor:
                    browser.driver.execute_script('arguments[0].scrollIntoView({block:"center"})', anchor)
                    try:
                        anchor.click()
                        browser.settle()
                        time.sleep(0.7)
                        result['anchor_exists'] = browser.driver.execute_script('return !!document.getElementById(arguments[0])', parts.fragment)
                        result['passed'] &= result['anchor_exists']
                    except Exception as error:
                        result['passed'] = False
                        result['error'] = str(error)
            elif target_page and target_page.get('kind') == 'page':
                browser.navigate(local_url)
                anchor = browser.driver.execute_script('return Array.from(document.querySelectorAll("a[href]")).find(a=>a.href===arguments[0]);', destination)
                try:
                    browser.driver.execute_script('arguments[0].scrollIntoView({block:"center"})', anchor)
                    time.sleep(0.5)
                    anchor.click()
                    browser.settle()
                    result['rendered_title'] = browser.driver.title
                    result['passed'] &= browser.driver.title == target_page.get('title')
                    result['route_reached'] = urlsplit(browser.driver.current_url).path.rstrip('/') == parts.path.rstrip('/')
                    result['passed'] &= result['route_reached']
                    browser.driver.refresh()
                    browser.settle()
                    result['refresh_passed'] = browser.driver.title == target_page.get('title')
                    result['passed'] &= result['refresh_passed']
                except Exception as error:
                    result['passed'] = False
                    result['error'] = str(error)
            checks.append(result)
    store.data['integration'] = {'checked_at': now(), 'passed': all(check['passed'] for check in checks), 'links': checks}
    for page in store.data['pages'].values():
        if page['state'] in ('validated', 'download_validated') and store.data['integration']['passed']:
            page['state'] = 'complete'
    store.data['status'] = 'complete' if store.data['pages'] and all(p['state'] == 'complete' for p in store.data['pages'].values()) and store.data['integration']['passed'] else 'incomplete'
    store.save()
    return store.data['integration']


def capture(target, crawler_directory, output, *, port=4173, viewports=None, allowed_ratio=0.01, scenarios=None):
    module = load_crawler(crawler_directory)
    target = module.WebCrawler._normalize_url(target)
    store = Store(output, target, crawler_identity(crawler_directory))
    store.data['policy'] = {'page_host': urlsplit(target).netloc, 'respect_robots': True, 'volatile_static_query': ['_rsc'], 'allowed_visual_ratio': allowed_ratio, 'viewports': viewports or [[1440, 900], [390, 844]]}
    store.data['status'] = 'running'
    store.data['scenarios'] = scenarios or store.data.get('scenarios', {})
    # Each output is a standalone, buildless npm project as well as a checkpoint.
    # No target-specific component code is generated.
    (store.root / 'package.json').write_text(json.dumps({'name': 'doppelgng-reconstruction', 'private': True, 'type': 'module', 'scripts': {'dev': 'node server.mjs --manifest manifest.json'}}, indent=2), encoding='utf-8')
    shutil.copyfile(Path(__file__).resolve().parents[1] / 'server.mjs', store.root / 'server.mjs')
    store.save()
    atomic_json(Path('.doppelgng/current.json'), {'manifest': str(store.path)})
    with Preview(store, port) as preview, Waterfox(store.root / 'artifacts') as browser:
        store.data['browser'] = browser.identity
        adapter = build_adapter(module, store, browser, preview, viewports=store.data['policy']['viewports'], allowed_ratio=allowed_ratio, scenarios=store.data['scenarios'])
        adapter.crawl()
        navigation_validation(store, browser, preview)
    print(json.dumps({'status': store.data['status'], 'pages': len(store.data['pages']), 'resources': len(store.data['resources']), 'manifest': str(store.path)}, indent=2), flush=True)
    return store
