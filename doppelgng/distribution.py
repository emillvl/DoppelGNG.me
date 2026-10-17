"""Package source, the pinned crawler, and the complete private browser runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from .bootstrap import verify_runtime
from .dependencies import PROJECT_ROOT, ensure_crawler, hash_file, runtime_lock

SOURCE_FILES = ('.gitignore', '.gitattributes', 'package.json', 'package-lock.json', 'README.md', 'THIRD_PARTY_NOTICES.md', 'requirements.txt', 'requirements.lock.txt', 'runtime-lock.json', 'server.mjs')


def package_files(root=PROJECT_ROOT):
    root = Path(root).resolve()
    runtime = verify_runtime(root)
    crawler = ensure_crawler(root, offline=True)
    files = {name: root / name for name in SOURCE_FILES}
    for directory, extensions in [('doppelgng', {'.py'}), ('scripts', {'.mjs'}), ('tests', {'.py', '.mjs', '.json'})]:
        for file in (root / directory).rglob('*'):
            if file.is_file() and file.suffix in extensions and '__pycache__' not in file.parts:
                files[file.relative_to(root).as_posix()] = file
    for name in runtime['files']:
        files['.tools/' + name] = root / '.tools' / name
    for name in ('runtime-manifest.json', 'waterfox-provenance.json', 'geckodriver-provenance.json'):
        files['.tools/' + name] = root / '.tools' / name
    for name in [*runtime_lock(root)['crawler']['files'], 'upstream.json']:
        files['.tools/webcrawler/' + name] = crawler / name
    for name, file in files.items():
        if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(root):
            raise RuntimeError(f'Cannot package missing or external dependency: {name}')
    return dict(sorted(files.items()))


def build_distribution(root=PROJECT_ROOT, destination=None):
    root = Path(root).resolve()
    destination = Path(destination or root / 'dist/doppelgng.me-windows-x64.zip').resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + '.part')
    files = package_files(root)
    hashes = {}
    print(f'Packaging {len(files)} application and runtime files', flush=True)
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, file in files.items():
            hashes[name] = {'sha256': hash_file(file), 'bytes': file.stat().st_size}
            archive.write(file, 'DoppelGNG.me/' + name)
        manifest = {'schema': 1, 'platform': 'windows-x64', 'prerequisites': ['Node.js 22+', 'Python 3.10+'], 'included': ['pinned WebCrawler files', 'complete Waterfox runtime', 'geckodriver', 'license notices'], 'files': hashes}
        archive.writestr('DoppelGNG.me/bundle-manifest.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(temporary) as archive:
        for name, expected in hashes.items():
            with archive.open('DoppelGNG.me/' + name) as source:
                digest = hashlib.sha256()
                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(chunk)
            if digest.hexdigest() != expected['sha256']:
                raise RuntimeError(f'Packaged file integrity failed: {name}')
    temporary.replace(destination)
    checksum = hash_file(destination)
    destination.with_name(destination.name + '.sha256').write_text(f'{checksum}  {destination.name}\n', encoding='utf-8')
    return {'archive': str(destination), 'bytes': destination.stat().st_size, 'sha256': checksum, 'files': len(files)}


def main():
    parser = argparse.ArgumentParser(description='Build the Windows x64 distribution with its crawler and browser already included')
    parser.add_argument('--output')
    args = parser.parse_args()
    print(json.dumps(build_distribution(destination=args.output), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError) as error:
        raise SystemExit(f'Packaging failed: {error}')
