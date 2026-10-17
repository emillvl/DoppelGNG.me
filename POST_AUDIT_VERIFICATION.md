# Independent post-audit verification: DoppelGNG.me

Historical run record from 17 October 2026. Source states, counts, and archive hashes below refer to that run. Absolute artifact links refer to the original local workspace and are not included in this repository.

17 October 2026, Asia/Baku. Verdict: READY WITH WARNINGS for the documented frontend reconstruction scope on the tested Windows environment.

The review retained the 17 original corrections and refined them as described below. This review found avoidable performance costs and unnecessarily broad restrictions in the first audit's implementation; these were corrected and tested. No unrelated refactoring, dependency addition, commit, push, pull request, publication or deployment was performed.

Two functional limitations remain material: some dynamically constructed external URLs still require their original service, and external documents that depend on origin-specific storage, modules or authenticated requests can require an integration. The first was reproduced and predates the audit. The second follows from keeping previously distinct documents isolated on a single replay origin. Arbitrary-site offline equivalence and proxy-only capture environments remain outside this result.

## Scope and evidence

The comparison baseline is the original pre-audit commit `12556a073831f8da4a24e9da01eb3b7dcd3432f4`. At verification time, HEAD was that commit on `codex/pre-push-audit-20261017`; all changes were uncommitted and the index was empty. The review compared the tracked diff and new network/test modules with the original commit as well as the audited working tree.

An untouched source snapshot of the original commit and a separate snapshot of the 99-test audited tree were retained for reproducible comparisons. The [complete source/test patch](C:/Users/user/Desktop/DoppelGNG.me/.tools/post-audit/original-to-final.diff), [changes after the first audit](C:/Users/user/Desktop/DoppelGNG.me/.tools/post-audit/post-audit-only.diff), and [machine-readable evidence and source hashes](C:/Users/user/Desktop/DoppelGNG.me/.tools/post-audit/verification-evidence.json) are local review artifacts. The source/test patch, excluding the two reports, has SHA256 `109fb81e9212f115ef78f07f0f0b33e1cb17157912b21559b987ab4ae2ecd97e`.

Executed environment: Windows x64, NTFS, Node 24.19.0, Python 3.12.14, pinned Waterfox 6.7.6 and geckodriver 0.37.1. Original, audited and refined comparisons used the same installed dependencies and browser. All security/network reproductions targeted owned local fixtures. Live certificate tests used a short-lived owned CA and real TLS handshakes, with the destination socket redirected by the test to its local server.

The [first audit](C:/Users/user/Desktop/DoppelGNG.me/AUDIT_REPORT.md) remains a historical record. Its immutable security report describes pre-correction source; it is not presented as a new security scan of this final tree.

## 1. Functionality before and after

