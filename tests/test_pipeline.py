from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from doppelgng.archive import ExtractionFailure
from doppelgng.crawler import load_crawler
from doppelgng.pipeline import build_adapter
from doppelgng.storage import Store


class PipelineGates(unittest.TestCase):
    def setUp(self):
        self.module = load_crawler(Path.home() / 'Desktop' / 'WebCrawler')
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = Store(self.temporary.name, 'https://example.test/')
        browser = SimpleNamespace(driver=SimpleNamespace(execute_script=lambda *_: 'test browser'), bidi=SimpleNamespace(events=[]))
        self.crawler = build_adapter(self.module, self.store, browser, SimpleNamespace(origin='http://127.0.0.1:4173'), viewports=[[1440, 900]], allowed_ratio=0.01, scenarios={})
        self.crawler.quiet = True

    def test_failed_current_page_is_retried_before_new_pages(self):
        first = self.store.page('https://example.test/')
        first['state'] = 'failed'
        self.store.page('https://example.test/next/')
        self.crawler.visited.add(first['url'])
        self.crawler._prepare_queue()
        self.assertEqual(self.crawler.stack.pop(), first['url'])
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
