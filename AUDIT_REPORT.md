# Pre-push audit: DoppelGNG.me

Historical run record from 17 October 2026. Source states, counts, and archive hashes below refer to that run. Absolute artifact links refer to the original local workspace and are not included in this repository.

The first audit's findings are recorded here. The follow-up review, additional corrections, updated test counts, performance measurements, and later verdict are recorded in [POST_AUDIT_VERIFICATION.md](C:/Users/user/Desktop/DoppelGNG.me/POST_AUDIT_VERIFICATION.md).

Date: 17 October 2026, Asia/Baku. Starting revision: `12556a073831f8da4a24e9da01eb3b7dcd3432f4` on `master`. Work branch: `codex/pre-push-audit-20261017`.

At the end of this audit, the corrections were local and uncommitted. No push, remote branch, pull request, publication, deployment, or release was performed.

## 1. Project overview

DoppelGNG.me reconstructs authorized websites into resumable local archives and standalone Node projects. The Python CLI combines a pinned upstream crawler, headless Waterfox, browser network observations, dependency discovery, raw-response storage, rewriting, screenshot/content checks, interactions, and navigation validation. The Node server serves archived resources without a server-side network fallback. Export requires completion and resource integrity. Distribution packaging includes the verified crawler and private browser.

Reviewed workflows were setup and cache reuse; authorization and origin scope; discovery and robots choices; extraction and dependency closure; capture checkpoints and resume; shared-resource invalidation; validation requirements for completion; downloads, queries and redirects; standalone replay; export; and distribution integrity.

Preserved behavior includes separate raw originals and rewritten files, observed URL discovery, existing CLI commands and defaults, robots override/checkpoint/quiet controls, explicit local executable overrides, domain-based output folders, export requiring verified resource hashes, and explicit failure for uncaptured backend operations.

The security review independently inspected all 45 initially tracked authored files. Managed upstream tests were also read and executed. Browser binaries and the complete upstream dependency implementation were not subjected to an exhaustive vulnerability audit.

## 2. Testing performed

Test environment: Windows x64 on NTFS; Node.js 24.19.0; npm 11.17.0; Python 3.12.14; Waterfox 6.7.6 with recorded engine 153.5.0; geckodriver 0.37.1. All 25 installed Python package pins matched `requirements.lock.txt`.

| Check | Final result |
| --- | --- |
| Project suite | 99 passed: 96 Python tests and 3 Node tests |
| Pinned upstream crawler suite | 33 passed |
| Existing project baseline | 63 Python + 2 Node tests passed after loopback access was enabled |
| Expanded owned browser fixture | Complete: 6 routes, including a redirect alias; 13 resources; capture, resume, validate, and export passed |
| Visual and navigation evidence | 30 desktop/mobile screenshot comparisons; maximum changed-pixel ratio 0.0; 13 navigation checks passed |
| Final snapshot smoke | Complete on the final source: 2 routes, 7 resources; capture, resume, validate, and export hashes passed |
| Export after original fixture shutdown | All 13 resource bodies matched their local hashes over HTTP; HEAD, ranges, uncaptured-query 404 and unsupported-method 501 passed |
| External document isolation | All 7 real-browser cases passed: HTML/SVG through iframe, object and embed, plus an externally redirected document |
| Python dependency consistency | Base-interpreter pip checked the project venv: no broken requirements |
| Syntax and whitespace | 33 Python files parsed; all four Node entry/test files passed syntax checks; Git whitespace check passed |
| Distribution | 124 files matched the extraction and current source/runtime; packaged install entry, offline runtime check, and all 99 packaged-copy tests passed |

Main commands executed from the repository:

