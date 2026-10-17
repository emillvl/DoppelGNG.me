"""Provision a private Waterfox runtime without a system browser installation."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import zipfile

import requests
from bs4 import BeautifulSoup


TOOLS = Path('.tools').resolve()


def download(url: str, destination: Path, algorithm: str, expected: str):
    digest = hashlib.new(algorithm)
    temporary = destination.with_suffix(destination.suffix + '.part')
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with temporary.open('wb') as handle:
            for chunk in response.iter_content(1024 * 1024):
                handle.write(chunk)
                digest.update(chunk)
    if digest.hexdigest().lower() != expected.lower():
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f'Published {algorithm} did not match {url}')
    temporary.replace(destination)


def main():
    TOOLS.mkdir(exist_ok=True)
    configured = os.environ.get('DOPPELGNG_WATERFOX')
    binary = Path(configured).resolve() if configured else TOOLS / 'waterfox' / 'core' / 'waterfox.exe'
    driver = Path(os.environ.get('DOPPELGNG_GECKODRIVER', TOOLS / 'geckodriver.exe')).resolve()
    if not binary.is_file():
        if platform.system() != 'Windows' or platform.machine().lower() not in ('amd64', 'x86_64'):
            raise RuntimeError('Automatic provisioning currently supports Windows x64. Set DOPPELGNG_WATERFOX and DOPPELGNG_GECKODRIVER on other platforms.')
        response = requests.get('https://www.waterfox.com/download/', timeout=40)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=re.compile(r'/WINNT_x86_64/.*\.exe$'))
        if not links:
            raise RuntimeError('Official Waterfox x64 download link was not found')
        url = links[0]['href']
        filename = TOOLS / 'waterfox-setup.exe'
        expected = None
        # Hero links have no checksum; the artifact list repeats the same URL.
        for link in links:
            section = link
            for _ in range(4):
                values = re.findall(r'[a-fA-F0-9]{128}', str(section))
                if len(set(values)) == 1:
                    expected = values[0]
                    break
                section = section.parent
            if expected:
                break
        if not expected:
            raise RuntimeError('Cannot unambiguously match the official Waterfox checksum')
        print(f'Downloading verified Waterfox to {TOOLS}', flush=True)
        download(url, filename, 'sha512', expected)
        sevenzip = shutil.which('7z') or r'C:\Program Files\7-Zip\7z.exe'
        if not Path(sevenzip).is_file():
            raise RuntimeError('7-Zip is needed to unpack Waterfox without installing it; set DOPPELGNG_WATERFOX to an existing executable instead.')
        subprocess.run([sevenzip, 'x', str(filename), f'-o{TOOLS / "waterfox"}', '-y'], check=True, stdout=subprocess.DEVNULL)
        if not binary.is_file():
            raise RuntimeError('Extracted Waterfox executable was not found')
        (TOOLS / 'waterfox-provenance.json').write_text(json.dumps({'url': url, 'sha512': expected}, indent=2))
    if not driver.is_file():
        release = requests.get('https://api.github.com/repos/mozilla/geckodriver/releases/latest', timeout=40)
        release.raise_for_status()
        asset = next(a for a in release.json()['assets'] if a['name'].endswith('-win64.zip'))
        digest = asset.get('digest', '')
        if not digest.startswith('sha256:'):
            raise RuntimeError('GitHub did not publish the geckodriver asset digest')
        archive = TOOLS / 'geckodriver.zip'
        download(asset['browser_download_url'], archive, 'sha256', digest.split(':')[1])
        with zipfile.ZipFile(archive) as zipped:
            with zipped.open('geckodriver.exe') as source, driver.open('wb') as target:
                shutil.copyfileobj(source, target)
        (TOOLS / 'geckodriver-provenance.json').write_text(json.dumps({'url': asset['browser_download_url'], 'digest': digest}, indent=2))
    print(json.dumps({'waterfox': str(binary), 'geckodriver': str(driver)}, indent=2))


if __name__ == '__main__':
    main()
