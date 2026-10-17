"""Pinned, project-local dependencies that never depend on a user's Desktop."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def runtime_lock(root=PROJECT_ROOT):
    return json.loads((Path(root) / 'runtime-lock.json').read_text(encoding='utf-8'))


def default_crawler(root=PROJECT_ROOT):
    configured = os.environ.get('DOPPELGNG_CRAWLER')
    return Path(configured).resolve() if configured else Path(root).resolve() / '.tools' / 'webcrawler'


def hash_file(path, algorithm='sha256'):
    digest = hashlib.new(algorithm)
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args, input=None, check=True):
    executable = shutil.which('git')
    if not executable:
        raise RuntimeError('Git is required for the first source-checkout setup. Packaged distributions already include the crawler.')
    result = subprocess.run([executable, *map(str, args)], input=input, capture_output=True, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if check and result.returncode:
        raise RuntimeError(f'Crawler download failed: {result.stderr.strip()}')
    return result


def crawler_errors(directory, spec):
    return [name for name, expected in spec['files'].items() if not (directory / name).is_file() or hash_file(directory / name) != expected]


def ensure_crawler(root=PROJECT_ROOT):
    root = Path(root).resolve()
    spec = runtime_lock(root)['crawler']
    target = root / '.tools' / 'webcrawler'
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        errors = crawler_errors(target, spec)
        if errors:
            raise RuntimeError(f'Managed crawler files differ from the pinned revision: {errors}. Preserve any local changes and choose an explicit --crawler path or a fresh project cache.')
    else:
        partial = target.with_name('webcrawler.partial')
        if not partial.exists():
            print(f'Fetching required crawler files at {spec["revision"][:12]}', flush=True)
            _git('clone', '--filter=blob:none', '--no-checkout', '--depth', '1', '--no-tags', spec['repository'], partial)
        elif not (partial / '.git').is_dir():
            raise RuntimeError(f'An incomplete crawler download needs inspection: {partial}')
        patterns = '\n'.join('/' + name for name in spec['files']) + '\n'
        _git('-C', partial, '-c', 'core.autocrlf=false', 'sparse-checkout', 'set', '--no-cone', '--stdin', input=patterns)
        if _git('-C', partial, 'cat-file', '-e', spec['revision'] + '^{commit}', check=False).returncode:
            _git('-C', partial, 'fetch', '--depth', '1', '--no-tags', 'origin', spec['revision'])
        _git('-C', partial, '-c', 'core.autocrlf=false', 'checkout', '--detach', spec['revision'])
        errors = crawler_errors(partial, spec)
        if errors:
            raise RuntimeError(f'Pinned crawler integrity failed: {errors}')
        if partial.resolve().parent != target.resolve().parent:
            raise RuntimeError('Crawler staging path escaped the project tools directory')
        partial.rename(target)
    receipt = {'repository': spec['repository'], 'revision': spec['revision'], 'files': spec['files']}
    path = target / 'upstream.json'
    contents = json.dumps(receipt, indent=2) + '\n'
    if not path.is_file() or path.read_text(encoding='utf-8') != contents:
        path.write_text(contents, encoding='utf-8')
    return target