| Capability | Original pre-audit behavior | Final behavior and compatibility assessment |
| --- | --- | --- |
| Capture and crawling | Existing crawler, original/rendered links, sitemap discovery, scrolling and scenarios | Retained, including robots choices, quiet/checkpoint controls, queries and same-origin page scope. Resource authorization does not expand page crawling. |
| Public and private dependencies | Native fallback could reach unrelated private services and rehost their responses | Public dependencies retain checked-IP transport and failover. The selected target may be private. Additional legitimate private resource origins now have an explicit, repeatable `--authorize-resource-origin URL` option, saved for resume. Other private redirect destinations remain blocked. |
| Origin and URL handling | Scheme confusion could misroute resources; equivalent default ports were treated inconsistently | Scheme/host/effective-port comparisons distinguish real origin changes while keeping `https://host` and `https://host:443` compatible. Ordinary external navigation remains external. |
| Redirects | Relative dependencies could use the requested rather than final base; replay could expose a different effective URL | Final response bases and same-origin document destinations are retained. A redirected document now works even when its canonical URL has no separate resource record; the previous audit could otherwise create a redirect loop. |
| Retrieval and downloads | GET-capable endpoints could fail at mandatory HEAD; an evicted-body branch bypassed the resource budget | HEAD 405/501 uses a streamed GET probe, closed promptly. Existing byte budgets apply consistently. Downloads, exact queries, HEAD and ranges remain available. |
| Resume and validation | Corrupt raw files could remain unrecoverable, shared changes could retain passes, and changed requirements could reuse stale evidence | Verified repair, dependency invalidation and explicit failure checkpoints work. Identical responses preserve transformed bytes. Stricter requirements are rechecked; looser visual tolerance retains evidence already passing the stricter threshold. |
| Subresource integrity | Rewritten bytes could fail original SRI | Supported integrity metadata tracks the final local bytes only after the strongest original check passes. Invalid original integrity remains invalid. Relative bases, multiple algorithms and chained HTML preloads are covered. |
| Embedded external documents | Replay collapsed their origins, enabling parent reads | Parent reads remain blocked for HTML/SVG through iframe/object/embed and external redirects. Clicked top-level navigation and popup behavior have been restored without allowing automatic top navigation or parent reads. Origin-dependent frame functionality remains limited. |
| Export and concurrency | Export could race a writer; stale PID locks could admit two owners | Capture/validation/CLI export use an OS workspace lock and consistent state reload. Conflicting operations in one workspace are excluded; different workspaces remain independent. Export still requires completion and integrity and produces the same standalone project structure. |
| Offline verification and configuration | Offline checks could repair metadata or create scratch files | Launcher verification remains read-only. Equivalent JSON receipt formatting is accepted without modification. Existing executable overrides, output folders and command defaults remain. Custom CA environment settings are preserved. |
| Replay network behavior | No server-side fallback; computed external expressions could still contact the original network | Server behavior is retained. The computed-external-URL limitation was reproduced rather than concealed by a successful visual comparison. |

Raw originals and reconstructed copies remain separate. The review retained the security fixes. No page-count, depth, resource-count, viewport or payload limit was newly imposed by this verification. The existing per-resource size budget and sitemap limits predate the audit; closing the evicted-body bypass enforces that existing budget consistently.

## 2. Assessment of all 17 corrections

