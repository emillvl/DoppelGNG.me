from pathlib import Path
from contextlib import redirect_stdout
import io
import json
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from doppelgng.archive import ExtractionFailure
from doppelgng.crawler import load_crawler
from doppelgng.pipeline import build_adapter, navigation_validation
from doppelgng.storage import Store
from doppelgng.dependencies import default_crawler


class PipelineGates(unittest.TestCase):
    def setUp(self):
        self.module = load_crawler(default_crawler())
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = Store(self.temporary.name, 'https://example.test/')
        self.browser = SimpleNamespace(driver=SimpleNamespace(execute_script=lambda *_: 'test browser'), bidi=SimpleNamespace(events=[]))
        self.preview = SimpleNamespace(origin='http://127.0.0.1:4173')
        self.crawler = self.make_crawler()

    def make_crawler(self, **options):
        options.setdefault('quiet', True)
        crawler = build_adapter(self.module, self.store, self.browser, self.preview, viewports=[[1440, 900]], allowed_ratio=0.01, scenarios={}, **options)
        self.addCleanup(crawler.archive.session.close)
        return crawler

    def test_failed_current_page_is_retried_before_new_pages(self):
        first = self.store.page('https://example.test/')
        first['state'] = 'failed'
        self.store.page('https://example.test/next/')
        self.crawler.visited.add(first['url'])
        self.crawler._prepare_queue()
        next_page = self.crawler.stack.popleft() if hasattr(self.crawler.stack, 'popleft') else self.crawler.stack.pop()
        self.assertEqual(next_page, first['url'])
        self.assertNotIn(first['url'], self.crawler.visited)

    def test_extraction_failure_keeps_manifest_incomplete(self):
        with patch.object(self.crawler.archive.session, 'head', side_effect=RuntimeError('upstream unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'upstream unavailable'):
                self.crawler._fetch('https://example.test/')
        resumed = Store(self.temporary.name)
        self.assertEqual(resumed.data['status'], 'incomplete')
        self.assertEqual(resumed.page('https://example.test/')['state'], 'failed')

    def test_origin_policy_does_not_expand_to_other_ports(self):
        self.assertTrue(self.crawler._same_domain('https://example.test/a'))
        self.assertFalse(self.crawler._same_domain('https://example.test:8443/a'))
        self.assertFalse(self.crawler._same_domain('http://example.test/a'))
        self.assertFalse(self.crawler._same_domain('https://other.test/a'))

    def test_robots_denial_is_visible_and_does_not_pass(self):
        self.crawler._robots = SimpleNamespace(can_fetch=lambda *_: False)
        with self.assertRaisesRegex(ExtractionFailure, 'robots.txt'):
            self.crawler._can_fetch('https://example.test/private/')
        self.assertEqual(self.store.page('https://example.test/private/')['state'], 'blocked')

    def test_ignore_robots_skips_the_request_and_allows_disallowed_routes(self):
        crawler = self.make_crawler(respect_robots=False)
        with patch('requests.get') as request, patch('doppelgng.pipeline.sitemap_pages', return_value=([], [])):
            crawler._load_robots()
        request.assert_not_called()
        self.assertFalse(crawler.respect_robots)
        self.assertTrue(crawler._can_fetch('https://example.test/private/'))

    def test_respect_robots_loads_and_applies_real_rules(self):
        response = MagicMock(status_code=200, text='User-agent: *\nDisallow: /private/\n')
        response.__enter__.return_value = response
        with patch.object(self.crawler.archive.session, 'get', return_value=response) as request, patch('doppelgng.pipeline.sitemap_pages', return_value=([], [])):
            self.crawler._load_robots()
        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.args[0], 'https://example.test/robots.txt')
        self.assertTrue(self.crawler._can_fetch('https://example.test/public/'))
        with self.assertRaisesRegex(ExtractionFailure, 'robots.txt'):
            self.crawler._can_fetch('https://example.test/private/')

    def test_checkpoint_interval_controls_actual_state_writes(self):
        crawler = self.make_crawler(checkpoint_every=3)
        with patch.object(crawler, '_ram_exceeded', return_value=False):
            crawler._after_page()
            crawler._after_page()
            self.assertFalse(Path(crawler.state_file).exists())
            crawler._after_page()
        state = json.loads(Path(crawler.state_file).read_text(encoding='utf-8'))
        self.assertEqual(state['meta']['pages_processed'], 3)

    def test_zero_interval_disables_periodic_writes_but_keeps_final_save(self):
        crawler = self.make_crawler(checkpoint_every=0)
        with patch.object(crawler, '_ram_exceeded', return_value=False):
            for _ in range(10):
                crawler._after_page()
        self.assertFalse(Path(crawler.state_file).exists())
        self.assertTrue(crawler.save_state(final=True))
        state = json.loads(Path(crawler.state_file).read_text(encoding='utf-8'))
        self.assertEqual(state['meta']['pages_processed'], 10)

    def test_quiet_suppresses_progress_and_report_without_hiding_failure(self):
        with redirect_stdout(io.StringIO()) as output, patch.object(self.crawler.archive.session, 'head', side_effect=RuntimeError('upstream unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'upstream unavailable'):
                self.crawler._fetch('https://example.test/')
            self.crawler._print_summary()
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(self.store.data['pages']['https://example.test/']['state'], 'failed')

    def test_failed_crawl_only_prints_product_progress_and_retains_checkpoint(self):
        crawler = self.make_crawler(quiet=False)
        with redirect_stdout(io.StringIO()) as output, patch.object(crawler, '_load_robots'), patch.object(crawler.archive.session, 'head', side_effect=RuntimeError('upstream unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'upstream unavailable'):
                crawler.crawl()
        lines = output.getvalue().splitlines()
        self.assertEqual(lines, ['[doppelgng.me] Extracting https://example.test/'])
        self.assertTrue(Path(crawler.state_file).is_file())
        self.assertEqual(self.store.data['status'], 'incomplete')

    def test_missing_edge_cannot_turn_a_failed_integration_into_a_pass(self):
        page = self.store.page('https://example.test/')
        page.update({'state': 'validated', 'kind': 'page'})
        edge = ('https://example.test/', 'http://127.0.0.1:4173/gone')
        self.store.data['integration'] = {'passed': False, 'links': [{'from': edge[0], 'to': edge[1], 'passed': False}]}
        browser = SimpleNamespace(viewport=lambda *_: None, navigate=lambda *_: None, driver=SimpleNamespace(execute_script=lambda *_: []))
        with redirect_stdout(io.StringIO()) as output:
            result = navigation_validation(self.store, browser, SimpleNamespace(origin='http://127.0.0.1:4173'), only_edges=[edge], quiet=True)
        self.assertEqual(output.getvalue(), '')
        self.assertFalse(result['passed'])
        self.assertEqual(self.store.data['status'], 'incomplete')
        self.assertIn('not present', result['links'][0]['error'])

    def navigation_result(self, reached, *, include_other_variant=False, final_url=None):
        source = self.store.data['target']
        target = source + 'item?variant=2'
        destination = self.preview.origin + '/item?variant=2'
        page = self.store.page(source)
        page.update(state='validated', kind='page', links=[target])
        if include_other_variant:
            other = self.store.page(source + 'item?variant=1')
            other.update(state='validated', kind='page', title='Variant one')
            (self.store.artifact_dir(other['url']) / 'baseline.json').write_text(json.dumps([{'snapshot': {'text': 'one', 'headings': []}}]))
        target_page = self.store.page(target)
        target_page.update(state='validated', kind='page', title='Variant two')
        if final_url:
            target_page['final_url'] = final_url
        (self.store.artifact_dir(target) / 'baseline.json').write_text(json.dumps([{'snapshot': {'text': 'two', 'headings': []}}]))
        driver = SimpleNamespace(current_url='', title='Variant two', refresh=lambda: None)
        def click():
            driver.current_url = reached
        anchor = SimpleNamespace(click=click)
        def execute(script, *_args):
            if '.find(a=>' in script:
                return anchor
            if 'a=>({href:a.href,text:a.innerText})' in script:
                return [{'href': destination, 'text': 'Variant two'}]
        driver.execute_script = execute
        browser = SimpleNamespace(driver=driver, bidi=SimpleNamespace(events=[]), viewport=lambda *_: None, navigate=lambda url: setattr(driver, 'current_url', url), settle=lambda: None)
        with patch('doppelgng.pipeline.requests.get', return_value=SimpleNamespace(status_code=200)), patch('doppelgng.pipeline.scroll'), patch('doppelgng.pipeline.time.sleep'), patch('doppelgng.pipeline.snapshot', return_value={'text': 'two', 'headings': [], 'brokenImages': []}):
            result = navigation_validation(self.store, browser, self.preview, only_edges=[(source, destination)], quiet=True)
        return result['links'][0]

    def test_navigation_selects_the_matching_query_variant(self):
        result = self.navigation_result(self.preview.origin + '/item?variant=2', include_other_variant=True)
        self.assertTrue(result['passed'], result)

    def test_crawl_scope_accepts_equivalent_default_port_without_expanding_origin(self):
        self.assertTrue(self.crawler._same_domain('https://example.test:443/next'))
        self.assertFalse(self.crawler._same_domain('https://example.test:444/next'))
        self.assertFalse(self.crawler._same_domain('http://example.test/next'))

    def test_navigation_accepts_the_recorded_same_origin_redirect_destination(self):
        result = self.navigation_result(self.preview.origin + '/canonical?variant=2', final_url='https://example.test/canonical?variant=2')
        self.assertTrue(result['passed'], result)

    def test_navigation_cannot_pass_after_escaping_local_origin_or_dropping_query(self):
        for reached in ('https://example.test/item?variant=2', self.preview.origin + '/item?variant=1'):
            with self.subTest(reached=reached):
                result = self.navigation_result(reached)
                self.assertFalse(result['passed'], result)
