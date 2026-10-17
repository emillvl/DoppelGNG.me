# Executed validation

Historical milestone records. Counts, folder names, and build hashes describe each milestone. Generated browser artifacts and captured websites remain in ignored local directories.

## Foundation

- Existing crawler: `WebCrawler` 2.0.0 loaded from the configured external directory, without modifying its source.
- Original crawler offline suite: 29 passed.
- Headless runtime: official Waterfox 6.7.6, reporting Gecko/browser version 153.5.0; official geckodriver 0.37.1. Published download digests were verified.
- Executed browser smoke test: title, exact viewport, network events, and authentic response-body retrieval passed.

## Reusable pipeline milestone

- Implementation regression suite: 25 Python tests and 2 Node HTTP tests passed.
- Independent owned regression website: 3 HTML pages and 1 download completed, with 9 captured resources.
- The regression site exercises nested routes, a JavaScript-generated route, captured JSON requests, CSS imports and relative assets, a downloadable binary, a menu disclosure, and a native details control.
- Desktop 1440×900 and mobile 390×844 screenshots were executed at top, middle, and bottom positions. All 18 comparisons passed.
- Individual page validation, download byte equality, navigation clicks, route refresh, and cross-page integration passed.
- A second regression run using the saved baselines also completed successfully.
- Expanded independent regression: 4 HTML pages and 1 download completed, with 10 resources and 24 passing desktop/mobile screenshot comparisons. The additional page is discoverable only after opening a menu; its route was discovered, reconstructed, and reached by an actual navigation click.
- Expanded cross-page regression: 11 internal links passed, including anchors, route content, nested-route refresh, interaction-revealed navigation, and browser-error checks.
- Standalone generated project and exported `website+copied` project: `npm install` and `npm run dev` succeeded. Every served resource matched its recorded SHA256 (9 resources for the first project, 10 for the expanded export).
- Setup replay with pinned dependencies succeeded. Completed captures resumed without re-extracting validated pages.

## Real-site acceptance: emilvaliyev.com

- 12 HTML pages and 7 downloadable resources completed; all 19 discovered in-scope entries have the `complete` state.
- 111 resources archived and reconstructed, with no original or local integrity failures.
- 72 of 72 screenshot comparisons passed across 1440×900 and 390×844 content viewports at top, middle, and bottom positions. Measured maximum changed-pixel ratio and mean channel difference were both zero for these captured states.
- 80 of 80 internal navigation checks passed, including keyboard-revealed skip links, scroll-activated navigation, anchors, client-side routing, route content, direct nested-route refresh, console monitoring, and network checks.
- Seven downloads passed original/local byte equality checks. Original HTML and rendered DOM are stored separately; authentic scripts, CSS, fonts, assets, and browser-observed route data are retained.
- The optional `/sitemap.xml` probe returned 404; this observation is recorded. Discovery exhausted the original/rendered internal-link frontier without silently skipping an in-scope page.
- A same-route home-link check initially compared different scroll states. The validator now establishes the baseline's scroll position before its content comparison. The failing edge was retested successfully; the other 79 passing checks were retained against unchanged, hash-verified resource files.
- The original crawler's two source hashes remained unchanged throughout the run. No target hostname appears in the general implementation.
- Delivered folder: `emilvaliyev.com+copied/`. Export verified the complete copied archive. `npm install` and `npm run dev` succeeded inside this folder; all 111 HTTP-served resources matched their validated SHA256 hashes.
- A nested article in the delivered folder passed an additional six Waterfox desktop/mobile screenshot, content, font, network, and refresh checks, with no browser errors.
- No remaining discrepancy was observed within these tested routes and states. This is not evidence for unexercised backend services or every possible website.

## Managed dependencies and Windows distribution