| # | Correction | Independent assessment and regression evidence |
| --- | --- | --- |
| 1 | Private-network native fallback and redirects | Retained, refined. The destination checks apply to native redirects and browser body ingestion/refetch; public connections retain checked IPs, Host, SNI, hostname verification and address failover. Existing private/mixed/mapped/multicast and redirect-pivot negatives pass. The previous blanket loss of legitimate secondary private dependencies is addressed by explicit origin authorization. An owned two-origin browser capture, archival and export passed; unlisted third origins still receive zero native requests in the regression tests. Environment proxies/netrc remain excluded as discussed below. |
| 2 | External active-document isolation | Retained, made more precise. All seven real-browser HTML/SVG iframe/object/embed/redirect cases still reject parent DOM reads. Before/after browser checks demonstrated that the audited policy unnecessarily blocked clicked top navigation and imposed its sandbox on popups. Added flags restore those actions while parent reads and automatic top navigation still raise SecurityError. Storage/module limitations inside the isolated frame are disclosed, not misrepresented as full parity. |
| 3 | Workspace locking | Verified. Persistent OS locks remove the stale-PID unlink race and release after process termination. Competing owners, corrupt abandoned metadata, live legacy owners, crash release and busy CLI export are covered. Reloading the manifest inside validation/export's lock avoids operating on a pre-lock snapshot. The exclusive lock is justified for a consistent capture/export revision; it does not add a global lock across workspaces. |
| 4 | Repair of corrupt content-addressed originals | Verified and made memory-efficient. Existing persisted bytes are checked, not trusted because their hash-shaped filename exists. Refetching the correct response repairs corruption. Streamed hashing preserves full-byte checking without another file-sized allocation. |
| 5 | Shared-resource pass invalidation | Verified, ingestion gap corrected. Body/status/render-relevant metadata and rewritten-byte changes invalidate dependent validated/completed pages and integration evidence. The first audit's Store-level fix was bypassed when browser ingestion saw identical bytes with a changed content type or disposition. That shortcut now checks the relevant metadata too, with a new regression. Empty change sets return immediately. |
| 6 | Resume after validation-policy changes | Verified, unnecessary work removed. New viewports, stricter tolerance or changed scenarios invalidate affected page checks; unchanged requirements retain resume. The audited implementation also recaptured pages when tolerance became looser, despite stronger existing evidence. That unnecessary recapture is removed. Saved explicit resource authorizations survive an ordinary resume. |
| 7 | Identical recapture preserving rewritten copies | Verified. Intact transformed bytes and dependency metadata are preserved for identical source bytes. Corrupt local copies are still detected. The focused regression and real capture/resume workflows pass. Additional persisted-file verification has a measured cost, explicitly quantified below. |
| 8 | Scheme-aware origin classification | Verified, normalized precisely. HTTP/HTTPS on the same host remain distinct. Host case and equivalent default ports remain compatible across resource aliases, link rewriting and crawl scope; different ports are still distinct. This avoids making the security fix a new default-port exclusion. |
| 9 | Final response base and replay redirects | Verified, canonical lookup completed. Relative-image and navigation checks use the recorded final URL. Replay now also serves the final document from an alias record when discovery did not create a second canonical record. The added Node regression verifies the final URL, body and query distinction and prevents the audited redirect-loop case. Replay uses a temporary GET redirect; historical intermediate redirect status codes are not separately reconstructed. |
| 10 | SRI after reconstruction | Verified, performance and ordering corrected. The first audit parsed every HTML document twice and repeatedly hashed shared dependencies. Integrity updates now use the existing document parse, cache only per-call digests, and write non-HTML dependencies first. Valid integrity-protected HTML preloads receive a targeted dependency-order finalization, including a three-document chain. An additional test caught an ordering gap in my initial optimization; it failed before correction and passes now. Invalid original strongest hashes are preserved. No full resource graph is buffered in memory. |
| 11 | HEAD 405/501 fallback | Verified. The fix changes the preliminary probe, preserves guarded redirects and closes both HEAD and streamed GET responses. The download regression and the owned browser fixture's real HEAD-405 endpoint pass. A successful GET is no longer excluded merely because HEAD is unsupported. |
| 12 | Query/origin navigation checks | Verified. Matching includes the query and local origin after clicks and refreshes, with recorded destinations allowed. Correct query variants pass; wrong variants and escapes to the original site fail. Sorting preserves duplicate-value order rather than collapsing distinct repeated parameters. |
| 13 | Evicted-body size enforcement | Verified. The refetched body is checked before storage, including its final destination. The existing oversized-body regression passes. This closes an inconsistent bypass rather than adding a new capture limit. |
| 14 | Interrupted/startup failure checkpoints | Verified. Preview startup and validation disconnect regressions record incomplete status and failed active pages, save the error and re-raise. The broad BaseException handler is limited to checkpointing/cleanup and does not turn failures into success. Sessions close on exit. If storage itself fails, a checkpoint cannot be promised. |
| 15 | Recovery of repaired downloads | Verified. Standalone validation restores an intact repaired download to download_validated before integration; corrupt bytes still fail. This restores recoverability without relaxing export integrity. |
| 16 | Read-only offline verification | Verified, formatting restriction removed. Missing or altered provenance is reported without repair. JSON is compared structurally so whitespace/key order does not reject equivalent valid metadata. No scratch creation is added by the offline launcher path. Packaged offline runtime verification passed again. |
| 17 | Concurrent atomic JSON writers | Verified, serialization cost corrected. Exclusive unique temporary names, atomic replacement, cleanup and bounded retries for specific transient Windows errors remain. The previous audit's many small serialization writes caused avoidable overhead; a single serialized write restores baseline speed/memory behavior. Concurrent writers pass. Injected full-disk and denied-replacement errors preserve the old checkpoint, remove the owned temporary file and propagate the failure. |

