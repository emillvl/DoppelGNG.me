# Distribution and licensing

## Build the Windows bundle

```sh
npm run setup
npm run runtime:check
npm run package
```

The packager produces:

```text
dist/doppelgng.me-windows-x64.zip
dist/doppelgng.me-windows-x64.zip.sha256
```

Choose another filename with `npm run package -- --output dist/custom.zip`. Packaging verifies the managed crawler and browser offline before writing the ZIP. It reads every archived file back and compares its SHA256 with the recorded inventory before publishing the final ZIP and checksum file. Packaging does not create a GitHub release or upload the archive.

The archive has a top-level `DoppelGNG.me/` directory containing application source, scripts, tests, documentation and screenshots, the MIT license, dependency notices, lockfiles, the selected crawler files, complete Waterfox core, geckodriver, provenance receipts, and `bundle-manifest.json`.

The bundle manifest records each file's SHA256 and byte count. Its prerequisites remain Node.js 22+ and Python 3.10+. The Python environment is not bundled. The browser/crawler binaries are included in the ZIP and excluded from source commits.

The explicit packaging allowlist excludes `.git/`, `.venv/`, npm caches, installer archives, browser profiles, compression receipts, `.env` files, downloaded websites, captures, benchmark evidence, and generated QA output. Adding a file to Git does not automatically add it to a distribution. Source documentation and documentation assets have their own allowed extensions.

Overrides used for capture do not replace the runtime included by the packager. Packaging requires the managed pinned crawler and Windows browser inventory. It is a Windows x64 distribution, even when invoked from a different host with those files available.

## Verify a downloaded ZIP

In PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 .\doppelgng.me-windows-x64.zip
Get-Content .\doppelgng.me-windows-x64.zip.sha256
```

The hash must match the first field in the checksum file. A checksum detects changed bytes relative to that file; obtain both from the expected distributor. After extraction, `npm run runtime:check` verifies the managed runtime inventory and crawler against the project pins.

Historical checksums in the reports identify earlier local builds. They are not checksums for a newly generated archive.

## Recipient setup

Extract the ZIP, open a terminal in `DoppelGNG.me/`, then run:

```sh
npm install
npm run setup
npm run runtime:check
```

Recipients need Node.js and Python. They do not need Git, 7-Zip, or an installed browser because the selected crawler and unpacked runtime are already present. Initial setup still downloads the pinned Python packages. A verified cache is reused on later runs.

ZIP extraction does not preserve NTFS LZX storage. On Windows NTFS, setup applies compression to the included verified browser files. The logical contents and file hashes stay the same. Other filesystems retain the uncompressed runtime.

The application's distribution ZIP is different from a copied website. A website export contains that capture and the Node replay server; it excludes Python and browser runtimes. See [export](getting-started.md#export).

## License choice

The project's source and documentation use the [MIT License](../LICENSE), a permissive license that requires retaining its copyright and license notice. It matches the managed WebCrawler's MIT license and keeps this local utility straightforward to reuse. [GitHub's MIT summary](https://choosealicense.com/licenses/mit/) describes its permissions and conditions.

Waterfox, geckodriver, and their dependencies retain their own terms. The application license does not relicense them. Their bundled notices and corresponding source locations are recorded in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). Mozilla's [MPL FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/) explains distribution of unchanged executables and the MPL's file-level scope.

Keep notices and source references with a redistributed runtime. If you modify a dependency, review the obligations for that dependency before distributing the changed files. Captured website assets keep their existing rights; the application license grants no permission to reproduce someone else's website.