```powershell
npm ci --ignore-scripts --no-audit --no-fund --cache .tools/npm-cache
npm run setup
npm run runtime:check
npm test
node scripts/python.mjs -m unittest discover -s .tools/webcrawler/tests -v
node scripts/python.mjs -m unittest discover -s tests -p test_recovery.py -v
node scripts/python.mjs -m unittest discover -s tests -p test_pipeline.py -v
node scripts/python.mjs -m unittest discover -s tests -p test_storage_lock.py -q
node scripts/python.mjs -m unittest discover -s tests -p test_network.py -v
node scripts/python.mjs -m unittest discover -s tests -p test_dependencies.py -q
node scripts/python.mjs -m unittest discover -s tests -p test_resources.py -q
node --check server.mjs
node --check scripts/setup.mjs
node --check scripts/python.mjs
node --check tests/server.test.mjs
.\.venv\Scripts\python.exe -c 'import ast;from pathlib import Path;files=list(Path("doppelgng").glob("*.py"))+list(Path("tests").glob("*.py"));[ast.parse(p.read_text(encoding="utf-8-sig"),filename=str(p)) for p in files];print(f"Syntax: {len(files)} Python files")'
& 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pip --python .venv/Scripts/python.exe check
.\.venv\Scripts\python.exe .tools/audit/run_fixture.py
.\.venv\Scripts\python.exe .tools/audit/run_fixture.py --smoke
.\.venv\Scripts\python.exe .tools/audit/verify_export.py
.\.venv\Scripts\python.exe .tools/audit/atomic_pointer_repro.py
npm run status -- --output .tools/audit/fixture-capture-verified
npm run export -- --output .tools/audit/fixture-capture-verified --destination .tools/audit/cli-export-verified
npm run crawl -- --help
npm run package -- --output dist/doppelgng.me-audit-20261017.zip
.\.venv\Scripts\python.exe .tools/audit/verify_package.py
git diff --check
git diff --cached --stat
```

The browser harness launches only the repository's owned HTTP fixture, prints the exact capture/validation commands and ephemeral target URL, uses disposable output folders, and restores the previous capture selection. The packaged-copy helper extracts the ZIP into a fresh directory, compares every packaged file against both the extraction and current source/runtime, then runs `npm ci`, `npm run runtime:check`, and `npm test` there. It reuses the existing pinned Python dependencies; it does not claim a fresh network dependency installation.

The isolated read-only check ran the Python launcher from an empty temporary working directory with the project interpreter and source path configured. Offline runtime verification succeeded and created zero files or directories.

The [security report](C:/Users/user/.codex/state/plugins/codex-security/scans/DoppelGNG.me/12556a073831f8da4a24e9da01eb3b7dcd3432f4_20261017T125419Z_34ht91qw/report.md) records the immutable pre-correction findings. Controlled [before](C:/Users/user/.codex/state/plugins/codex-security/scans/DoppelGNG.me/12556a073831f8da4a24e9da01eb3b7dcd3432f4_20261017T125419Z_34ht91qw/artifacts/security-before.json) and [after](C:/Users/user/.codex/state/plugins/codex-security/scans/DoppelGNG.me/artifacts-b258355eb7d8f7077d409abc2c4921a168c1963d6be4f05b23e924736ae2e0ab/artifacts/security-after.json) evidence and the [seven-case isolation result](C:/Users/user/.codex/state/plugins/codex-security/scans/DoppelGNG.me/artifacts-b258355eb7d8f7077d409abc2c4921a168c1963d6be4f05b23e924736ae2e0ab/artifacts/isolation-matrix.json) support the local corrections. No real private service, credential, or third-party website was targeted.

## 3. Defects discovered and corrected

All entries below were resolved in the audited working tree. Severity describes the demonstrated security or reliability impact; only findings 1 and 2 are security findings in the plugin report.

