# doppelgng.me

A local website reconstruction pipeline for websites you own or have permission to reproduce. It integrates an existing `WebCrawler` project, extracts resources with headless Waterfox, keeps original source separate from rendered DOM, and verifies reconstructed pages before marking them complete.

## Development

Requires Node.js 22+, Python 3.10+, and the existing crawler directory containing `webcrawler.py` and `signatures.py`.

```text
npm install
npm run setup
npm test
```

`npm run setup` creates a virtual environment, installs Python dependencies, and provisions a checksum-verified Waterfox and geckodriver runtime under ignored `.tools/`. On Windows x64, 7-Zip is used to unpack the official browser distribution without a system installation. You can supply existing executables with `DOPPELGNG_WATERFOX` and `DOPPELGNG_GECKODRIVER`. Other platforms currently require those executable paths. Set `DOPPELGNG_PYTHON` if Python is not on PATH.

## Architecture and integration evidence

The inspected existing crawler is version 2.0.0: a Python `requests`/Beautiful Soup single-host crawler with a LIFO frontier, URL normalization and tracking-parameter removal, robots handling, Selenium/Chrome fallback, heuristic input analysis, and atomic JSON checkpoints. Its `FetchResult` contains HTML, discovered links, and an escalation flag; it does not archive dependencies, response bodies, rendered state, or screenshots.

`doppelgng.crawler` imports that project in place. Adapters inherit its URL discovery, analysis, robots policy, and crawl loop. Waterfox extraction, dependency closure, resumable storage, reconstruction, and validation are separate components. The original crawler and its configuration are not edited or copied into this repository. Source hashes provide integration provenance.

The previous crawler report is evidence of an earlier run only. Current extraction and validation must produce their own evidence. Browser-visible frontend code cannot recover unavailable server implementation or prove behavior that was not exercised. Uncaptured services and unsupported interaction states must remain explicit discrepancies.

## Version-control policy

Commits remain local. Never push, create remote branches, pull requests, or releases. `.doppelgng/`, browser runtimes, virtual environments, downloaded website data, screenshots, logs, and generated builds are ignored. Commit implementation, tests, documentation, and small factual validation summaries only.
