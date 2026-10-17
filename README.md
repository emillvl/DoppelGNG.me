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

## Reconstruct an authorized website

```text
npm run crawl -- --url https://your-authorized-site.example --authorized --crawler /path/to/WebCrawler
npm run status
npm run dev
```

Open the printed local address. Internal pages, scripts, fonts, images, captured GET data, and downloads are served from the archive. The replay server has no network fallback. Every output is also a standalone npm project: change into its output directory, run `npm install`, then `npm run dev`.

Use `--output <directory>` to keep multiple captures. Repeat the same capture command to resume; intact validated pages are retained, and failed or corrupt pages are retried. Separate workspaces cannot overwrite each other while an operation owns the workspace lock. The crawler records same-origin links from original HTML, rendered DOM, and sitemap indexes; scrolling discovers lazy assets and browser-driven prefetch dependencies.

`--viewport 1440x900 --viewport 390x844` selects exact content viewport sizes. Defaults are those two sizes. Original and local screenshots are compared at the top, middle, and bottom of every page. Default failure threshold is more than 1% of pixels differing by more than 25 in any RGB channel; measured differences and diff images are retained. This tolerance is configurable with `--visual-tolerance`, and recorded in the manifest.

```text
npm run validate -- --output .doppelgng/your-capture
```

Validation checks content, typography, image loading, responsive dimensions, link inventory, controls, browser errors, network responses, screenshots, direct route refresh, and internal navigation clicks. Disclosure controls are discovered automatically. Other controls require explicit read-only interaction scenarios, for example:

```json
{
  "/catalogue/": [
    { "action": "click", "selector": "#filter-toggle", "assert_selector": "#filters" },
    { "action": "hover", "selector": ".menu-trigger", "assert_selector": ".submenu" }
  ]
}
```

Pass the file with `--scenarios scenarios.json`. Supported actions are `click`, `hover`, and `details`. Scenarios compare original and local state and screenshots. Forms are not submitted against the original website. Unknown interactive controls prevent a successful page-completion claim. Configure real service integrations separately where behavior depends on server-side state; unrecorded non-GET operations return an explicit 501 response locally.

## Evidence and limits

Each capture contains `manifest.json`, untouched content-addressed `raw/` responses, reconstructed `site/` resources, original crawler checkpoints, and `artifacts/` with original DOM, sanitized network logs, screenshots, differences, interaction evidence, and page results. The manifest records URL mappings, dependencies, content hashes, request provenance, page states, scope, visual tolerances, and integration results. The local `/__doppelgng__/report` endpoint exposes this evidence as JSON.

A page is first marked `validated` after its individual checks pass. It becomes `complete` only after cross-page integration passes. A failed extraction or validation stops the crawl and leaves an explicit incomplete checkpoint. Reports from the original crawler alone are not completion evidence.

The product supports reusable frontend capture, not recovery of arbitrary backend source. Login flows, payments, mutations, unexercised application states, WebSockets, live streaming, DRM, and unavailable authenticated services are not proven by a visual match. JavaScript discovery combines literal module/resource references with actual browser network traffic; computed routes and hidden interactions may need scenarios. Automatic runtime provisioning is Windows x64 at present. No third-party website is authorized merely because the tool can access it.

## Architecture and integration evidence

The inspected existing crawler is version 2.0.0: a Python `requests`/Beautiful Soup single-host crawler with a LIFO frontier, URL normalization and tracking-parameter removal, robots handling, Selenium/Chrome fallback, heuristic input analysis, and atomic JSON checkpoints. Its `FetchResult` contains HTML, discovered links, and an escalation flag; it does not archive dependencies, response bodies, rendered state, or screenshots.

`doppelgng.crawler` imports that project in place. Adapters inherit its URL discovery, analysis, robots policy, and crawl loop. Waterfox extraction, dependency closure, resumable storage, reconstruction, and validation are separate components. The original crawler and its configuration are not edited or copied into this repository. Source hashes provide integration provenance.

The previous crawler report is evidence of an earlier run only. Current extraction and validation must produce their own evidence. Browser-visible frontend code cannot recover unavailable server implementation or prove behavior that was not exercised. Uncaptured services and unsupported interaction states must remain explicit discrepancies.

## Version-control policy

Commits remain local. Never push, create remote branches, pull requests, or releases. `.doppelgng/`, browser runtimes, virtual environments, downloaded website data, screenshots, logs, and generated builds are ignored. Commit implementation, tests, documentation, and small factual validation summaries only.