The Requests minimum increase to 2.32.2 is justified by the adapter extension API; the pinned installed 2.34.2 remains unchanged. No new runtime dependency or service was added. Existing tests were retained; 13 further project tests were added beyond the 99-test audited tree.

## 3. Restrictions retained and why

Unrelated private resource origins require explicit operator authorization. A reference in an untrusted page is not itself authorization to read an intranet service. The new opt-in is scoped to scheme, hostname and effective port; it supports owned secondary services without opening all private networks or expanding the crawler's page scope.

Native capture uses direct transport and does not inherit environment proxies or automatic netrc credentials. A proxy can perform a separate destination resolution that bypasses the checked-IP connection, and ambient credentials must not silently accompany unrelated fallback retrieval. Configured custom CAs are still honored and live-tested. Proxy-only networking and automatic netrc authentication are genuine compatibility restrictions; safe proxy/authenticated-service integration was not added speculatively.

External active documents retain an opaque origin. Adding allow-same-origin would recreate the demonstrated parent-origin exposure. The narrower navigation/popup permissions restore ordinary interactions without removing the origin boundary. The distinct meanings of these permissions and the remaining origin/storage restriction follow the [HTML sandboxing standard](https://html.spec.whatwg.org/multipage/browsers.html#sandboxing), and the selected behavior was tested in the actual pinned browser. A separate origin-preserving replay architecture would be needed for broader frame compatibility; it was not introduced as an unrelated redesign.

Changed resources and stricter validation invalidate stale passes, and a workspace writer excludes concurrent CLI export of that same workspace. These are correctness boundaries. Original integrity failures and incompatible cyclic HTML integrity dependencies are not silently converted into successful rewritten resources.

## 4. Performance and resources

The deterministic Python benchmarks use one warmup followed by five wall/CPU samples; the table gives median wall milliseconds. Allocation peaks are measured in a separate tracemalloc run and exclude pre-existing input/setup allocations. OS caches were warm. All source snapshots use the same interpreter, dependencies and disk. These are controlled workloads, not claims about arbitrary websites.

| Workload | Original | First audited tree | Final tree |
| --- | ---: | ---: | ---: |
| Atomic JSON, 2,000 resource records | 13.16 ms | 23.89 ms | 13.69 ms |
| Reconstruct 80 HTML documents with 1,000 other records | 286.22 ms | 470.37 ms | 271.70 ms |
| Reconstruct 40 SRI documents sharing rewritten CSS | 119.87 ms | 267.17 ms | 106.87 ms |
| Recapture identical 16 MiB response | 13.54 ms | 33.05 ms | 27.02 ms |
| Verify raw and local 16 MiB copies | 25.86 ms | 26.28 ms | 18.94 ms |

Median CPU for the 80-document workload was 281.25 / 421.88 / 265.63 ms respectively; for the SRI workload, 109.38 / 218.75 / 109.38 ms. Atomic-write CPU returned from 31.25 to 15.63 ms, matching the original. Short CPU samples have the Windows process-clock granularity of approximately 15.6 ms.

Identical recapture still costs about 13.5 ms more per 16 MiB than the original in this workload, with CPU approximately 31.25 versus 15.63 ms. The original skipped verification of an existing raw file and overwrote the local copy; the corrected operation checks both persisted copies while preserving a valid transformed local file. Those checks support corruption repair and reuse of intact transformed files. Streamed hashes reduced the audited 16 MiB incremental allocation to about 1.01 MiB. A chunk-comparison alternative was measured, was slower, and was discarded. The extra verification accounts for the remaining processing cost.

Raw/local integrity verification also fell from approximately 16.01 MiB incremental allocation to 1.01 MiB. The binary test retained the same 33,554,705 bytes on disk. Resource bodies are still processed individually. SRI caches contain digests, not copies of all resource bodies; HTML-preload ordering operates on dependency edges without a recursion-depth limit. Empty invalidation sets avoid rescanning all pages.

The atomic writer again materializes a JSON string, matching the original's approximately 3.90 MiB allocation peak for this manifest. The first audit's streaming serializer used about 0.05 MiB but cost 82% more wall time in this case. The final implementation combines original serialization behavior with the new atomic replacement and concurrency protection. Very large manifests still require workload-specific profiling.

Replay throughput used a 2,000-record manifest, checked every response body, and took five 400-request samples after warmup:

| Requests per second | Original | First audited tree | Final server |
| --- | ---: | ---: | ---: |
| Sequential client | 74.17 | 76.00 | 73.58 |
| 16 concurrent requests | 271.15 | 272.31 | 277.00 |

This shows no material replay throughput regression in the tested workload. Initial combined client/server RSS readings varied with garbage collection, so memory was investigated in a separate server process. After 2,600 requests and explicit GC, retained heap was 8.019 / 8.015 / 8.020 MiB and RSS was 122.03 / 122.91 / 123.04 MiB. Server CPU totals were 7.624 / 7.342 / 7.562 seconds. No added retained-memory growth was observed over that run. This is not a long-duration leak proof.

The three-source end-to-end comparison used one owned page, three resources, an 800×600 viewport and unchanged default tolerance:

| Measure | Original | First audited tree | Refined capture |
| --- | ---: | ---: | ---: |
| Fresh capture | 35.948 s | 36.046 s | 35.708 s |
| Identical resume | 9.461 s | 9.428 s | 9.451 s |
| Sampled capture CPU, process tree | 7.781 s | 7.500 s | 7.875 s |
| Peak summed process RSS | 1,354.64 MiB | 1,354.79 MiB | 1,349.30 MiB |

All three completed with identical raw response hashes. CPU was sampled every 100 ms; summed RSS counts shared mappings and is not unique physical memory. These are single end-to-end samples, not statistically conclusive speedups. This timing comparison preceded the final narrow HTML-preload ordering correction; final microbenchmarks, regression tests and desktop/mobile capture smoke were rerun after that correction. The timed page did not contain HTML-preload chains.

Reproduce locally using the retained [Python benchmark](C:/Users/user/Desktop/DoppelGNG.me/.tools/post-audit/benchmark.py), [replay throughput benchmark](C:/Users/user/Desktop/DoppelGNG.me/.tools/post-audit/replay-benchmark.mjs), [isolated replay memory check](C:/Users/user/Desktop/DoppelGNG.me/.tools/post-audit/replay-memory.mjs), and [capture comparison](C:/Users/user/Desktop/DoppelGNG.me/.tools/post-audit/capture-benchmark.py). Their exact inputs, samples and commands remain under .tools/post-audit. No sustained large-site capture, public-CDN latency benchmark or exhaustive scalability claim is made. Manifest parsing/resource lookup in replay remains linear, as before the audit; the review did not add an index or cache.

## 5. Follow-up on the first audit warnings

| Warning | Precise cause, investigation and final classification | Blocking status |
| --- | --- | --- |
| Other platforms, minimum versions and overrides | Only Windows x64/NTFS with the versions above was executed. All 33 Python source/test files also parse with Python 3.10 grammar, but that is not runtime verification. POSIX locks, Node 22, Python 3.10, alternate browsers and other actual filesystems remain unexecuted compatibility checks. | Non-blocking for the tested Windows use; blocks broader compatibility claims. |
| Fresh installation | Downloaded and installed all 25 exact Python pins into a clean, separate environment and ran its Python suite. The final ZIP's new extraction then completed actual npm setup, dependency installation, runtime verification and all 112 tests. First-time browser/crawler Internet download and installer unpack were not replayed; the package already contains verified runtime files. | Python/recipient setup gap resolved. Cold runtime provisioning remains a non-blocking unexecuted path. |
| Public HTTPS/CDN/proxy behavior | Real owned TLS proved custom CA success, correct SNI/Host, checked socket destination, and rejection of untrusted or wrong-host certificates. Public-address failover and redirect negatives also pass. No real public CDN or proxy deployment was exercised. Native proxy inheritance is intentionally unsupported, not a sandbox failure. | Non-blocking for direct capture; proxy-only environments require integration. |
| Third-party vulnerability coverage | Pinned file inventories and package consistency establish the chosen bytes/versions. No fresh CVE database assessment or exhaustive browser/upstream source audit was performed. | Remaining assurance gap; no vulnerability-free dependency claim. |
| Scale, storage, permissions and encodings | Controlled multi-resource graphs, concurrent replay, binary storage and real browser workflows were benchmarked. ENOSPC and denied replacement were injected and correctly preserved the old JSON checkpoint with explicit failure. Actual disk exhaustion, all permission models, very large captures, long soaks and legacy/nondeterministic sites remain unproven. | Non-blocking for demonstrated workloads; synthetic fault tests are not physical-disk compatibility proof. |
| Backends, authentication, streaming and hidden states | These remain outside the documented frontend reconstruction proof. No backend behavior or unexercised state was removed by a fix. Scenario authors must still know the effects of their handlers. | Product scope, not a newly introduced defect. |
| Browser network independence | Confirmed an owned computed external script was archived, yet replay issued a request to its original server. The source site could be stopped, but stopping that separate script server broke the runtime operation. This is a pre-existing computed-URL rewriting limit, now explicit in README. A generic runtime interception layer would be a substantial new design with security/compatibility consequences and was not added to this correction review. | Blocks universal fully-offline/completeness claims. Non-blocking for publishing the scoped tool with this limitation disclosed. |
| Secondary private origins / external widgets | Explicit resource-origin authorization resolves the blanket rejection of legitimate owned private dependencies; an end-to-end two-origin capture/export passed. Sandbox navigation/popup overreach is fixed. Opaque frames still cannot recover every origin-dependent storage/module/authentication workflow. | Private-resource gap resolved. Frame-origin integration remains a conditional compatibility limitation. |
| No lint/type-check/CI setup | None is configured in the project. Local syntax, tests and whitespace checks were executed; no remote CI or unconfigured tool is called passed. | Non-blocking for this local readiness assessment. |
| Credentials/history/raw export | Added a heuristic scan of all 136 blobs reachable from 13 local commits, totaling 844,042 bytes; no selected credential-prefix/private-key-header patterns matched. Current authored files and diff were also reviewed. This is not proof of credential absence. Existing user captures were not scanned or altered; raw/artifact export is deliberately not sanitized publication. | No detected publication blocker in current source/history; captures remain separate private artifacts. |
| Daybreak/plugin advisory | The prior plugin reported access not granted. This is historical tooling/account state, not a demonstrated product failure. This review used local evidence and did not claim new protected-plugin results or reseal the original scan. | Non-blocking for local verification. |

Testing-environment failures were separated from software failures. A direct Python test invocation initially encountered the sandbox's temporary-directory permissions; the normal launcher uses the project scratch directory. One preliminary original-code benchmark at experimental zero tolerance differed by five pixels; the comparison was rerun at the unchanged project default, and the larger owned fixture later produced zero changed pixels. An automatic approval-review quota interruption prevented one command from executing; after continuation, approval succeeded and all remaining required checks completed. The final counts include only completed passing checks.

## 6. Additional corrections and final checks

The changes made during this verification are limited to: explicit secondary resource authorization; canonical origin comparisons; effective-URL replay lookup; response-metadata invalidation; reuse of stricter validation evidence when tolerance loosens; semantic receipt comparison; precise sandbox navigation/popup permissions; and measured serialization, hashing and SRI processing improvements. Chained HTML-preload integrity ordering and storage-failure tests were added to prevent the optimizations sacrificing correctness. Documentation now states the actual offline and frame-origin limits.

| Final check | Result |
| --- | --- |
| Project suite on final source | 112 passed: 109 Python + 3 Node, no skips/failures |
| Pinned crawler suite | 33 passed |
| Independent fresh Python download/install | 25 exact pins installed; Python tests and dependency consistency passed |
| Larger owned browser fixture | 6 routes, 13 resources; capture, resume, standalone validation and export passed |
| Visual/navigation evidence | 30 desktop/mobile comparisons, maximum changed-pixel ratio 0.0, 13 navigation checks |
| Final frozen-source browser check | 2 routes, 7 resources; default desktop/mobile viewports, SRI, computed same-origin asset, HEAD-405 download, capture/resume/validate/export passed |
| Export with original fixture stopped | All 13 local resource bodies matched hashes over HTTP; HEAD, ranges, method rejection and uncaptured query behavior passed |
| Origin isolation / compatibility | 7 isolation cases passed; clicked navigation/popup restoration and blocked parent/automatic navigation passed |
| Live pinned TLS | Trusted custom CA success; hostname mismatch and untrusted certificates rejected |
| Fresh extracted distribution | 124 file hashes match extraction and current source/runtime; npm ci, actual setup, offline runtime check and all 112 tests passed |
| Syntax / Git | 33 Python files parsed, including 3.10 grammar; four Node files passed syntax; Git whitespace check passed; index empty |

Detailed logs: [final project tests](C:/Users/user/Desktop/DoppelGNG.me/.tools/post-audit/project-tests-final.log), [crawler tests](C:/Users/user/Desktop/DoppelGNG.me/.tools/post-audit/crawler-tests.log), [final browser workflow](C:/Users/user/Desktop/DoppelGNG.me/.tools/post-audit/final-smoke.log), [package verification](C:/Users/user/Desktop/DoppelGNG.me/.tools/post-audit/package-verification.log), [TLS](C:/Users/user/Desktop/DoppelGNG.me/.tools/post-audit/tls-result.json), [sandbox compatibility](C:/Users/user/Desktop/DoppelGNG.me/.tools/post-audit/isolation-compat.json), and [confirmed computed-URL limitation](C:/Users/user/Desktop/DoppelGNG.me/.tools/post-audit/computed-replay.json).

Final local archive: [doppelgng.me-post-audit-20261017.zip](C:/Users/user/Desktop/DoppelGNG.me/dist/doppelgng.me-post-audit-20261017.zip), 176,016,733 bytes, 124 application/runtime files plus bundle manifest. SHA256:

```text
f6eb9179307474bd6c85ed1beff2ea497e631378fb3f1f0d4c8dd671b26e097d
```

The archive above contains the source verified in this review; the earlier ZIP records an earlier build. Generated captures, benchmark snapshots, fresh environments and ZIPs remain ignored local QA artifacts. No existing user capture was modified.

## 7. Verification result

READY WITH WARNINGS. The tested local source and recipient package have no known blocking regression in the documented, exercised workflows. All 17 corrections address demonstrated problems; the additional refinements remove demonstrated unnecessary restrictions and avoidable processing costs while retaining their security/correctness boundaries.

Remaining limits are: computed external requests can still require the original network; some origin-dependent external widgets and proxy-only capture environments need integrations; untested platforms, cold runtime provisioning, very large workloads and third-party vulnerability coverage remain unproven. These results do not support a claim of arbitrary fully offline website equivalence.

At verification completion, Git was on `codex/pre-push-audit-20261017` at the original pre-audit commit. Changes were local, unstaged, and uncommitted. Nothing had been pushed, published, or deployed.
