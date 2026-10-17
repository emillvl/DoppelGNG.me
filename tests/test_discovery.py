from types import SimpleNamespace
import unittest
from unittest.mock import patch

from doppelgng.discovery import sitemap_pages


class Response:
    def __init__(self, content, status=200):
        self.content, self.status_code = content, status
    def __enter__(self):
        return self
    def __exit__(self, *_):
        pass
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(str(self.status_code))
    def iter_content(self, _):
        yield self.content


class SitemapTests(unittest.TestCase):
    def test_follows_sitemap_indexes_and_excludes_external_hosts(self):
        crawler = SimpleNamespace(base_url='https://a.test/', _robots=None, timeout=10, _HEADERS={}, _same_domain=lambda url: url.startswith('https://a.test/'), _normalize_url=lambda url: url)
        responses = [Response(b'<sitemapindex><sitemap><loc>https://a.test/pages.xml</loc></sitemap><sitemap><loc>https://other.test/map.xml</loc></sitemap></sitemapindex>'), Response(b'<urlset><url><loc>https://a.test/hidden-linked-route/</loc></url><url><loc>https://other.test/page/</loc></url></urlset>')]
        with patch('doppelgng.discovery.requests.get', side_effect=responses):
            pages, observations = sitemap_pages(crawler)
        self.assertEqual(pages, ['https://a.test/hidden-linked-route/'])
        self.assertEqual(observations[-1]['state'], 'outside-authorized-origin')

    def test_absent_optional_sitemap_is_recorded(self):
        crawler = SimpleNamespace(base_url='https://a.test/', _robots=None, timeout=10, _HEADERS={}, _same_domain=lambda _: True)
        with patch('doppelgng.discovery.requests.get', return_value=Response(b'not found', 404)):
            pages, observations = sitemap_pages(crawler)
        self.assertEqual(pages, [])
        self.assertEqual(observations[0]['status'], 404)
