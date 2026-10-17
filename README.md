# doppelgng.me

A local website reconstruction pipeline for websites you own or have permission to reproduce. It integrates an existing `WebCrawler` project, extracts resources with headless Waterfox, keeps original source separate from rendered DOM, and verifies reconstructed pages before marking them complete.

## Development

Requires Node.js 22+ and Python 3.10+. The first setup from a source checkout also needs Git.

```text
npm install
npm run setup
npm test
```

`npm run setup` creates a virtual environment, installs Python dependencies, and fetches only the required files from [emillvl/webcrawler](https://github.com/emillvl/webcrawler) into `.tools/webcrawler/`. The revision and file hashes are pinned in `runtime-lock.json`; verified cached files are reused without another clone. Source, requirements, license, documentation, and upstream regression tests are retained. `--crawler` or `DOPPELGNG_CRAWLER` remains available as an explicit override.

Setup provisions the pinned Waterfox and geckodriver runtime under ignored `.tools/` once. It verifies and reuses the complete cached runtime on subsequent runs, and also reuses already-verified Python dependencies. A separate Waterfox installation is never required. Source-checkout setup on Windows x64 uses 7-Zip to unpack the official distribution. You can supply existing executables with `DOPPELGNG_WATERFOX` and `DOPPELGNG_GECKODRIVER`. Other platforms currently require those executable paths. Set `DOPPELGNG_PYTHON` if Python is not on PATH.

The Waterfox installer is unpacked without being run. DoppelGNG.me disables automatic Private Browsing shortcuts and default-browser prompts in its temporary browser profiles, so runtime launches do not add a Waterfox app to the Start menu. The intact engine remains an internal dependency; manually opening its executable can still start Waterfox.

On Windows NTFS drives, setup automatically applies LZX compression to the verified private browser files. The tested runtime uses approximately **176 MB on disk**, while its logical size remains 544 MB. Repeated setup reuses the compressed files; `runtime:check` remains read-only. Other filesystems keep the verified runtime uncompressed. No additional command or flag is needed.

## Distribute the tool with Waterfox included

```text
npm run setup
npm run package
```

This creates `dist/doppelgng.me-windows-x64.zip` and a SHA256 checksum file. The ZIP already includes the pinned crawler files, complete Waterfox runtime, geckodriver, integrity manifests, and license notices. It excludes Git history, virtual environments, downloaded websites, user settings, browser profiles, installer archives, and copied-site output.

Recipients extract the ZIP, open a terminal in its `DoppelGNG.me` folder, and run `npm install` followed by `npm run setup`. Node.js 22+ and Python 3.10+ are prerequisites. Python packages install on first setup, while the included crawler and browser are verified and reused; recipients need neither Git, 7-Zip, nor a Waterfox installation. Browser binaries remain outside source commits and travel inside this distribution artifact.

`npm run runtime:check` verifies the cached or bundled crawler and browser without network access. It fails clearly if a required runtime file is missing or altered. See `THIRD_PARTY_NOTICES.md` for included dependency notices.

## Reconstruct an authorized website

```text
npm run crawl -- --url https://your-authorized-site.example --authorized
npm run status
npm run dev
```

Open the printed local address. Internal pages, scripts, fonts, images, captured GET data, and downloads are served from the archive. The replay server has no network fallback. By default, a capture creates a separate directory named after the actual website domain, for example `example.com` or `www.another.org`. Each output is a standalone npm project: change into that directory, run `npm install`, then `npm run dev`. An unrelated existing folder is never overwritten.

Use `--output <directory>` to keep multiple captures. Repeat the same capture command to resume; intact validated pages are retained, and failed or corrupt pages are retried. Separate workspaces cannot overwrite each other while an operation owns the workspace lock. The crawler records same-origin links from original HTML, rendered DOM, and sitemap indexes; scrolling discovers lazy assets and browser-driven prefetch dependencies.

Existing folders from earlier versions keep their names. Supply their existing path with `--output` to resume them.

These crawler controls are optional additions to the capture command. The existing command works without any of them:

```text
npm run crawl -- --url https://your-authorized-site.example --authorized --ignore-robots --checkpoint-every 25 -q
npm run crawl -- --help
```

| Option | Behavior |
| --- | --- |
| `--ignore-robots` | Skip loading and applying robots.txt rules for this capture. |
| `--respect-robots` | Apply robots.txt rules; this is the default. Cannot be combined with `--ignore-robots`. |
| `--checkpoint-every N` | Save the upstream crawler's state every N processed pages. Default: 1. Use 0 to disable periodic checkpoint saves. Final saves, RAM-triggered offloading, and reconstruction recovery records remain enabled. |
| `-q`, `--quiet` | Suppress DoppelGNG.me's extraction, validation, and navigation progress. The final JSON result and errors remain visible. Use `npm --silent run crawl -- ... -q` to suppress npm's own command banner too. |

These choices are recorded in the capture manifest's `policy`. Repeat the flags when resuming a capture. Omitting them preserves the existing defaults: respect robots.txt, checkpoint every page, and show progress.

Terminal output belongs to DoppelGNG.me. The upstream crawler's banners, state-save messages, security findings, and completion report are suppressed in every mode; its checkpoint files remain internal recovery data. A product completion result is printed only after reconstruction and validation finish.

`--viewport 1440x900 --viewport 390x844` selects exact content viewport sizes. Defaults are those two sizes. Original and local screenshots are compared at the top, middle, and bottom of every page. Default failure threshold is more than 1% of pixels differing by more than 25 in any RGB channel; measured differences and diff images are retained. This tolerance is configurable with `--visual-tolerance`, and recorded in the manifest.

```text
npm run validate -- --output example.com
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

To deliver an existing completed capture in a separate folder:

```text
npm run export -- --output /path/to/capture
```

This creates a folder named after the actual website domain, or the folder selected with `--destination`. Export verifies copied resource hashes and refuses to overwrite an existing folder. Incomplete reconstructions cannot be exported as completed projects. Domain-named output folders remain excluded from Git.

## Evidence and limits

Each capture contains `manifest.json`, untouched content-addressed `raw/` responses, reconstructed `site/` resources, original crawler checkpoints, and `artifacts/` with original DOM, sanitized network logs, screenshots, differences, interaction evidence, and page results. The manifest records URL mappings, dependencies, content hashes, request provenance, page states, scope, visual tolerances, and integration results. The local `/__doppelgng__/report` endpoint exposes this evidence as JSON.

A page is first marked `validated` after its individual checks pass. It becomes `complete` only after cross-page integration passes. A failed extraction or validation stops the crawl and leaves an explicit incomplete checkpoint. Reports from the original crawler alone are not completion evidence.

The product supports reusable frontend capture, not recovery of arbitrary backend source. Login flows, payments, mutations, unexercised application states, WebSockets, live streaming, DRM, and unavailable authenticated services are not proven by a visual match. JavaScript discovery combines explicit module/worker references with actual browser network traffic. Arbitrary URL-like strings and computed URL fragments are not downloaded as invented dependencies; observed complete asset URLs can be rewritten for replay. Computed routes and hidden interactions may need scenarios. Automatic runtime provisioning is Windows x64 at present. No third-party website is authorized merely because the tool can access it.

## Architecture and integration evidence

The inspected existing crawler is version 2.0.0: a Python `requests`/Beautiful Soup single-host crawler with a LIFO frontier, URL normalization and tracking-parameter removal, robots handling, Selenium/Chrome fallback, heuristic input analysis, and atomic JSON checkpoints. Its `FetchResult` contains HTML, discovered links, and an escalation flag; it does not archive dependencies, response bodies, rendered state, or screenshots.

`doppelgng.crawler` imports the managed, pinned upstream files by default, or an explicitly configured crawler in place. Adapters inherit its URL discovery, analysis, robots policy, and crawl loop. Waterfox extraction, dependency closure, resumable storage, reconstruction, and validation are separate components. The current upstream uses a deduplicated FIFO frontier; the adapter also supports the original local crawler's LIFO frontier. No upstream source is rewritten, and the original external crawler and its Git configuration remain untouched. Source hashes provide integration provenance.

The previous crawler report is evidence of an earlier run only. Current extraction and validation must produce their own evidence. Browser-visible frontend code cannot recover unavailable server implementation or prove behavior that was not exercised. Uncaptured services and unsupported interaction states must remain explicit discrepancies.

## Version-control policy

Commits remain local. Never push, create remote branches, pull requests, or releases. `.doppelgng/`, browser runtimes, virtual environments, downloaded website data, screenshots, logs, and generated builds are ignored. Commit implementation, tests, documentation, and small factual validation summaries only.
