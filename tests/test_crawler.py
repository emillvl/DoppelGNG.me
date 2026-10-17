import os
from pathlib import Path
import tempfile
import unittest

from doppelgng.crawler import crawler_identity, load_crawler

TEST_TEMP = Path(__file__).resolve().parents[1] / '.tools' / 'test-temp'
TEST_TEMP.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(TEST_TEMP)


class ExistingCrawlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = Path(os.environ.get("DOPPELGNG_CRAWLER", Path.home() / "Desktop" / "WebCrawler"))
        cls.module = load_crawler(cls.directory)

    def test_original_source_is_not_modified_by_adapter(self):
        before = crawler_identity(self.directory)
        load_crawler(self.directory)
        self.assertEqual(before, crawler_identity(self.directory))

    def test_uses_existing_normalization_and_navigation(self):
        from bs4 import BeautifulSoup
        with tempfile.TemporaryDirectory() as directory:
            crawler = self.module.WebCrawler("https://example.com", output_dir=directory, allow_selenium=False)
            soup = BeautifulSoup('<a href="/a?utm_source=x#top">a</a><a href="/a">b</a><a href="https://other.test">out</a>', 'html.parser')
            self.assertEqual(crawler._extract_links(soup, crawler.base_url), ['https://example.com/a'])

    def test_inherits_existing_checkpoint_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            crawler = self.module.WebCrawler('https://example.com', output_dir=directory, quiet=True)
            crawler.visited.add('https://example.com/')
            crawler.stack.append('https://example.com/next')
            self.assertTrue(crawler.save_state())
            resumed = self.module.WebCrawler('https://example.com', output_dir=directory, quiet=True)
            self.assertTrue(resumed.load_state())
            self.assertEqual(resumed.stack, ['https://example.com/next'])

    def test_missing_crawler_is_explicit_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'webcrawler.py'):
                load_crawler(directory)
