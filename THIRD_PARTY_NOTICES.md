# Dependency notices

DoppelGNG.me source and documentation use the [MIT License](LICENSE). Dependencies retain their own copyrights, licenses, and notices. The Windows bundle preserves the complete browser core and its embedded notices.

## WebCrawler

Project: [emillvl/webcrawler](https://github.com/emillvl/webcrawler). License: MIT. Copyright: 2026 Emil.

The selected revision is `435a46d903ed83105728b5f0c4ec11f45ee9c342`, pinned with individual file hashes in [runtime-lock.json](runtime-lock.json). The selected source, requirements, README, license, and upstream tests remain unmodified under `.tools/webcrawler/`. The bundle includes the original license at `.tools/webcrawler/LICENSE` and the `upstream.json` receipt.

## Waterfox

The bundle contains the official Waterfox 6.7.6 Windows x64 core at `.tools/waterfox/core/`. The recorded engine version is 153.5.0. The pinned archive URL and SHA512 are in [runtime-lock.json](runtime-lock.json).

Corresponding source: [BrowserWorks/waterfox at 1de140d004d3fd63a2b63564b2ed4ea26f0adc97](https://github.com/BrowserWorks/waterfox/tree/1de140d004d3fd63a2b63564b2ed4ea26f0adc97). Waterfox includes MPL-covered code and other components with their own terms. Its complete license notices are retained inside the browser distribution and are accessible through `about:license`. The application does not replace them with MIT terms or alter the browser files. The exact source link is also retained in `.tools/runtime-manifest.json` and `.tools/waterfox-provenance.json`.

## geckodriver

Project and corresponding source: [mozilla/geckodriver v0.37.1](https://github.com/mozilla/geckodriver/tree/v0.37.1). License: Mozilla Public License 2.0.

The binary is included at `.tools/geckodriver.exe`. Its license text is included at `.tools/licenses/MPL-2.0.txt`. [runtime-lock.json](runtime-lock.json) pins the archive SHA256 and license-text SHA256. Provenance is retained in `.tools/geckodriver-provenance.json`.

## Python packages

Direct dependencies are requests, Beautiful Soup, psutil, Selenium, Pillow, tinycss2, and websocket-client. Exact versions, including transitive dependencies, are listed in [requirements.lock.txt](requirements.lock.txt).

Setup installs packages into the recipient's Python environment. The distribution ZIP does not bundle that environment. Installed distributions retain their license files and metadata. Review those notices when redistributing an environment or changing dependency versions.

## Captured websites and copied projects

Captured responses, website code, images, fonts, and other target assets retain their existing rights. Permission to use DoppelGNG.me does not grant permission to copy those assets. A copied website contains the target's captured frontend and the application's replay server. It does not contain Waterfox or need the crawler for local serving.

New captures and exported projects carry the replay server's MIT notice in `DOPPELGNG_LICENSE.txt`. That notice does not relicense captured assets.

Keep this file, the application license, dependency notices, and corresponding-source references with redistributed application bundles. See [distribution and licensing](docs/distribution.md).
