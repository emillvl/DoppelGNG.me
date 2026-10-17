"""Deliver a complete reconstruction as a separate, portable npm project."""
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit

from .storage import Store


def default_output(url):
    host = re.sub(r'[^\w.-]', '_', urlsplit(url).netloc).rstrip('.')
    if not host:
        raise ValueError('A website hostname is required for the copied folder name')
    if re.match(r'^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', host, re.IGNORECASE):
        host = '_' + host
    return Path(host)


def export_project(store: Store, destination=None):
    if store.data['status'] != 'complete':
        raise ValueError('Export requires a completed and validated reconstruction')
    broken = store.verify(list(store.data['resources']))
    if broken:
        raise ValueError(f'Export integrity check failed: {broken}')
    target = Path(destination or default_output(store.data['target'])).resolve()
    if target == store.root:
        return target
    if target.is_relative_to(store.root):
        raise ValueError('The delivery folder must be separate from the capture workspace')
    if target.exists():
        raise ValueError(f'Delivery folder already exists; choose another destination: {target}')
    partial = target.with_name(target.name + '.partial')
    if partial.exists():
        raise ValueError(f'An unfinished export already exists: {partial}')
    target.parent.mkdir(parents=True, exist_ok=True)
    # Both the staging folder and final folder resolve inside the explicit
    # destination parent. No existing folder is overwritten or deleted.
    parent = target.parent.resolve()
    if partial.resolve().parent != parent or target.resolve().parent != parent:
        raise ValueError('Export path escapes the destination parent')
    partial.mkdir()
    for name in ('site', 'raw', 'artifacts', 'crawler'):
        if (store.root / name).is_dir():
            shutil.copytree(store.root / name, partial / name)
    for name in ('manifest.json', 'package.json', 'server.mjs'):
        shutil.copy2(store.root / name, partial / name)
    copied = Store(partial)
    if copied.verify(list(copied.data['resources'])):
        raise ValueError('Copied resource integrity failed; the staging folder was retained for diagnosis')
    partial.rename(target)
    return target