- Managed crawler: sparse checkout of `https://github.com/emillvl/webcrawler` at pinned revision `435a46d903ed83105728b5f0c4ec11f45ee9c342`. A cold fetch and a second cached setup both succeeded. Selected source, requirements, documentation, license, and upstream tests are verified against `runtime-lock.json`.
- Project regression suite: 36 Python tests and 2 Node HTTP tests passed. The pinned upstream crawler suite also passed 33 tests: 71 tests in total. The earlier crawler-integration milestone additionally passed its 28 Python and 2 Node tests using both the managed default and the original external crawler override.
- A complete live regression capture using the managed default completed 4 HTML pages and 1 download, archived 10 resources, and passed 24 desktop/mobile screenshot comparisons and 11 internal navigation checks, including a route revealed by opening a menu. No explicit `--crawler` path was supplied.
- The private runtime is pinned to official Waterfox 6.7.6 and geckodriver 0.37.1. Publisher archive digests were checked before extraction. A manifest verifies 66 runtime and notice files, including the complete 64-file browser core. Offline checks pass; missing DLLs, altered bytes, and unexpected browser files fail explicitly.
- Source setup ran twice successfully. The second run reused verified Python dependencies, crawler files, and browser files. Browser executables and their supporting libraries remain project-local; no system Waterfox installation was used.
- Built and verified `dist/doppelgng.me-windows-x64.zip`: 116 application and runtime files, 175,988,892 bytes. SHA256: `f73f410bf818fe46da74c9c6a28b92a5e2f23b30c3380a9bf407ea559ef75e02`. Each archived file was read back and checked against the embedded bundle manifest. A separate checksum file accompanies the ZIP.
- Extracted this ZIP into a clean project folder. `npm install`, fresh `npm run setup`, repeated setup, all 38 project tests, and all 33 upstream tests passed there. The packaged crawler and browser were reused without cloning or unpacking another browser.
- The extracted package's real headless Waterfox started successfully, rendered a test document, established exact 1280x800 and 390x844 content viewports, and enabled browser response-body collection. Dependency network requests and Git calls were forced to fail throughout this smoke check; neither was attempted.
- The distribution excludes Git metadata, virtual environments, browser profiles, installer archives, settings, and captured websites. Recipients still need Node.js 22+ and Python 3.10+; Python packages install on first setup. The prepared browser bundle supports Windows x64.

## Optional terminal crawler controls

- Added optional `--ignore-robots`, `--respect-robots`, `--checkpoint-every N`, and `-q`/`--quiet` flags. A command without these flags remains valid and retains the previous defaults. Conflicting robots choices and invalid checkpoint values fail before capture starts.
- Project regression suite: 46 Python tests and 2 Node HTTP tests passed. The pinned upstream suite passed 33 tests (81 total). All 46 Python tests additionally passed with the original external crawler override.
- Actual inherited checkpoint writes were verified at the selected three-page interval. An interval of zero suppressed periodic writes while retaining a working final save. Reconstruction recovery records and RAM-triggered offloading remain independent of this interval.
- Live terminal checks against an owned fixture with `Disallow: /` confirmed that the original command with no optional flags applied the default robots rule. An explicit `--respect-robots --checkpoint-every 0 --quiet` run also enforced the rule, emitted no progress output, and retained the error on stderr with exit code 1.
- Resumed that blocked capture with `--ignore-robots --checkpoint-every 3 -q`. It completed 4 HTML pages and 1 download, archived 10 resources, and passed 24 desktop/mobile screenshot comparisons and all 11 navigation checks, including the menu-revealed route. Stdout contained exactly one final JSON result, stderr was empty, and the process exited 0. The manifest recorded all three selected settings. The original preview selection was restored and the test server was stopped.
- Rebuilt the Windows distribution with the optional flags and documentation: 117 application and runtime files, 175,991,649 bytes. SHA256: `cb5b721ec4444b1b9b18ffac9023d623a5c661623cd2eed29e2d9df1dc54f32f`. The archive's CLI, pipeline, CLI tests, and README were verified to match the tested working-tree files.

## Product-only terminal output

- Suppressed the upstream crawler's banners, checkpoint chatter, findings, and unconditional completion report in all modes. DoppelGNG.me retains its own extraction, verification, navigation progress, final result, and errors.
- 47 Python tests and 2 Node HTTP tests passed. A real inherited crawl loop with a simulated extraction failure printed only branded product progress, propagated the failure, retained an incomplete manifest, and saved its internal checkpoint without announcing completion.

## Computed resource URL regression

