# Executed validation

This file contains factual milestone evidence. Full captured website data and browser artifacts stay under ignored `.doppelgng/`.

## Foundation

- Existing crawler: `WebCrawler` 2.0.0 loaded from the configured external directory, without modifying its source.
- Original crawler offline suite: **29 passed**.
- Headless runtime: official Waterfox 6.7.6, reporting Gecko/browser version 153.5.0; official geckodriver 0.37.1. Published download digests were verified.
- Executed browser smoke test: title, exact viewport, network events, and authentic response-body retrieval passed.

## Reusable pipeline milestone

- Implementation regression suite: **24 Python tests and 2 Node HTTP tests passed**.
- Independent owned regression website: **3 HTML pages and 1 download completed**, with 9 captured resources.
- The regression site exercises nested routes, a JavaScript-generated route, captured JSON requests, CSS imports and relative assets, a downloadable binary, a menu disclosure, and a native details control.
- Desktop 1440×900 and mobile 390×844 screenshots were executed at top, middle, and bottom positions. All 18 comparisons passed.
- Individual page validation, download byte equality, navigation clicks, route refresh, and cross-page integration passed.
- A second regression run using the saved baselines also completed successfully.
- Expanded independent regression: **4 HTML pages and 1 download completed**, with 10 resources and 24 passing desktop/mobile screenshot comparisons. The additional page is discoverable only after opening a menu; its route was discovered, reconstructed, and reached by an actual navigation click.
- Expanded cross-page regression: **11 internal links passed**, including anchors, route content, nested-route refresh, interaction-revealed navigation, and browser-error checks.
- Standalone generated project and exported `website+copied` project: `npm install` and `npm run dev` succeeded. Every served resource matched its recorded SHA256 (9 resources for the first project, 10 for the expanded export).
- Setup replay with pinned dependencies succeeded. Completed captures resumed without re-extracting validated pages.
- Real-site integration against the user-owned initial target remains in progress at this milestone. An individual-page pass is not a whole-site completion claim.

## Completion rules

No page is complete solely because HTML was downloaded or the server started. The pipeline distinguishes extracted, reconstructed, validated, complete, failed, and blocked states. Unsupported service operations, missing resources, untested controls, visual differences beyond the configured tolerance, and browser failures remain explicit failures. The tool does not claim support for every possible website or recover unavailable backend source.

All Git work is local. Browser runtimes, website responses, downloaded assets, generated npm projects, and screenshots are excluded from commits.
