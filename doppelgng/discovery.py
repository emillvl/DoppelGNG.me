"""Supplement the existing link crawler with same-origin sitemap discovery."""
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET

import requests


def sitemap_pages(crawler, *, max_maps=100, max_bytes=10_000_000):
    origin = '{0.scheme}://{0.netloc}'.format(urlsplit(crawler.base_url))
    declared = crawler._robots.site_maps() if crawler._robots else None
    pending = list(declared or [urljoin(origin, '/sitemap.xml')])
    seen, pages, observations = set(), [], []
    while pending:
        url = pending.pop(0)
        if url in seen:
            continue
        if not crawler._same_domain(url):
            observations.append({'url': url, 'state': 'outside-authorized-origin'})
            continue
        if len(seen) >= max_maps:
            raise RuntimeError(f'Sitemap discovery limit reached ({max_maps}); capture cannot claim exhaustive discovery')
        seen.add(url)
        response = requests.get(url, headers=crawler._HEADERS, timeout=crawler.timeout, stream=True)
        with response:
            observation = {'url': url, 'status': response.status_code}
            observations.append(observation)
            if response.status_code in (404, 410) and not declared:
                continue
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_content(65536):
                content.extend(chunk)
                if len(content) > max_bytes:
                    raise RuntimeError(f'Sitemap exceeds configured size limit: {url}')
        root = ET.fromstring(content)
        locations = [element.text.strip() for element in root.iter() if element.tag.rsplit('}', 1)[-1] == 'loc' and element.text]
        if root.tag.rsplit('}', 1)[-1] == 'sitemapindex':
            pending.extend(locations)
        else:
            for location in locations:
                if crawler._same_domain(location):
                    pages.append(crawler._normalize_url(location))
        observation['locations'] = len(locations)
    return list(dict.fromkeys(pages)), observations
