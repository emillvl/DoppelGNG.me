"""Install once, verify, and reuse the project's private browser runtime."""
from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import zipfile

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .dependencies import PROJECT_ROOT, ensure_crawler, hash_file, runtime_lock


def download(url, destination, algorithm, expected, *, offline=False):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and hash_file(destination, algorithm) == expected:
        return
    if offline:
        raise RuntimeError(f'Required cached dependency is missing or corrupt: {destination}')
    temporary = destination.with_name(destination.name + '.part')
    digest = hashlib.new(algorithm)
    with requests.Session() as session:
        session.mount('https://', HTTPAdapter(max_retries=Retry(total=3, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504))))
        with session.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()
            with temporary.open('wb') as handle:
                for chunk in response.iter_content(1024 * 1024):
                    handle.write(chunk)
                    digest.update(chunk)
    if digest.hexdigest().lower() != expected.lower():
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f'Published {algorithm} did not match {url}')
    temporary.replace(destination)


def spec_digest(spec):
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


def _entry(path):
    return {'sha256': hash_file(path), 'bytes': path.stat().st_size}


def _inventory(directory):
    return {file.relative_to(directory).as_posix(): _entry(file) for file in sorted(directory.rglob('*')) if file.is_file()}


def verify_runtime(root=PROJECT_ROOT):
    root = Path(root).resolve()
    tools = root / '.tools'
    path = tools / 'runtime-manifest.json'
    if not path.is_file():
        raise RuntimeError('The verified project runtime is missing. Run npm run setup first.')
    receipt = json.loads(path.read_text(encoding='utf-8'))
    if receipt.get('spec_sha256') != spec_digest(runtime_lock(root)['windows-x64']):
        raise RuntimeError('The cached browser runtime does not match runtime-lock.json; use a matching package or a fresh cache.')
    required = {'waterfox/core/waterfox.exe', 'waterfox/core/application.ini', 'waterfox/core/xul.dll', 'waterfox/core/omni.ja', 'geckodriver.exe', 'licenses/MPL-2.0.txt'}
    if not required.issubset(receipt.get('files', {})):
        raise RuntimeError('The browser runtime manifest is incomplete')
    for name, expected in receipt['files'].items():
        file = (tools / name).resolve()
        if not file.is_relative_to(tools.resolve()) or not file.is_file() or file.stat().st_size != expected['bytes'] or hash_file(file) != expected['sha256']:
            raise RuntimeError(f'Cached browser runtime integrity failed: {name}')
    core = tools / 'waterfox/core'
    actual = {f'waterfox/core/{file.relative_to(core).as_posix()}' for file in core.rglob('*') if file.is_file()}
    recorded = {name for name in receipt['files'] if name.startswith('waterfox/core/')}
    if actual != recorded:
        raise RuntimeError('The browser runtime file inventory differs from its verified manifest')
    return receipt


