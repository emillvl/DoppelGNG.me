"""Atomic manifests, content hashes, resource mappings, and resumable page states."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit
from contextlib import contextmanager

import psutil


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def digest(data: bytes):
    return hashlib.sha256(data).hexdigest()


def digest_file(path, algorithm='sha256'):
    hasher = hashlib.new(algorithm)
    buffer = bytearray(1024 * 1024)
    with Path(path).open('rb') as handle:
        while size := handle.readinto(buffer):
            hasher.update(memoryview(buffer)[:size])
    return hasher.hexdigest()


def atomic_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, ensure_ascii=False, indent=2)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, prefix=path.name + '.', suffix='.tmp', delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(serialized)
        except BaseException:
            handle.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        for attempt in range(10):
            try:
                temporary.replace(path)
                break
            except PermissionError as error:
                if os.name != 'nt' or getattr(error, 'winerror', None) not in (5, 32, 33) or attempt == 9:
                    raise
                # Windows can deny replacement briefly while another writer renames.
                time.sleep(0.01 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def incomplete_on_failure(store):
    try:
        yield
    except BaseException as error:
        message = str(error) or type(error).__name__
        store.data.update(status='incomplete', error=message)
        for page in store.data['pages'].values():
            if page['state'] in ('extracting', 'validating'):
                page.update(state='failed', error=message)
        store.save()
        raise


@contextmanager
def workspace_lock(directory):
    root = Path(directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = root / 'capture.lock'
    # Unlinking a stale PID file can remove a new owner's lock after a race.
    # Keep the file; OS locks release on process exit.
    with lock.open('a+', encoding='utf-8') as handle:
        try:
            if os.name == 'nt':
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError(f'Another capture or validation owns {root}') from error
        try:
            handle.seek(0)
            try:
                owner = json.load(handle)
            except ValueError:
                owner = {}
            if isinstance(owner, dict) and owner.get('locking') != 'os' and isinstance(owner.get('pid'), int) and owner['pid'] > 0 and psutil.pid_exists(owner['pid']):
                raise RuntimeError(f'Another capture or validation owns {root} (legacy process {owner["pid"]})')
            handle.seek(0)
            handle.truncate()
            json.dump({'locking': 'os', 'pid': os.getpid(), 'created_at': now()}, handle)
            handle.flush()
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class Store:
    def __init__(self, directory: str | Path, target=None, crawler=None):
        self.root = Path(directory).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'manifest.json'
        if not self.path.exists() and any(file.name != 'capture.lock' for file in self.root.iterdir()):
            raise ValueError(f'The output folder already contains unrelated files; choose another --output directory: {self.root}')
        for name in ('raw', 'site', 'artifacts', 'crawler'):
            (self.root / name).mkdir(exist_ok=True)
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
            extension = '.html' if 'html' in headers.get('content-type', '').lower() else '.bin'
        raw = f'raw/{content_hash}'
        local = f'site/files/{key}{extension}'
        previous = self.data['resources'].get(url)
        if previous and (previous['sha256'] != content_hash or previous['status'] != status
                         or previous['content_type'] != headers.get('content-type', 'application/octet-stream')
                         or previous.get('headers', {}).get('content-disposition') != headers.get('content-disposition')):
            self.invalidate([url])
        raw_path = self.root / raw
        if not raw_path.is_file() or digest_file(raw_path) != content_hash:
            self.write(raw, body)
        keep_local = previous and previous['sha256'] == content_hash and previous['local'] == local and self.intact(previous, local=True)
        if not keep_local:
            self.write(local, body)
        local_hash = previous['local_sha256'] if keep_local else content_hash
        record = {'url': url, 'key': key, 'raw': raw, 'local': local, 'sha256': content_hash, 'local_sha256': local_hash, 'bytes': len(body), 'status': status, 'content_type': headers.get('content-type', 'application/octet-stream'), 'method': method, 'source': source, 'kind': kind, 'headers': {k: v for k, v in headers.items() if k in ('content-type', 'content-disposition', 'cache-control', 'vary')}, 'request_headers': request_headers or {}, 'dependencies': previous.get('dependencies', []) if keep_local else [], 'captured_at': now()}
        self.data['resources'][url] = record
        return record

    def invalidate(self, urls):
        changed = set(urls)
        if not changed:
            return
        for page in self.data['pages'].values():
            if page['state'] in ('validated', 'complete', 'download_validated') and changed.intersection(page['resources']):
                page['state'] = 'reconstructed'
                page['validation'].update(passed=False, stale=True)
                self.data['status'] = 'incomplete'
                if 'integration' in self.data:
                    self.data['integration'].update(passed=False, stale=True)

    def intact(self, record, local=False):
        path = self.root / record['local' if local else 'raw']
        return path.is_file() and digest_file(path) == record['local_sha256' if local else 'sha256']

    def verify(self, urls):
        return [url for url in urls if url not in self.data['resources'] or not self.intact(self.data['resources'][url]) or not self.intact(self.data['resources'][url], local=True)]

    def artifact_dir(self, url):
        directory = self.root / 'artifacts' / digest(url.encode())[:16]
        directory.mkdir(exist_ok=True)
        return directory
