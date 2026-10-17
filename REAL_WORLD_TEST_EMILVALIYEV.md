# Real-world verification: emilvaliyev.com

Historical run record from 17 October 2026. Source states, counts, and archive hashes below refer to that run. Absolute artifact links refer to the original local workspace and are not included in this repository.

Verdict: PASS for the tested portfolio capture, resume, export and local replay workflows.

The owner's authorized public portfolio was copied using the actual DoppelGNG.me CLI and its pinned crawler/browser runtime. All 19 discovered routes and 110 resource records were captured. The original capture, a resumed run and the independently validated export all reached `complete`. A fresh browser then browsed the exported site successfully with external HTTP(S) unavailable.

## Delivered copy

- [Completed capture](C:/Users/user/Desktop/DoppelGNG.me/emilvaliyev.com/manifest.json)
- [Portable export](C:/Users/user/Desktop/DoppelGNG.me/emilvaliyev.com-export/package.json); folder: `C:\Users\user\Desktop\DoppelGNG.me\emilvaliyev.com-export`
- [Desktop replay screenshot](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/emilvaliyev-20261017/portfolio-local-desktop.png)
- [Mobile replay screenshot](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/emilvaliyev-20261017/portfolio-local-mobile.png)
- [Preview recorded during the run](http://127.0.0.1:4339/); the exported folder's own server, bound to loopback only; background PID `4424`.

The export contains its own `server.mjs`, `package.json`, raw files, reconstructed files and verification artifacts. Run `npm run dev` from the exported folder to view it locally; no dependency installation is required. The deliverable stayed local; it was not published or deployed.

## Executed checks

| Check | Actual result |
| --- | --- |
| Initial authorized capture | CLI exit 0; all 19 routes complete; all 110 recorded resource responses HTTP 200 |
| Individual page checks | 12 HTML pages × 2 viewports × 3 scroll positions = 72 passing observations |
| Page behavior and rendering | Titles, text, headings/fonts, dimensions, images, links and control inventory passed all 72 observations |
| Initial internal navigation | 80 passing link checks at 1440×900, including fragments, route clicks and refreshes where applicable |
| Resume | Real capture command rerun against the completed workspace; resource URLs and raw/local hashes unchanged; final status complete |
| Independent validation | Real `validate` command against the separate exported folder; all routes complete |
| Export integrity | Every raw and reconstructed file verified; exported resource hashes match the initial capture |
| Standalone exported runtime | Exported `server.mjs` started from its own directory; health and homepage HTTP 200; all 110 resource body hashes passed; no recorded server failures at the check |
| All-resource replay | GET body hashes, HEAD behavior and first-byte range responses passed for all 110 records |
| Published download checksums | All 3 software archives match their captured public `.sha256` sidecars |
| Browser isolation control | Direct navigation to the original HTTPS site failed through the deliberately closed browser proxy, with a matching browser network failure recorded |
| Isolated exported replay | 24 passing direct-route/refresh cases: all 12 HTML pages at 1440×900 and 390×844; top/middle/bottom inspected in each case |
| Final isolated browser cases | Zero recorded browser errors, failed resource responses, broken images or external HTTP(S) requests in the 24 completed cases |
| Isolated internal navigation | 80 passing link checks at 1440×900 with zero external HTTP(S) requests |
| Uncaptured requests | Intentional test GET returned 404; intentional test POST returned 501, with explicit failure for the uncaptured operation |
| Final state | Both manifests complete; no implementation correction or weakened capture settings needed |

The isolation test used a fresh browser profile with a closed HTTP/HTTPS proxy and an explicit loopback exception. It blocked browser access to the original site while allowing the local copy. This was browser-level network isolation, not an operating-system air gap. Downloaded applications were preserved and checked as files; they were not installed or executed.

## Routes exercised

| Route | Type | Result |
| --- | --- | --- |
| `/` | HTML page | Passed |
| `/writing/` | HTML page | Passed |
| `/projects/ghostnector/` | HTML page | Passed |
| `/projects/adlibere/` | HTML page | Passed |
| `/projects/f4fchecker/` | HTML page | Passed |
| `/writing/das-ist-blitzkrieg/` | HTML page | Passed |
| `/writing/remember-the-rhetorical-question/` | HTML page | Passed |
| `/writing/ghostnector/` | HTML page | Passed |
| `/writing/gaussian-prep-framework/` | HTML page | Passed |
| `/writing/coded-an-adblocker-out-of-nowhere/` | HTML page | Passed |
| `/writing/cicero-is-finished/` | HTML page | Passed |
| `/writing/windows-never-forgets-is-out/` | HTML page | Passed |
| `/downloads/ghostnector_0.1.0+site20261010_amd64.deb` | Download | Passed |
| `/downloads/ghostnector_0.1.0+site20261010_amd64.deb.sha256` | Download | Passed |
| `/downloads/adLibere-v2.0.0.zip` | Download | Passed |
| `/downloads/adLibere-v2.0.0.zip.sha256` | Download | Passed |
| `/downloads/F4FChecker-v1.0.7.zip` | Download | Passed |
| `/downloads/F4FChecker-v1.0.7.zip.sha256` | Download | Passed |
| `/papers/gambling-digital-evolution-report.pdf` | Download | Passed |

The 110 records include the pages and downloads listed above, plus CSS, JavaScript, images, fonts and framework route data. MIME distribution: 12 text/html, 1 text/css, 9 application/x-javascript, 4 font/woff2, 1 image/webp, 75 text/plain, 1 image/svg+xml, 4 application/font-woff, 2 application/zip, 1 application/pdf. Unique raw-file contents total 5,971,072 bytes; replay-file contents total 6,305,736 bytes. Artifact screenshots and crawler checkpoints use additional disk space; filesystem allocation overhead is not included.

Published archive checksum results:

- `ghostnector_0.1.0+site20261010_amd64.deb`: `ed679a0f4f188d0a923f0392ab9c6639a0b1181c18dffacf3ecba3040e602bc0`
- `adLibere-v2.0.0.zip`: `adf3bf7394b9ebc0cfd8fda870baaa3851baf8ef681934282d9c0fb362e16d17`
- `F4FChecker-v1.0.7.zip`: `18eb8cc94a7eea90a71407809a8dbc5d20dad964e56648aa8ac9ca4d0f2dba30`

## Timing and environment

- Initial capture started: 2026-10-17 21:47:01 UTC+04:00.
- Initial capture completed: 2026-10-17 22:01:25 UTC+04:00; 864 seconds including discovery, capture, page validation and all navigation checks.
- Independent verification completed: 2026-10-17 22:28:33 UTC+04:00.
- Host: Windows; Node.js replay server; pinned Waterfox 153.5.0 and geckodriver 0.37.1.
- Standard settings retained: robots respected, checkpoint every page, desktop/mobile viewports, visual tolerance 0.01, no added resource-origin authorization or target-specific workaround.

| Additional CLI workflow | Exit | Observed elapsed | Evidence |
| --- | --- | --- | --- |
| export | 0 | 6.637 s | [export.log](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/emilvaliyev-20261017/export.log) |
| resume | 0 | 217.004 s | [resume.log](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/emilvaliyev-20261017/resume.log) |
| validate | 0 | 518.023 s | [validate.log](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/emilvaliyev-20261017/validate.log) |

Resume and exported validation ran concurrently in separate directories, browser profiles and local ports. Their elapsed times include contention on this machine. These are observations from this end-to-end run, not a controlled throughput or CPU/memory benchmark.

## Scope and remaining limitations

Two auxiliary isolation attempts stopped on `NS_BINDING_ABORTED` for the same Next.js background prefetch during the mobile-writing-page case. The recorded trace pinpointed the sequence: viewport resize started the old document's prefetch at event 0; the harness forced navigation at event 1; cancellation arrived at event 2. The same URL completed HTTP 200 in the new document at events 52 and 125, and passed body-hash checks. Waiting only around refresh did not address this earlier transition. The harness was corrected to wait after resizing before navigation, as well as before and after refresh. The complete isolated run then passed with every error still treated as a failure. No application code, security setting or error filter was changed. Both interrupted attempts are preserved in [first-attempt proof](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/emilvaliyev-20261017/proof-first-isolated-attempt.json), [second-attempt proof](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/emilvaliyev-20261017/proof-second-isolated-attempt.json), their matching logs, and [the cancellation diagnosis and full-trace reference](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/emilvaliyev-20261017/prefetch-cancellation-diagnosis.json).

The run found no blocking product defect. The source returned 404 for optional `robots.txt` and `sitemap.xml`; linked-page discovery still completed successfully. Coverage is the 19 discovered routes and their recorded resources, not a claim about unlinked or undiscoverable URLs.

External social/GitHub links and email actions remain external destinations. No email, external form submission, application installation or remote account operation was performed. This portfolio supplied no backend transaction that would demonstrate reconstruction of a remote service. Other websites, browser engines, operating systems and physical mobile devices were not certified by this run.

## Git and evidence

Work stayed on `codex/pre-push-audit-20261017` at commit `12556a073831f8da4a24e9da01eb3b7dcd3432f4`. All 49 files fingerprinted after the preceding audit were unchanged at the end of this run. Existing audit changes were retained. The only new reviewable root artifact from this test is this report; generated copies and QA evidence are ignored by Git. Nothing was staged, committed, pushed, published or deployed. `git diff --check` passed.

- [Machine-readable operational proof](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/emilvaliyev-20261017/proof.json)
- [Original completed manifest snapshot](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/emilvaliyev-20261017/initial-manifest.json)
- [Initial capture log](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/emilvaliyev-20261017/capture.log)
- [Independent verification log](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/emilvaliyev-20261017/verification.log)
- [Git/source verification](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/emilvaliyev-20261017/git-verification.json)
- [Standalone exported-server startup evidence](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/emilvaliyev-20261017/standalone-preview.json)
- [Initial CLI and verification harness](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/verify-emilvaliyev.py)
- [Final isolated-replay harness with request-settling checks](C:/Users/user/Desktop/DoppelGNG.me/.tools/real-world/verify-emilvaliyev-replay.py)

The run verified capture, resume, export, and replay of this portfolio's recorded pages, assets, downloads, and internal navigation with browser access to the original site blocked.