def ensure_browser_runtime(root=PROJECT_ROOT, *, offline=False):
    root = Path(root).resolve()
    tools = root / '.tools'
    tools.mkdir(parents=True, exist_ok=True)
    if (tools / 'runtime-manifest.json').is_file():
        receipt = verify_runtime(root)
        print(f'Reusing project Waterfox {receipt["waterfox_version"]} and geckodriver {receipt["driver_version"]}', flush=True)
        return receipt
    if offline:
        raise RuntimeError('The packaged browser runtime or its verification manifest is missing; no download was attempted.')
    if platform.system() != 'Windows' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise RuntimeError('Bundled runtime provisioning currently supports Windows x64. Set DOPPELGNG_WATERFOX and DOPPELGNG_GECKODRIVER for explicit executables on other platforms.')
    spec = runtime_lock(root)['windows-x64']
    browser_spec, driver_spec = spec['waterfox'], spec['geckodriver']
    archive = tools / 'waterfox-setup.exe'
    driver_zip = tools / 'geckodriver.zip'
    print('Preparing the pinned private Waterfox runtime (first setup only)', flush=True)
    download(browser_spec['url'], archive, 'sha512', browser_spec['sha512'])
    download(driver_spec['url'], driver_zip, 'sha256', driver_spec['sha256'])
    sevenzip = shutil.which('7z') or r'C:\Program Files\7-Zip\7z.exe'
    if not Path(sevenzip).is_file():
        raise RuntimeError('Source-checkout setup needs 7-Zip to unpack Waterfox. The Windows distribution already contains the unpacked runtime and needs neither 7-Zip nor a Waterfox installation.')
    stage = Path(tempfile.mkdtemp(prefix='runtime-staging-', dir=tools)).resolve()
    try:
        subprocess.run([sevenzip, 'x', str(archive), f'-o{stage}', '-y'], check=True, stdout=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        extracted = stage / 'core'
        if not (extracted / 'waterfox.exe').is_file():
            raise RuntimeError('The official distribution did not contain its expected browser runtime')
        core = tools / 'waterfox/core'
        if core.exists():
            if _inventory(core) != _inventory(extracted):
                raise RuntimeError('The existing private browser differs from the verified distribution. Keep any local changes and use a fresh runtime cache.')
        else:
            core.parent.mkdir(exist_ok=True)
            shutil.copytree(extracted, core)
    finally:
        # Remove only this invocation's staging folder after checking its scope.
        if stage.parent == tools.resolve() and stage.name.startswith('runtime-staging-'):
            shutil.rmtree(stage)
    with zipfile.ZipFile(driver_zip) as zipped:
        binary = zipped.read('geckodriver.exe')
    driver = tools / 'geckodriver.exe'
    if driver.is_file() and driver.read_bytes() != binary:
        raise RuntimeError('The existing private geckodriver differs from the verified distribution')
    if not driver.is_file():
        driver.write_bytes(binary)
    license_file = tools / 'licenses/MPL-2.0.txt'
    download(driver_spec['license_url'], license_file, 'sha256', driver_spec['license_sha256'])
    ini = configparser.ConfigParser()
    ini.read(core / 'application.ini', encoding='utf-8')
    if ini.get('App', 'Name') != 'Waterfox':
        raise RuntimeError('The extracted application is not Waterfox')
    files = {f'waterfox/core/{name}': value for name, value in _inventory(core).items()}
    files['geckodriver.exe'] = _entry(driver)
    files['licenses/MPL-2.0.txt'] = _entry(license_file)
    receipt = {'schema': 1, 'platform': 'windows-x64', 'spec_sha256': spec_digest(spec), 'waterfox_version': browser_spec['version'], 'engine_version': ini.get('App', 'Version'), 'driver_version': driver_spec['version'], 'source_url': browser_spec['source_url'], 'files': files}
    for name, value in [('waterfox-provenance.json', browser_spec), ('geckodriver-provenance.json', driver_spec), ('runtime-manifest.json', receipt)]:
        (tools / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    return verify_runtime(root)


def provision(root=PROJECT_ROOT, *, offline=False):
    root = Path(root).resolve()
    override = os.environ.get('DOPPELGNG_CRAWLER')
    if override:
        from .crawler import load_crawler
        load_crawler(override)
        crawler = Path(override).resolve()
    else:
        crawler = ensure_crawler(root, offline=offline)
    browser = os.environ.get('DOPPELGNG_WATERFOX')
    driver = os.environ.get('DOPPELGNG_GECKODRIVER')
    if browser or driver:
        browser = Path(browser or root / '.tools/waterfox/core/waterfox.exe').resolve()
        driver = Path(driver or root / '.tools/geckodriver.exe').resolve()
        if not browser.is_file() or not driver.is_file():
            raise RuntimeError('The explicit browser/driver override is missing')
    else:
        ensure_browser_runtime(root, offline=offline)
        browser, driver = root / '.tools/waterfox/core/waterfox.exe', root / '.tools/geckodriver.exe'
    return {'crawler': str(crawler), 'waterfox': str(browser), 'geckodriver': str(driver)}


def main():
    parser = argparse.ArgumentParser(description='Prepare or verify pinned project dependencies')
    parser.add_argument('--offline', action='store_true', help='Verify bundled/cached dependencies without downloads or Git operations')
    args = parser.parse_args()
    print(json.dumps(provision(offline=args.offline), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, requests.RequestException) as error:
        raise SystemExit(f'Dependency setup failed: {error}')
