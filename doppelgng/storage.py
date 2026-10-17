"""Atomic manifests, content hashes, resource mappings, and resumable page states."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from contextlib import contextmanager

import psutil


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def digest(data: bytes):
    return hashlib.sha256(data).hexdigest()


def atomic_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


@contextmanager
def workspace_lock(directory):
    root = Path(directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = root / 'capture.lock'
    if lock.exists():
        owner = json.loads(lock.read_text(encoding='utf-8'))
        if psutil.pid_exists(owner['pid']):
            raise RuntimeError(f'Another capture or validation owns {root} (process {owner["pid"]})')
        lock.unlink()
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError as error:
        raise RuntimeError(f'Another operation acquired the capture workspace: {root}') from error
    with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
        json.dump({'pid': os.getpid(), 'created_at': now()}, handle)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


class Store:
    def __init__(self, directory: str | Path, target=None, crawler=None):
        self.root = Path(directory).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        for name in ('raw', 'site', 'artifacts', 'crawler'):
            (self.root / name).mkdir(exist_ok=True)
        self.path = self.root / 'manifest.json'
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding='utf-8'))
            if target and self.data['target'] != target:
                raise ValueError('This workspace belongs to another target; use a separate output directory')
            if crawler and self.data.get('crawler', {}).get('files') != crawler.get('files'):
                raise ValueError('Crawler source changed since capture; use a new output workspace')
        else:
            if not target:
                raise ValueError(f'No capture manifest found in {self.root}')
            self.data = {'schema': 1, 'target': target, 'created_at': now(), 'status': 'discovered', 'crawler': crawler, 'pages': {}, 'resources': {}, 'discrepancies': [], 'policy': {}}
            self.save()

    def save(self):
        self.data['updated_at'] = now()
        atomic_json(self.path, self.data)

    def page(self, url):
        if url not in self.data['pages']:
            self.data['pages'][url] = {'url': url, 'state': 'discovered', 'resources': [], 'links': [], 'validation': {}, 'discovered_at': now()}
        return self.data['pages'][url]

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.part')
        temporary.write_bytes(data)
        temporary.replace(path)

    def resource(self, url, body, *, status=200, headers=None, method='GET', source='waterfox', kind='resource', request_headers=None):
        headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
        key = digest(url.encode())
        content_hash = digest(body)
        extension = Path(urlsplit(url).path).suffix
        if not extension or len(extension) > 12 or not extension[1:].isalnum():
            extension = '.html' if 'html' in headers.get('content-type', '') else '.bin'
        raw = f'raw/{content_hash}'
        local = f'site/files/{key}{extension}'
        if not (self.root / raw).is_file():
            self.write(raw, body)
        self.write(local, body)
        record = {'url': url, 'key': key, 'raw': raw, 'local': local, 'sha256': content_hash, 'local_sha256': content_hash, 'bytes': len(body), 'status': status, 'content_type': headers.get('content-type', 'application/octet-stream'), 'method': method, 'source': source, 'kind': kind, 'headers': {k: v for k, v in headers.items() if k in ('content-type', 'content-disposition', 'cache-control', 'vary')}, 'request_headers': request_headers or {}, 'dependencies': [], 'captured_at': now()}
        self.data['resources'][url] = record
        return record

    def intact(self, record, local=False):
        path = self.root / record['local' if local else 'raw']
        return path.is_file() and digest(path.read_bytes()) == record['local_sha256' if local else 'sha256']

    def verify(self, urls):
        return [url for url in urls if url not in self.data['resources'] or not self.intact(self.data['resources'][url]) or not self.intact(self.data['resources'][url], local=True)]

    def artifact_dir(self, url):
        directory = self.root / 'artifacts' / digest(url.encode())[:16]
        directory.mkdir(exist_ok=True)
        return directory
