"""Rewrite local resource copies and their integrity metadata."""
import base64
from collections import defaultdict, deque
from urllib.parse import urlsplit, urlunsplit

from .resources import process
from .network import origin
from .storage import digest, digest_file


def public_url(url, target):
    parts = urlsplit(url)
    if origin(url) == origin(target):
        return urlunsplit(('', '', parts.path or '/', parts.query, parts.fragment))
    return '/__doppelgng__/asset/' + digest(url.encode())


def reconstruct(store, urls):
    urls = list(dict.fromkeys(urls))
    previous_hashes = {url: store.data['resources'][url].get('local_sha256') for url in urls}
    hashes = {}
    document_dependencies = defaultdict(set)

    def integrity(dependency, value, document):
        record = store.data['resources'].get(dependency)
        if not record:
            return value
        tokens = [token.partition('-') for token in value.split()]
        supported = {algorithm for algorithm, _, _ in tokens if algorithm in ('sha256', 'sha384', 'sha512')}
        if not supported:
            return value

        def encoded(field, algorithm):
            key = record[field], algorithm
            if key not in hashes:
                hashes[key] = base64.b64encode(bytes.fromhex(digest_file(store.root / record[field], algorithm))).decode('ascii')
            return hashes[key]

        strongest = max(supported, key=lambda algorithm: int(algorithm[3:]))
        expected = encoded('raw', strongest)
        if not any(algorithm == strongest and token.partition('?')[0] == expected for algorithm, _, token in tokens):
            return value
        if 'html' in record['content_type'].lower():
            document_dependencies[document].add(dependency)
        updated = []
        for algorithm, separator, token in tokens:
            if algorithm in supported:
                options = '?' + token.partition('?')[2] if '?' in token else ''
                updated.append(algorithm + '-' + encoded('local', algorithm) + options)
            else:
                updated.append(algorithm + separator + token)
        return ' '.join(updated)

    # Document integrity attributes need the dependencies' final local bytes.
    urls.sort(key=lambda url: 'html' in store.data['resources'][url]['content_type'].lower())
    def write_resource(url):
        record = store.data['resources'][url]
        raw = (store.root / record['raw']).read_bytes()
        mime = record['content_type'].lower()
        if any(token in mime for token in ('html', 'css', 'javascript')) or urlsplit(url).path.endswith(('.js', '.mjs')):
            text = raw.decode('utf-8-sig')
            _, modified = process(text, mime, record.get('final_url', url), lambda value: public_url(value, store.data['target']), known_urls=store.data['resources'], integrity=lambda dependency, value: integrity(dependency, value, url))
            body = modified.encode('utf-8')
        else:
            body = raw
        store.write(record['local'], body)
        record['local_sha256'] = digest(body)
        record['public_url'] = public_url(url, store.data['target'])
        for algorithm in ('sha256', 'sha384', 'sha512'):
            hashes.pop((record['local'], algorithm), None)

    for url in urls:
        write_resource(url)
    # Integrity-protected HTML preloads need dependency-ordered finalization.
    # Cycles have no stable rewrite order.
    waiting, dependants = {}, defaultdict(set)
    for document, dependencies in document_dependencies.items():
        pending = {dependency for dependency in dependencies if dependency in document_dependencies}
        waiting[document] = len(pending)
        for dependency in pending:
            dependants[dependency].add(document)
    ready = deque(document for document, count in waiting.items() if not count)
    while ready:
        document = ready.popleft()
        write_resource(document)
        del waiting[document]
        for dependant in dependants[document]:
            waiting[dependant] -= 1
            if not waiting[dependant]:
                ready.append(dependant)
    if waiting:
        raise ValueError('Cannot rewrite cyclic HTML subresource integrity dependencies')
    changed = [url for url in urls if previous_hashes[url] and previous_hashes[url] != store.data['resources'][url]['local_sha256']]
    store.invalidate(changed)
    store.save()
