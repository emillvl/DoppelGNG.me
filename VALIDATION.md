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

## Managed dependencies and Windows distribution

- Managed crawler: sparse checkout of `https://github.com/emillvl/webcrawler` at pinned revision `435a46d903ed83105728b5f0c4ec11f45ee9c342`. A cold fetch and a second cached setup both succeeded. Selected source, requirements, documentation, license, and upstream tests are verified against `runtime-lock.json`.
- Project regression suite: **36 Python tests and 2 Node HTTP tests passed**. The pinned upstream crawler suite also passed **33 tests**: **71 tests in total**. The earlier crawler-integration milestone additionally passed its 28 Python and 2 Node tests using both the managed default and the original external crawler override.
- A complete live regression capture using the managed default completed **4 HTML pages and 1 download**, archived **10 resources**, and passed **24 desktop/mobile screenshot comparisons and 11 internal navigation checks**, including a route revealed by opening a menu. No explicit `--crawler` path was supplied.
- The private runtime is pinned to official Waterfox 6.7.6 and geckodriver 0.37.1. Publisher archive digests were checked before extraction. A manifest verifies **66 runtime and notice files**, including the complete 64-file browser core. Offline checks pass; missing DLLs, altered bytes, and unexpected browser files fail explicitly.
- Source setup ran twice successfully. The second run reused verified Python dependencies, crawler files, and browser files. Browser executables and their supporting libraries remain project-local; no system Waterfox installation was used.
- Built and verified `dist/doppelgng.me-windows-x64.zip`: **116 application and runtime files**, **175,988,892 bytes**. SHA256: `f73f410bf818fe46da74c9c6a28b92a5e2f23b30c3380a9bf407ea559ef75e02`. Each archived file was read back and checked against the embedded bundle manifest. A separate checksum file accompanies the ZIP.
- Extracted this ZIP into a clean project folder. `npm install`, fresh `npm run setup`, repeated setup, all 38 project tests, and all 33 upstream tests passed there. The packaged crawler and browser were reused without cloning or unpacking another browser.
- The extracted package's real headless Waterfox started successfully, rendered a test document, established exact 1280x800 and 390x844 content viewports, and enabled browser response-body collection. Dependency network requests and Git calls were forced to fail throughout this smoke check; neither was attempted.
- The distribution excludes Git metadata, virtual environments, browser profiles, installer archives, settings, and captured websites. Recipients still need Node.js 22+ and Python 3.10+; Python packages install on first setup. The prepared browser bundle supports Windows x64.

## Optional terminal crawler controls

- Added optional `--ignore-robots`, `--respect-robots`, `--checkpoint-every N`, and `-q`/`--quiet` flags. A command without these flags remains valid and retains the previous defaults. Conflicting robots choices and invalid checkpoint values fail before capture starts.
- Project regression suite: **46 Python tests and 2 Node HTTP tests passed**. The pinned upstream suite passed **33 tests** (**81 total**). All 46 Python tests additionally passed with the original external crawler override.
- Actual inherited checkpoint writes were verified at the selected three-page interval. An interval of zero suppressed periodic writes while retaining a working final save. Reconstruction recovery records and RAM-triggered offloading remain independent of this interval.
- Live terminal checks against an owned fixture with `Disallow: /` confirmed that the original command with no optional flags applied the default robots rule. An explicit `--respect-robots --checkpoint-every 0 --quiet` run also enforced the rule, emitted no progress output, and retained the error on stderr with exit code 1.
- Resumed that blocked capture with `--ignore-robots --checkpoint-every 3 -q`. It completed **4 HTML pages and 1 download**, archived **10 resources**, and passed **24 desktop/mobile screenshot comparisons and all 11 navigation checks**, including the menu-revealed route. Stdout contained exactly one final JSON result, stderr was empty, and the process exited 0. The manifest recorded all three selected settings. The original preview selection was restored and the test server was stopped.
- Rebuilt the Windows distribution with the optional flags and documentation: **117 application and runtime files**, **175,991,649 bytes**. SHA256: `cb5b721ec4444b1b9b18ffac9023d623a5c661623cd2eed29e2d9df1dc54f32f`. The archive's CLI, pipeline, CLI tests, and README were verified to match the tested working-tree files.

## Product-only terminal output

- Suppressed the upstream crawler's banners, checkpoint chatter, findings, and unconditional completion report in all modes. DoppelGNG.me retains its own extraction, verification, navigation progress, final result, and errors.
- **47 Python tests and 2 Node HTTP tests passed**. A real inherited crawl loop with a simulated extraction failure printed only branded product progress, propagated the failure, retained an incomplete manifest, and saved its internal checkpoint without announcing completion.

## Completion rules

No page is complete solely because HTML was downloaded or the server started. The pipeline distinguishes extracted, reconstructed, validated, complete, failed, and blocked states. Unsupported service operations, missing resources, untested controls, visual differences beyond the configured tolerance, and browser failures remain explicit failures. The tool does not claim support for every possible website or recover unavailable backend source.

All Git work is local. Browser runtimes, website responses, downloaded assets, generated npm projects, and screenshots are excluded from commits. No remote branches, pull requests, releases, or pushes were created.