| # / severity | Location and reproduction | Root cause and impact | Correction and evidence |
| --- | --- | --- | --- |
| 1 / High | [doppelgng/archive.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/archive.py:114), [doppelgng/network.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/network.py:26). A remote resource reference points at an unrelated loopback service and browser retrieval is denied. | Native fallback accepted the destination and redirects. Private response data became readable on the replay origin. | One shared destination policy protects native requests, redirects, and newly observed/refetched bodies. The authorized origin remains usable; unrelated destinations require public addresses. Public connections pin checked addresses, preserve Host/TLS identity, and fail over safely. Reproduction changed from 1 private request/body archived to 0 requests/no body archived. |
| 2 / Medium | [server.mjs](C:/Users/user/Desktop/DoppelGNG.me/server.mjs:80), [doppelgng/resources.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/resources.py). Replay an external active document embedded by an otherwise authorized parent. | Distinct document origins became one local origin, allowing parent DOM and report reads. | Response-level sandboxing isolates external HTML/XML/SVG documents, including redirected responses. Ordinary script/stylesheet authority is preserved. All 7 real-browser embedding cases now raise SecurityError for parent reads. |
| 3 / High | [doppelgng/storage.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/storage.py:65). Two operations inspect one stale PID lock before either replaces it. | Both could enter the same workspace and overwrite state. Corrupt abandoned lock JSON also prevented recovery. | Atomic OS locks replace stale-file deletion, release on process exit, and retain metadata. Active legacy PID owners remain respected. Competing-owner, crash-release, corrupt-lock, legacy-lock, and busy-export regressions pass. CLI validation/export reload state under the lock. |
| 4 / Medium | [doppelgng/storage.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/storage.py:141). Corrupt a raw hash-named file, then retrieve the same original bytes again. | Existing raw files were trusted solely because the filename existed, so retries could never repair corruption. | Recheck existing raw bytes and restore a corrupt raw file from the verified response. The regression failed before correction and passes now. |
| 5 / Medium | [doppelgng/storage.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/storage.py:166), [doppelgng/reconstruct.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/reconstruct.py:20). Change a resource shared by validated or completed pages. | Existing pass states survived response changes, or invalidation covered only completed pages. | Changes to body/status/render-relevant metadata and rewritten bytes invalidate affected pass states and integration evidence. Validated and completed cases are covered. |
| 6 / Medium | [doppelgng/pipeline.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/pipeline.py:376). Resume with another viewport list, tolerance, or scenario set. | Old passes were reused while the manifest advertised new verification requirements. | Changed verification requirements invalidate page checks; unchanged requirements preserve resume. An explicit empty scenario mapping can clear previous scenarios. |
| 7 / Medium | [doppelgng/storage.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/storage.py:141). Recapture an unchanged response already represented by rewritten local bytes. | Replacing the local copy with raw bytes reset its hash and falsely invalidated previous pages. This stopped the expanded redirect fixture as incomplete. | Preserve intact rewritten bytes and dependency metadata when the source is unchanged. The focused regression and expanded capture/resume both pass. |
| 8 / Medium | [doppelgng/reconstruct.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/reconstruct.py:12), [doppelgng/resources.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/resources.py). Use HTTP and HTTPS resources on the same host. | Scheme was omitted from origin comparisons, producing wrong local routes or rewriting external navigation into missing resources. | Scheme participates in origin classification. External assets receive aliases and external navigation stays external. Regression coverage passes. |
| 9 / Medium | [doppelgng/reconstruct.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/reconstruct.py:20), [server.mjs](C:/Users/user/Desktop/DoppelGNG.me/server.mjs:68). A document redirects before resolving relative assets or navigation. | Rewriting used the requested URL and replay could expose the document at a different effective URL from the original. | Preserve final response URLs, rewrite against that base, replay same-origin document redirects, and validate the recorded destination. Relative-image and redirected-navigation tests pass. |
| 10 / Medium | [doppelgng/reconstruct.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/reconstruct.py:20). Rewrite CSS/JS referenced with subresource integrity metadata. | Original SRI hashes no longer matched the rewritten resource, so browsers rejected valid local resources. | Recompute supported algorithms over local bytes only after the original strongest integrity check passes. Original integrity failures stay failures. Dependencies are written before document metadata is updated, without buffering the whole resource graph. Unit and real-browser SRI checks pass. |
| 11 / Medium | [doppelgng/pipeline.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/pipeline.py:57). A valid GET endpoint returns 405 or 501 to HEAD. | Mandatory HEAD success prevented otherwise valid captures and downloads. | Probe with GET when HEAD is explicitly unsupported, close probe responses, and retain the guarded transport. Both regression and owned fixture pass. |
| 12 / Medium | [doppelgng/pipeline.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/pipeline.py:241). Navigate among query variants, drop a query, or escape to the original site while retaining matching content/title. | Target lookup and arrival checks used only the path, causing false failures and false completion evidence. | Match query variants and verify local origin plus expected path/query after clicks and refresh, allowing recorded redirects. All positive and negative regressions pass. |
| 13 / Medium | [doppelgng/archive.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/archive.py:49). Evicted browser data triggers a browser refetch larger than the configured resource limit. | That branch bypassed the size check applied to normal bodies. | Apply destination and byte-limit checks before storing refetched data. The oversized-body regression passes. |
| 14 / Medium | [doppelgng/storage.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/storage.py:51), [doppelgng/__main__.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/__main__.py). Preview startup fails or a browser disconnects during validation. | Stored status remained running/validating, and the current page could retain an old completion state. | Record an explicit incomplete capture and failed active page, save the error, and re-raise it. Startup and interrupted-validation regressions pass; native sessions close on exit. |
| 15 / Low | [doppelgng/__main__.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/__main__.py). Repair a failed download and rerun validation. | Intact downloads kept the failed state. | Revalidate original/local hashes and restore download_validated before integration. The recovery regression passes. |
| 16 / Low | [doppelgng/dependencies.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/dependencies.py:45), [scripts/python.mjs](C:/Users/user/Desktop/DoppelGNG.me/scripts/python.mjs). Run offline verification with missing/altered provenance or from an empty working directory. | The supposedly read-only check could repair metadata and create scratch directories. | Offline checks report provenance problems without modifying them; the launcher skips scratch creation. Corrupt/missing receipt tests and the zero-file isolated check pass. |
| 17 / Medium | [doppelgng/storage.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/storage.py:25). Independent captures update the shared current pointer after both have written its fixed .tmp name. | A forced original-protocol interleaving reproduced FileNotFoundError. Windows replacement contention was also observed during verification. | Use exclusive per-write temporary files, clean them up, and retry only bounded transient Windows replacement failures. Corrected concurrent-writer tests pass, with valid final JSON and no temporary files remaining. |

