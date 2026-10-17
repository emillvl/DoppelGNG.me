"""Reconstruct captured code while keeping the untouched originals addressable."""
from urllib.parse import urlsplit, urlunsplit

from .resources import process
from .storage import digest


def public_url(url, target):
    parts = urlsplit(url)
    if parts.netloc.lower() == urlsplit(target).netloc.lower():
        return urlunsplit(('', '', parts.path or '/', parts.query, parts.fragment))
    return '/__doppelgng__/asset/' + digest(url.encode())


def reconstruct(store, urls):
    changed = []
    for url in urls:
        record = store.data['resources'][url]
        raw = (store.root / record['raw']).read_bytes()
        mime = record['content_type']
        if any(token in mime for token in ('html', 'css', 'javascript')) or urlsplit(url).path.endswith(('.js', '.mjs')):
            text = raw.decode('utf-8-sig')
            _, modified = process(text, mime, url, lambda value: public_url(value, store.data['target']), known_urls=store.data['resources'])
            body = modified.encode('utf-8')
        else:
            body = raw
        previous = record.get('local_sha256')
        store.write(record['local'], body)
        record['local_sha256'] = digest(body)
        record['public_url'] = public_url(url, store.data['target'])
        if previous and previous != record['local_sha256']:
            changed.append(url)
    # Shared modifications invalidate previously recorded pass states.
    for page in store.data['pages'].values():
        if page['state'] == 'complete' and set(page['resources']).intersection(changed):
            page['state'] = 'reconstructed'
            page['validation']['stale'] = True
            store.data['status'] = 'incomplete'
    store.save()