- Diagnosed the reported post-copy failure from the existing captured resources. The saved advertising loader builds a versioned URL from a prefix and `/pubads_impl.js`; the previous parser interpreted that suffix as a standalone dependency and requested a nonexistent URL. The existing folder already contained copied website files when this extra dependency lookup failed.
- Arbitrary JavaScript URL-like strings now require browser request evidence. Explicit imports and complete worker/module asset references remain discoverable; computed import prefixes and split URL fragments are preserved. Captured full URL literals can still be rewritten for local replay. Real missing imports and explicitly referenced external scripts still fail extraction.
- 53 Python tests, 2 Node HTTP tests, and 33 pinned upstream tests passed (88 total). All 53 Python tests additionally passed with the original external crawler override.
- Reprocessed the exact loader script from the user's saved capture. The nonexistent `https://pagead2.googlesyndication.com/pubads_impl.js` was no longer inferred, and the original URL fragment remained unchanged. No downloaded website source was added to version control.
- Full browser regression with a script URL assembled from separate prefix, version, and filename strings completed 4 HTML pages and 1 download, archived 11 resources, and passed 24 visual comparisons and all 11 navigation checks. The original test server was then stopped; local replay executed the computed script successfully, with all observed HTTP requests confined to the local preview. No invented filename-only resource was requested, and stdout contained product progress without the upstream report.
- All 126 protected files (the existing manifest and raw/site files) retained their original hashes. The original preview selection was restored. The user's existing copied folder was retained without recapturing or overwriting it.
- Rebuilt and verified the Windows distribution with the fixes: 118 application and runtime files, 175,994,091 bytes. SHA256: `7fccb626cbfdfa1d3ee376632757ab989f16f2b08f463ac5de5c02498e4b56ff`.

## Waterfox filesystem compression

- Compared a verified runtime copy without compression, with XPRESS4K, and with LZX. Windows-reported file storage was 543,988,971, 265,146,174, and 175,766,591 bytes respectively. LZX saves 368,222,380 bytes (67.69%) with identical logical file contents.
- Three fresh browser sessions per mode had warm-cache median launches of 5.375 s, 5.324 s, and 5.333 s respectively. Exact viewports, response-body capture, downloads, computed asset execution, and desktop/mobile screenshot equality passed. These timing samples do not measure cold starts.
- The LZX runtime passed 24 existing visual comparisons, 11 navigation checks, and offline replay. All 66 runtime/notice hashes and 126 protected copied-site file hashes remained correct. Decompression of the test copy restored its original size and hashes.
- Applied LZX to the actual project runtime, then passed an additional browser smoke check, 53 Python + 2 Node + 33 upstream tests (88 total), and offline runtime verification. The extra test runtime was removed after validation.
- The existing 175,994,091-byte ZIP and its SHA256 remained unchanged. This is a disk-storage improvement on the tested NTFS machine; automatic setup/distribution behavior is unchanged. Details are in `COMPRESSION_REPORT.md`.

## Private runtime and automatic LZX setup

- Located the Windows Search app entry at the current user's `Waterfox Private Browsing.lnk`. Its target was this project's `.tools/waterfox/core/private_browsing.exe`. Removed that exact shortcut and retained a non-launchable backup record under ignored `.tools/`. No Waterfox installed-app entry, App Paths entry, StartMenuInternet registration, recent shortcut, or taskbar shortcut was found in the audited locations. Windows' Start app inventory contained no Waterfox entry after cleanup and fresh launches.
- Inspected `StartupOSIntegration.sys.mjs` inside the pinned browser archive: its startup task creates a Private Browsing shortcut even in ZIP builds, unless `browser.privateWindowSeparation.enabled` is false. Every DoppelGNG.me browser session now supplies that preference in its temporary profile, alongside the existing disabled default-browser prompt. Official runtime file contents remain unchanged. Manually opening the internal executable can still start Waterfox.
- Automatic setup applies LZX only to the explicit manifest-verified browser file list on Windows NTFS storage. All runtime hashes are checked before and after compression. A matching manifest and actual storage measurements permit reuse; corrupt receipts or changed storage trigger recompression. Unsupported filesystems retain the verified runtime. Offline checks remain read-only, and explicit external browser overrides are preserved.
- 61 Python tests, 2 Node HTTP tests, and 33 pinned upstream tests passed (96 total). Eight new compression regressions cover scope, integrity, storage changes, receipt recovery, unsupported filesystems, failed compression, altered contents, setup integration, and read-only offline checks. Localhost tests passed with the required local-network permissions.
- Source and packaged runtime checks completed four fresh headless browser sessions with eight pixel-identical desktop/mobile comparisons against the previous uncompressed baselines. Exact viewports, captured response bodies, computed script execution, and download byte equality passed. No session recreated the shortcut. All 66 runtime/notice hashes and 126 protected copied-site hashes passed.
- Rebuilt and read back the Windows ZIP: 120 application/runtime files, 175,997,888 bytes, SHA256 `33744f1b6b8601b1341085dde829ea8e452d4c692fc9a47d1d80d4ee08407424`. Fresh extraction had no compression receipt and used 543,988,971 bytes for the browser core. `npm install` and fresh setup succeeded, automatically reducing core storage to 175,766,591 bytes. Repeated setup reused LZX, and offline runtime verification passed. This package includes the tested source and excludes test artifacts and storage receipts.
- Retained measurement records, logs, and browser evidence under ignored `.tools/`; removed the temporary delivery project after validation. Also removed the older, hash-verified duplicate test browser core, which had occupied another 543,988,971 bytes. The main runtime, delivery ZIP, and existing copied websites were preserved.

