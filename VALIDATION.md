# Executed validation

This file contains factual milestone evidence. Full captured website data and browser artifacts stay under ignored `.doppelgng/`.

## Foundation

- Existing crawler: `WebCrawler` 2.0.0 loaded from the configured external directory, without modifying its source.
- Original crawler offline suite: **29 passed**.
- Headless runtime: official Waterfox 6.7.6, reporting Gecko/browser version 153.5.0; official geckodriver 0.37.1. Published download digests were verified.
- Executed browser smoke test: title, exact viewport, network events, and authentic response-body retrieval passed.

## Reusable pipeline milestone

- Implementation regression suite: **25 Python tests and 2 Node HTTP tests passed**.
- Independent owned regression website: **3 HTML pages and 1 download completed**, with 9 captured resources.
- The regression site exercises nested routes, a JavaScript-generated route, captured JSON requests, CSS imports and relative assets, a downloadable binary, a menu disclosure, and a native details control.
- Desktop 1440×900 and mobile 390×844 screenshots were executed at top, middle, and bottom positions. All 18 comparisons passed.
- Individual page validation, download byte equality, navigation clicks, route refresh, and cross-page integration passed.
- A second regression run using the saved baselines also completed successfully.
- Expanded independent regression: **4 HTML pages and 1 download completed**, with 10 resources and 24 passing desktop/mobile screenshot comparisons. The additional page is discoverable only after opening a menu; its route was discovered, reconstructed, and reached by an actual navigation click.
- Expanded cross-page regression: **11 internal links passed**, including anchors, route content, nested-route refresh, interaction-revealed navigation, and browser-error checks.
- Standalone generated project and exported `website+copied` project: `npm install` and `npm run dev` succeeded. Every served resource matched its recorded SHA256 (9 resources for the first project, 10 for the expanded export).
- Setup replay with pinned dependencies succeeded. Completed captures resumed without re-extracting validated pages.

## Real-site acceptance: emilvaliyev.com

- **12 HTML pages and 7 downloadable resources completed**; all 19 discovered in-scope entries have the `complete` state.
- **111 resources archived and reconstructed**, with no original or local integrity failures.
- **72 of 72 screenshot comparisons passed** across 1440×900 and 390×844 content viewports at top, middle, and bottom positions. Measured maximum changed-pixel ratio and mean channel difference were both zero for these captured states.
- **80 of 80 internal navigation checks passed**, including keyboard-revealed skip links, scroll-activated navigation, anchors, client-side routing, route content, direct nested-route refresh, console monitoring, and network checks.
- Seven downloads passed original/local byte equality checks. Original HTML and rendered DOM are stored separately; authentic scripts, CSS, fonts, assets, and browser-observed route data are retained.
- The optional `/sitemap.xml` probe returned 404; this observation is recorded. Discovery exhausted the original/rendered internal-link frontier without silently skipping an in-scope page.
- A same-route home-link check initially compared different scroll states. The validator now establishes the baseline's scroll position before its content comparison. The failing edge was retested successfully; the other 79 passing checks were retained against unchanged, hash-verified resource files.
- The original crawler's two source hashes remained unchanged throughout the run. No target hostname appears in the general implementation.
- **Delivered folder:** `emilvaliyev.com+copied/`. Export verified the complete copied archive. `npm install` and `npm run dev` succeeded inside this folder; all 111 HTTP-served resources matched their validated SHA256 hashes.
- A nested article in the delivered folder passed an additional six Waterfox desktop/mobile screenshot, content, font, network, and refresh checks, with no browser errors.
- No remaining discrepancy was observed within these tested routes and states. This is not evidence for unexercised backend services or every possible website.

## Completion rules

No page is complete solely because HTML was downloaded or the server started. The pipeline distinguishes extracted, reconstructed, validated, complete, failed, and blocked states. Unsupported service operations, missing resources, untested controls, visual differences beyond the configured tolerance, and browser failures remain explicit failures. The tool does not claim support for every possible website or recover unavailable backend source.

All Git work is local. Browser runtimes, website responses, downloaded assets, generated npm projects, and screenshots are excluded from commits. No remote branches, pull requests, releases, or pushes were created.