Original source and reconstructed copies remain distinct. The corrections retained features, exception reporting, legitimate tests, and documented completion thresholds.

## 4. Edge-case findings

Executed cases include corrupt/missing cached files; same-size tampering; unrelated output/destination folders; repeated capture and export; target/crawler mismatch; busy and abandoned workspaces; two simultaneous owners; process termination; legacy locks; concurrent JSON writers; changed validation policy; shared response changes and identical recapture; same-host/different-scheme URLs; redirects and query variants; external active documents; private/mixed/mapped IPv6/multicast destination answers; redirect pivots; public-address failover; evicted oversized browser data; unsupported HEAD; invalid and valid SRI; missing resources; robots choices; checkpoint boundaries; quiet/error behavior; server methods, ranges, exact queries, and containment.

The final expanded fixture measured 30 screenshot comparisons across five HTML routes at 1440×900 and 390×844, at top/middle/bottom positions, plus a download route. All compared pixels matched. Integration checked 13 links. This is evidence for the owned fixture, not for any unrelated website.

Failed checks during discovery were retained as evidence and corrected. Initial sandboxed Node socket tests failed with EACCES; the unchanged baseline passed with loopback permission. Direct venv pip commands could not run because that interpreter has no pip module; base pip successfully checked the venv. An intermediate ZIP failed comparison against a later source edit and was replaced by the final verified build. All final required checks passed.

## 5. Modifications made

Production changes are limited to [doppelgng/network.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/network.py), [doppelgng/storage.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/storage.py), [doppelgng/archive.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/archive.py), [doppelgng/dependencies.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/dependencies.py), [doppelgng/discovery.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/discovery.py), [doppelgng/reconstruct.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/reconstruct.py), [doppelgng/resources.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/resources.py), [doppelgng/pipeline.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/pipeline.py), [doppelgng/__main__.py](C:/Users/user/Desktop/DoppelGNG.me/doppelgng/__main__.py), [server.mjs](C:/Users/user/Desktop/DoppelGNG.me/server.mjs), [scripts/python.mjs](C:/Users/user/Desktop/DoppelGNG.me/scripts/python.mjs), and [requirements.txt](C:/Users/user/Desktop/DoppelGNG.me/requirements.txt).

No dependency was added. Requests' minimum declared version became 2.32.2 to match the adapter extension API; the pinned installed version remains 2.34.2. Direct native transport intentionally avoids environment proxies and automatic netrc credentials, while preserving configured REQUESTS_CA_BUNDLE/CURL_CA_BUNDLE certificate authorities and certificate verification.

Three test modules were added: [tests/test_network.py](C:/Users/user/Desktop/DoppelGNG.me/tests/test_network.py), [tests/test_recovery.py](C:/Users/user/Desktop/DoppelGNG.me/tests/test_recovery.py), and [tests/test_storage_lock.py](C:/Users/user/Desktop/DoppelGNG.me/tests/test_storage_lock.py). Existing archive, discovery, dependency, distribution, pipeline, resource and server tests were extended or adjusted for the guarded transport. The owned fixture gained SRI, a redirected relative-image route, and a HEAD-rejecting download. 34 project tests were added; all existing tests remain.