## Domain-named output folders

- Default capture and export folders now use each target's actual domain, without the `+copied` suffix: `https://example.com/page` becomes `example.com`, while `https://www.another.org/catalogue` becomes `www.another.org`. Local development ports retain Windows-safe names such as `localhost_4319`. Custom output and destination options remain available.
- Windows device names are escaped, and dot-only hostnames cannot select the current or parent directory. A capture refuses an unrelated nonempty output folder before adding files or overwriting its project configuration. Default export still verifies every resource and refuses existing destinations.
- 63 Python and 2 Node HTTP tests passed (65 project tests), including actual-domain naming, CLI forwarding, default export byte integrity, existing-folder protection, and Windows path cases. Git exclusion checks covered domain folders, local hosts, partial exports, and older suffixed folders while keeping source and CI paths visible.
- All 126 protected existing copied-site files retained their hashes. Existing capture folders and the preview selection were preserved; older captures can be resumed by passing their existing folder with `--output`.
- Rebuilt and read back the delivery ZIP: 120 application/runtime files, 175,998,577 bytes, SHA256 `34d6982f51773111c5a5dfcbbe15451bfede9a2013d539df6759e723adc7d619`. Packaging tests exclude both domain-named and older suffixed website outputs.

## Cookie-form login

Verified on 17 October 2026 with generated credentials and owned loopback fixtures. No real account credentials or external login service were used.

- The project suite passed 131 Python tests and 3 Node tests. The pinned crawler passed 33 tests, for 167 total. The 22 login regressions cover hidden prompts, rejected password arguments, wrong credentials, form/redirect origin checks, cookie paths/expiry, evidence filtering, reflected values, pre-screenshot checks, and cleanup after errors.
- Real Waterfox capture and fresh-login validation both completed at the default 1440x900 and 390x844 viewports. The fixture supplied one protected HTML page and one download, with four resource records. All six capture screenshot comparisons had a changed-pixel ratio of 0.0; two navigation checks passed. Authenticated native HEAD probes also succeeded.
- Export completed. With the original servers stopped and a fresh browser without login state, every exported resource matched its recorded local hash over HTTP and the page replayed successfully.
- Response interception kept the browser cookie jar empty while retaining cookie rotation in the in-memory HTTP session. An owned origin on another port received zero cookie headers. Session expiry, a hidden signed-in marker, and browser POST were rejected. The hidden-marker attempt retained an incomplete manifest with no archived resources.
- The final run scanned 38 capture files, 37 export files, and 331 readable browser-profile files for its generated username, password, session cookie, CSRF value, and rotated cookie. No values matched. Four active `parent.lock` files could not be read. All temporary profiles were removed on normal shutdown.
- Public capture defaults and resume tests still pass. Authenticated capture requires a fresh output directory, and authenticated validation requires a new login. The manifest records the requirement without saving credentials, cookie state, or login settings.

Reproduce the browser workflow with `node scripts/python.mjs scripts/verify_login.py`. Numeric results and full logs remain in ignored `.tools/login-verification-*` directories. This evidence covers the owned HTML-form fixtures, not JavaScript login, SSO, MFA, arbitrary transformed credential reflections, or every website. The [authentication guide](docs/authentication.md) records those limits.

## Completion rules

No page is complete solely because HTML was downloaded or the server started. The pipeline distinguishes extracted, reconstructed, validated, complete, failed, and blocked states. Unsupported service operations, missing resources, untested controls, visual differences beyond the configured tolerance, and browser failures remain explicit failures. The tool does not claim support for every possible website or recover unavailable backend source.

At the earlier milestones recorded above, Git work remained local and no remote branches, pull requests, releases, or pushes had been created. Browser runtimes, website responses, downloaded assets, and generated npm projects remain excluded from commits. Documentation screenshots of the owned fixture are tracked separately.
