"""Capture pages, validate local replay, and check navigation."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import time
from urllib.parse import parse_qsl, urlsplit
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
import requests

from .archive import Archive, ExtractionFailure, sanitized_events
from .browser import Waterfox
from .crawler import load_crawler, crawler_identity
from .discovery import sitemap_pages
from .network import origin
from .reconstruct import reconstruct, public_url
from .resources import html_process
from .storage import Store, atomic_json, incomplete_on_failure, now
from .validation import record_baseline, local_validate, interaction_check, snapshot, scroll


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


def build_adapter(module, store, browser, preview, *, viewports, allowed_ratio, scenarios, respect_robots=True, checkpoint_every=1, quiet=False):
    class ReconstructionCrawler(module.WebCrawler):
        def __init__(self):
            super().__init__(store.data['target'], output_dir=str(store.root / 'crawler'), delay=0.3, checkpoint_every=checkpoint_every, allow_selenium=False, respect_robots=respect_robots, resume=True, quiet=quiet)
            self.archive = Archive(store, browser)
            self.authorized_resource_origins = store.data.get('policy', {}).get('authorized_resource_origins', [])
            self.authentication = store.authentication

        def _print_summary(self):
            # The manifest records completion after replay validation.
            pass

        def _say(self, message=''):
            # Suppress upstream output while retaining its checkpoint behavior.
            pass

        def _progress(self, message):
            if not self.quiet:
                print(f'[doppelgng.me] {message}', flush=True)

        def _load_robots(self):
            self._robots = None
            if self.respect_robots:
                parts = urlsplit(self.base_url)
                robots_url = f'{parts.scheme}://{parts.netloc}/robots.txt'
                try:
                    with self.archive.session.get(robots_url, headers=self._HEADERS, timeout=self.timeout) as response:
                        if response.status_code == 200:
                            parser = RobotFileParser(robots_url)
                            parser.parse(response.text.splitlines())
                            self._robots = parser
                except requests.RequestException:
                    # The upstream crawler proceeds when robots.txt is unavailable.
                    self._robots = None
            pages, observations = sitemap_pages(self)
            store.data['discovery'] = {'sitemaps': observations, 'sitemap_pages': pages}
            for url in pages:
                store.page(url)
            store.save()

        def _same_domain(self, url):
            # Alternate schemes and ports are outside the authorized page origin.
            return super()._same_domain(url) and origin(url) == origin(self.base_url)

        def _prepare_queue(self):
            super()._prepare_queue()
            # Upstream marks visits before fetching; only verified pages can resume.
            pending = []
            for url, page in store.data['pages'].items():
                if page['state'] not in ('validated', 'complete', 'download_validated') or store.verify(page['resources']):
                    self.visited.discard(url)
                    pending.append(url)
                else:
                    self.visited.add(url)
            # The configured crawler may use a FIFO deque or a LIFO list.
            fifo = hasattr(self.stack, 'popleft')
            existing = list(self.stack) if fifo else list(reversed(self.stack))
            if pending:
                ordered = list(dict.fromkeys([*pending, *existing]))
                self.stack = type(self.stack)(ordered) if fifo else list(reversed(ordered))
                if hasattr(self, 'queued'):
                    self.queued = set(ordered)
            if not self.stack and not store.data['pages']:
                self.stack.append(self.base_url)
                if hasattr(self, 'queued'):
                    self.queued.add(self.base_url)

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
            self._progress(f'Extracting {url}')
            start = len(browser.bidi.events)
            try:
                probe = self.archive.session.head(url, timeout=30, allow_redirects=True)
                if probe.status_code in (405, 501):
                    probe.close()
                    probe = self.archive.session.get(url, timeout=30, stream=True, allow_redirects=True)
                try:
                    probe.raise_for_status()
                    mime = probe.headers.get('content-type', '').lower()
                finally:
                    probe.close()
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
                self.archive.policy.address(meta['url'])
                record = store.resource(url, body, headers=meta['headers'], source='waterfox-fetch', kind='page')
                record['final_url'] = meta['url']
                page['kind'] = 'page'
                page['final_url'] = meta['url']
                directory = store.artifact_dir(url)
                original = body.decode('utf-8-sig')
                observed = self.archive.ingest(browser.bidi.events[start:])
                def flush_responses():
                    observed.extend(self.archive.ingest(browser.bidi.events[start:]))
                baselines = record_baseline(browser, url, directory, viewports, flush_responses)
                rendered = browser.driver.page_source
                if authentication := store.authentication:
                    authentication.guard.check(rendered)
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
                try:
                    page['resources'] = self.archive.closure([url, *dom_dependencies, *observed])
                finally:
                    # Keep request evidence even when dependency extraction fails.
                    (directory / 'network-original.json').write_text(json.dumps(sanitized_events(browser.bidi.events[start:]), ensure_ascii=False, indent=2), encoding='utf-8')
                page['state'] = 'extracted'
                store.save()
                reconstruct(store, page['resources'])
                broken = store.verify(page['resources'])
                if broken:
                    raise ExtractionFailure(f'Reconstruction integrity failed: {broken}')
                page['state'] = 'reconstructed'
                store.save()
                self._progress(f'Validating {url} ({len(page["resources"])} resources)')
                local_url = preview.origin + public_url(url, store.data['target'])
                validation = local_validate(browser, url, local_url, directory, baselines, allowed_ratio=allowed_ratio)
                def capture_interaction_resources(events):
                    added = self.archive.closure(self.archive.ingest(events))
                    page['resources'] = list(dict.fromkeys([*page['resources'], *added]))
                    expanded_links = self._extract_links(BeautifulSoup(browser.driver.page_source, 'html.parser'), browser.driver.current_url)
                    links.extend(link for link in expanded_links if link not in links)
                    page['links'] = links
                    for link in expanded_links:
                        store.page(link)
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
                self._progress(f'Verified {url}')
                store.save()
                return module.FetchResult(links=links, html=original)
            except BaseException as error:
                page['state'] = 'failed'
                page['error'] = store.error_message(error)
                store.data['status'] = 'incomplete'
                store.save()
                raise

    return ReconstructionCrawler()


def navigation_validation(store, browser, preview, only_edges=None, *, quiet=False):
    def route_key(value):
        parts = urlsplit(value)
        query = sorted(parse_qsl(parts.query, keep_blank_values=True), key=lambda item: item[0])
        return parts.path.rstrip('/') or '/', query

    def reached_route(destination):
        current = urlsplit(browser.driver.current_url)
        local = urlsplit(preview.origin)
        return (current.scheme, current.netloc) == (local.scheme, local.netloc) and route_key(browser.driver.current_url) == route_key(destination)

    def link_for(destination):
        def locate():
            return browser.driver.execute_script('return Array.from(document.querySelectorAll("a[href]")).find(a=>a.href===arguments[0]&&!a.closest("[inert]")&&getComputedStyle(a).display!=="none"&&getComputedStyle(a).visibility!=="hidden");', destination)
        anchor = locate()
        if anchor is None:
            # Scroll-activated navigation is intentionally inert at page entry.
            scroll(browser, 0.5)
            anchor = locate()
        if anchor is None:
            # Some links exist only after a verified disclosure action.
            for interaction in page.get('validation', {}).get('interactions', []):
                scenario = interaction.get('scenario')
                if not interaction.get('passed') or not scenario:
                    continue
                from selenium.webdriver.common.by import By
                element = browser.driver.find_element(By.CSS_SELECTOR, scenario['selector'])
                if scenario['action'] == 'hover':
                    from selenium.webdriver import ActionChains
                    ActionChains(browser.driver).move_to_element(element).perform()
                else:
                    element.click()
                browser.settle()
                anchor = locate()
                if anchor is not None:
                    break
        if anchor is None:
            raise RuntimeError(f'No available navigation link in the tested states: {destination}')
        browser.driver.execute_script('arguments[0].scrollIntoView({block:"center"}); arguments[0].focus({preventScroll:true});', anchor)
        time.sleep(0.5)
        return anchor

    edges = set(only_edges) if only_edges is not None else None
    remaining = set(edges or ())
    checks = [record for record in store.data.get('integration', {}).get('links', []) if (record['from'], record['to']) not in edges] if edges is not None else []
    for url, page in list(store.data['pages'].items()):
        if page.get('kind') != 'page' or page['state'] not in ('validated', 'complete'):
            continue
        if edges is not None and not any(source == url for source, _ in edges):
            continue
        local_url = preview.origin + public_url(url, store.data['target'])
        browser.viewport(1440, 900)
        browser.navigate(local_url)
        # HTTP checks alone do not exercise client-side route transitions.
        anchors = browser.driver.execute_script('return Array.from(document.querySelectorAll("a[href]"),a=>({href:a.href,text:a.innerText}));')
        unique = list(dict.fromkeys(item['href'] for item in anchors if item['href'].startswith(preview.origin + '/')))
        for link in page['links']:
            destination = preview.origin + public_url(link, store.data['target'])
            if destination.split('#')[0] not in {item.split('#')[0] for item in unique}:
                unique.append(destination)
        if not quiet:
            print(f'[doppelgng.me] Checking navigation: {url} ({len(unique)} internal links)', flush=True)
        for destination in unique:
            if edges is not None and (url, destination) not in edges:
                continue
            remaining.discard((url, destination))
            event_start = len(browser.bidi.events)
            parts = urlsplit(destination)
            target_page = next((p for u, p in store.data['pages'].items() if route_key(u) == route_key(destination)), None)
            expected_destination = preview.origin + public_url(target_page['final_url'], store.data['target']) if target_page and target_page.get('final_url') else destination
            response = requests.get(destination.split('#')[0], timeout=60)
            result = {'from': url, 'to': destination, 'http_status': response.status_code, 'passed': response.status_code == 200}
            if parts.fragment:
                browser.navigate(local_url)
                try:
                    anchor = link_for(destination)
                    if anchor:
                        anchor.click()
                        browser.settle()
                        time.sleep(0.7)
                        result['anchor_exists'] = browser.driver.execute_script('return !!document.getElementById(arguments[0])', parts.fragment)
                        result['passed'] &= result['anchor_exists']
                        result['anchor_reached'] = urlsplit(browser.driver.current_url).fragment == parts.fragment and reached_route(expected_destination)
                        result['passed'] &= result['anchor_reached']
                except Exception as error:
                    result['passed'] = False
                    result['error'] = str(error)
            elif target_page and target_page.get('kind') == 'page':
                browser.navigate(local_url)
                try:
                    anchor = link_for(destination)
                    anchor.click()
                    browser.settle()
                    result['rendered_title'] = browser.driver.title
                    result['passed'] &= browser.driver.title == target_page.get('title')
                    result['route_reached'] = reached_route(expected_destination)
                    result['passed'] &= result['route_reached']
                    baseline = json.loads((store.artifact_dir(target_page['url']) / 'baseline.json').read_text(encoding='utf-8'))[0]['snapshot']
                    # Same-route links may retain scroll; the baseline starts at top.
                    scroll(browser, 0)
                    reached = snapshot(browser)
                    result['content_checks'] = {'text': reached['text'] == baseline['text'], 'headings': reached['headings'] == baseline['headings'], 'images': not reached['brokenImages']}
                    result['content_passed'] = all(result['content_checks'].values())
                    result['passed'] &= result['content_passed']
                    browser.driver.refresh()
                    browser.settle()
                    result['refresh_passed'] = browser.driver.title == target_page.get('title') and reached_route(expected_destination)
                    result['passed'] &= result['refresh_passed']
                except Exception as error:
                    result['passed'] = False
                    result['error'] = str(error)
            browser_failures = []
            for event in browser.bidi.events[event_start:]:
                params = event.get('params', {})
                if event.get('method') == 'network.fetchError' or (event.get('method') == 'log.entryAdded' and params.get('level') == 'error') or (event.get('method') == 'network.responseCompleted' and params['response']['status'] >= 400):
                    browser_failures.append({'method': event['method'], 'url': params.get('response', params.get('request', {})).get('url'), 'message': params.get('text', params.get('errorText')), 'status': params.get('response', {}).get('status')})
            result['browser_failures'] = browser_failures
            result['passed'] &= not browser_failures
            result['checked_at'] = now()
            checks.append(result)
    for source, destination in sorted(remaining):
        checks.append({'from': source, 'to': destination, 'passed': False, 'error': 'Requested navigation edge was not present in the current page inventory', 'checked_at': now()})
    store.data['integration'] = {'checked_at': now(), 'passed': all(check['passed'] for check in checks), 'links': checks}
    for page in store.data['pages'].values():
        if page['state'] in ('validated', 'download_validated') and store.data['integration']['passed']:
            page['state'] = 'complete'
    store.data['status'] = 'complete' if store.data['pages'] and all(p['state'] == 'complete' for p in store.data['pages'].values()) and store.data['integration']['passed'] else 'incomplete'
    store.save()
    return store.data['integration']


def capture(target, crawler_directory, output, *, port=4173, viewports=None, allowed_ratio=0.01, scenarios=None, respect_robots=True, checkpoint_every=1, quiet=False, authorized_resource_origins=None, authentication=None):
    if checkpoint_every < 0:
        raise ValueError('--checkpoint-every must be a non-negative integer')
    module = load_crawler(crawler_directory)
    target = module.WebCrawler._normalize_url(target)
    existing_manifest = Path(output) / 'manifest.json'
    if existing_manifest.exists() and (authentication or json.loads(existing_manifest.read_text(encoding='utf-8')).get('authentication', {}).get('required')):
        raise ValueError('Authenticated captures require a fresh --output directory for each session; login state is never saved for resume.')
    store = Store(output, target, crawler_identity(crawler_directory))
    store.authentication = authentication
    if authentication:
        store.data['authentication'] = {'required': True, 'method': 'html-form'}
    policy = {'page_host': urlsplit(target).netloc, 'respect_robots': respect_robots, 'checkpoint_every': checkpoint_every, 'quiet': quiet, 'volatile_static_query': ['_rsc'], 'allowed_visual_ratio': allowed_ratio, 'viewports': viewports or [[1440, 900], [390, 844]]}
    effective_scenarios = store.data.get('scenarios', {}) if scenarios is None else scenarios
    previous_policy = store.data.get('policy', {})
    policy['authorized_resource_origins'] = (previous_policy.get('authorized_resource_origins', [])
        if authorized_resource_origins is None else authorized_resource_origins)
    stricter_tolerance = previous_policy.get('allowed_visual_ratio') is None or allowed_ratio < previous_policy['allowed_visual_ratio']
    if (previous_policy.get('viewports') != policy['viewports'] or stricter_tolerance
            or store.data.get('scenarios', {}) != effective_scenarios):
        for page in store.data['pages'].values():
            if page.get('kind') != 'download' and page['state'] in ('validated', 'complete'):
                page['state'] = 'discovered'
                page['validation'].update(passed=False, stale=True)
        if 'integration' in store.data:
            store.data['integration'].update(passed=False, stale=True)
    store.data['policy'] = policy
    store.data['status'] = 'running'
    store.data.pop('error', None)
    store.data['scenarios'] = effective_scenarios
    (store.root / 'package.json').write_text(json.dumps({'name': 'doppelgng-reconstruction', 'private': True, 'type': 'module', 'scripts': {'dev': 'node server.mjs --manifest manifest.json'}}, indent=2), encoding='utf-8')
    shutil.copyfile(Path(__file__).resolve().parents[1] / 'server.mjs', store.root / 'server.mjs')
    shutil.copyfile(Path(__file__).resolve().parents[1] / 'LICENSE', store.root / 'DOPPELGNG_LICENSE.txt')
    store.save()
    atomic_json(Path('.doppelgng/current.json'), {'manifest': str(store.path)})
    browser_options = {'authentication': authentication} if authentication else {}
    with incomplete_on_failure(store), Preview(store, port) as preview, Waterfox(store.root / 'artifacts', **browser_options) as browser:
        if authentication:
            browser.navigate(target)
        store.data['browser'] = browser.identity
        adapter = build_adapter(module, store, browser, preview, viewports=store.data['policy']['viewports'], allowed_ratio=allowed_ratio, scenarios=store.data['scenarios'], respect_robots=respect_robots, checkpoint_every=checkpoint_every, quiet=quiet)
        try:
            adapter.crawl()
            navigation_validation(store, browser, preview, quiet=quiet)
        finally:
            adapter.archive.session.close()
    print(json.dumps({'status': store.data['status'], 'pages': len(store.data['pages']), 'resources': len(store.data['resources']), 'manifest': str(store.path)}, indent=2), flush=True)
    return store