[README.md](C:/Users/user/Desktop/DoppelGNG.me/README.md) documents the corrected resume behavior, persistent locks, network boundary, external-document isolation, integrity handling and failure checkpoints. This report is the additional audit artifact. Small disposable harnesses and generated captures/ZIPs stay under ignored .tools/ and dist/ paths. Existing user capture folders were not modified.

Compatibility evidence covers the existing default behavior and the exercised CLI interfaces. The two security boundaries can reject unrelated private dependencies or limit external widgets relying on their original origin. Those limitations are explicit; they do not silently produce a successful capture.

## 6. Remaining risks and verification limits

- Only the stated Windows/Node/Python/browser environment was executed. Linux/macOS, the POSIX lock branch, minimum Node 22/Python 3.10, other filesystems, and alternate browser overrides were not established by these runs.
- Cached setup and an extracted distribution were tested. A fresh Internet download/install of all Python packages and a first-time runtime download/unpack were not executed. Managed hashes/inventories and package integrity passed.
- Actual public HTTPS/CDN/proxy deployments were not contacted. HTTP address pinning/failover was exercised with owned sockets; TLS identity and custom CA selection were checked through adapter regressions, not a live external TLS handshake.
- Third-party dependency vulnerability databases and the complete browser/upstream implementation were not exhaustively audited. Integrity checks establish the selected pinned bytes, not the absence of dependency vulnerabilities.
- Large binary packaging was tested; very large site graphs, sustained high-load capture, exhausted storage, denied filesystem permissions, and nondeterministic/legacy-encoding sites were not fully exercised.
- Authenticated services, backend mutations, payments, WebSockets, streaming, hidden states, and all header/cookie-dependent representations remain outside the proof supplied by these frontend fixtures. Scenario authors must know whether their handlers are read-only.
- The Node server's no-network-fallback behavior does not establish browser network isolation. Unrewritten dynamically constructed external URLs may still depend on the original network; arbitrary-site browser behavior with that network unavailable was not proven. URL fragments were deliberately left intact in the established discovery design, so this remains a reported compatibility limit rather than an unrequested rewriting change.
- Cross-origin private dependencies require separate authorization/design support; no implicit allowlist was added. Sandboxed external widgets may need separate integrations. Errors must remain explicit and incomplete.
- No project lint/type-check configuration or CI workflow exists in the inspected tree. Syntax and Git checks passed; no unconfigured lint/type tool or remote CI run is described as passed.
- Credential review covered current authored files and the final diff, not Git history or existing user captures. No embedded credentials/private keys or staged sensitive files were found. Export deliberately contains raw responses and artifacts and is not a sanitized publication.
- The security plugin reported Daybreak access not granted. Its protected UI results may not be displayable, but this advisory did not prevent local verification. The generated security report describes the initial source; post-fix evidence and this audit describe the local corrections.

Security plugin usage recorded at scan completion, including conversation context: 7,483,801 total tokens, 7,426,470 input, 7,044,096 cached input, and 57,331 output. The tool labeled measurement coverage complete; this is not a measurement of all subsequent QA work.

## 7. Audit result

READY WITH WARNINGS

No known blocking defect or failed configured check remains in the tested environment. The 17 documented defects are corrected locally; 99 project tests and 33 upstream tests pass, owned browser workflows and security reproductions pass, and the final distribution matches the tested source. The compatibility, fresh-install, external-service and dependency-audit gaps above prevent a broader release assurance.

Final local archive: [dist/doppelgng.me-audit-20261017.zip](C:/Users/user/Desktop/DoppelGNG.me/dist/doppelgng.me-audit-20261017.zip); 176,013,215 bytes; 124 application/runtime files plus the bundle manifest. SHA256:

```text
0e8df1c74279cbfcfe4cdc38aa5931f6b43fb475970a62bb3c46a1637583c00f
```

At audit completion, Git was on `codex/pre-push-audit-20261017` at the original commit. Changes were uncommitted, the index was empty, and nothing had been pushed.
