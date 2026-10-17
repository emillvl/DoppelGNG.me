# Capture, replay, and evidence

## Workspace layout

```text
example.com/
  manifest.json
  capture.lock
  package.json
  server.mjs
  DOPPELGNG_LICENSE.txt
  raw/
    <SHA256 of original response bytes>
  site/
    files/<SHA256 of URL>.<extension>
  artifacts/
    <first 16 characters of URL SHA256>/
      baseline.json
      rendered.html
      network-original.json
      original-1440x900-top.png
      local-1440x900-top.png
      diff-1440x900-top.png
      validation.json
      interactions.json
    geckodriver.log
    server.log
  crawler/
    <upstream checkpoint files>
```

Screenshot filenames repeat for each viewport and top/middle/bottom position. Interaction screenshots use `interaction-N-original.png`, `interaction-N-local.png`, and `interaction-N-diff.png`. The manifest also stores interaction and integration results. `validation.json` records the page snapshot checks; inspect the manifest for the combined page outcome.

Raw files use the hash of their contents, so identical response bodies can share one stored original. Local files use the URL hash and keep their own content hash after rewriting. Rendered DOM is evidence of browser state; it does not replace the original HTTP response.

Capture, validation, and CLI export hold the workspace's operating-system lock. The persistent lock file records PID and creation time. It is not deleted to recover an abandoned operation. JSON writes use a unique temporary file and atomic replacement, with bounded retries for transient Windows replacement errors.

## Manifest reference

The manifest is JSON with `schema: 1`. Fields can be absent until their corresponding step runs. It is an internal capture format, not a separately versioned public API.

| Field | Contents |
| --- | --- |
| `target` | Normalized original target URL |
| `created_at`, `updated_at` | UTC timestamps |
| `status`, `error` | Capture state and an operation error when recorded |
| `crawler` | Loaded crawler directory and SHA256 hashes of its two source modules |
| `browser` | Executable path, browser capabilities, and response-body collector setup error if present |
| `policy` | Robots/checkpoint/quiet choices, page host, viewports, tolerance, volatile query keys, extra resource-origin authorizations |
| `scenarios` | Saved mapping of original paths to interaction scenarios |
| `discovery` | Sitemap observations and discovered sitemap pages |
| `pages` | Original URL to page/download record |
| `resources` | Original URL to archived resource record |
| `integration` | Cross-page link results, time, and overall pass state |
| `discrepancies` | Reserved discrepancy list; detailed failures also appear in page/error records |

Page records include `url`, `state`, `resources`, `links`, and `validation`. Extracted HTML pages also have `kind: "page"`, `title`, and a recorded `final_url`. Downloads use `kind: "download"` and checks applicable to their bytes. Failure and robots records can contain `error` or `reason`.

Resource records contain:

| Field | Meaning |
| --- | --- |
| `url`, `key` | Original URL and its SHA256 key |
| `raw`, `local` | Paths relative to the capture workspace |
| `sha256`, `local_sha256` | Original and reconstructed content hashes |
| `bytes` | Original response-body length |
| `status`, `content_type`, `method` | Captured response and request classification |
| `kind` | Page, download, or other resource |
| `source` | How the response body was obtained |
| `headers` | Retained content type/disposition, cache-control, and vary headers when present |
| `request_headers` | Selected representation headers from observed requests |
| `dependencies` | Parsed dependency URLs |
| `captured_at` | UTC capture time |
| `final_url` | Effective URL when supplied by that retrieval path |
| `head_observed`, `empty_verified` | Additional retrieval evidence when applicable |

Resources are keyed by URL. The archive does not model every possible cookie-, header-, or method-dependent representation of the same URL. Selected request headers help refetch observed variants but do not turn the store into a general HTTP session recorder.

## Completion states

An HTML page normally advances through:

```text
discovered -> extracting -> extracted -> reconstructed -> validated -> complete
```

A download passes byte checks, reaches `download_validated`, and becomes `complete` after integration. `failed` records an extraction or validation failure. `blocked` records a robots denial. An operation error sets overall status to `incomplete`; it also marks currently extracting/validating pages as failed.

`validated` means the individual page checks passed. `complete` also requires integration to pass and every discovered entry to be complete. The upstream crawler's visited set, checkpoint, or completion summary cannot establish this state.

Reusing a workspace checks its target and crawler identity. Resume verifies saved resources and requeues incomplete or corrupt work. Source changes to a shared body, status, content type, or content disposition invalidate dependent pass states. Changed rewritten bytes also invalidate them. Identical source responses retain intact transformed local files.

A changed viewport list, tighter page screenshot tolerance, or changed scenarios requires fresh page checks. A looser tolerance can reuse stricter evidence. See [resume](getting-started.md#resume-and-validate) for settings retained or reset on each command.

## What validation checks

Original baselines are recorded at each configured content viewport after navigation and scrolling. The default list is 1440x900 and 390x844. At top, middle, and bottom, the browser captures a screenshot and a snapshot of the document.

For each corresponding local state, validation compares:

- Screenshot dimensions and changed-pixel ratio.
- Page title and whitespace-normalized visible body text.
- H1/H2/H3 text, computed font family, and font size.
- Scroll width, absence of horizontal overflow, and document height within two pixels.
- Broken images, link URL/text/target inventory, and control inventory.
- Browser fetch failures, HTTP responses of 400 or higher, console errors, and recorder disconnects.

The default visual rule counts a pixel as changed if any RGB channel differs by more than 25. The allowed ratio is `0.01`, or 1%. The saved difference image contains RGB differences; JSON records the measured ratio and mean channel difference. A dimension mismatch fails without producing a matching-size diff. A tolerance of zero still uses the channel threshold of 25.

Interaction checks compare original and local control state and screenshots. Unknown controls prevent a passing claim. See [scenario semantics](cli.md#interaction-scenarios), including their fixed screenshot tolerance and active viewport.

Integration runs at 1440x900. It checks internal link HTTP loading and exercises HTML page edges through clicks and refreshes. It checks recorded destination routes, queries, titles, visible content, heading fonts, images, anchors, and browser errors. This desktop navigation pass is separate from the configured page screenshot viewports.

Standalone validation uses saved originals rather than creating new screenshot baselines. It still visits original pages for interaction discovery/comparison. To demonstrate offline behavior for a particular target, test replay with its original services unavailable and record that separate result.

## Replay behavior

The Node server reads the manifest for each request. Same-origin URLs retain their paths and queries; external resources use `/__doppelgng__/asset/KEY`. It supports GET, HEAD, single byte ranges, saved content disposition, same-origin document redirects, and trailing-slash alternatives.

Exact sorted query matching takes precedence. The configured volatile key `_rsc` can be ignored for non-page, non-JSON static variants. This handles captured framework flight files; it does not make all query variants interchangeable.

Missing resources return 404 and non-GET/HEAD operations return 501. Missing manifests return 503 for normal content requests. The server checks that resource paths and resolved files stay inside `site/`. It sends `Cache-Control: no-store` and `X-Content-Type-Options: nosniff` with archived responses.

An archive can contain partial data while the manifest is incomplete. Serving it does not change completion status. The report endpoint exposes the manifest, so it includes original URLs, local paths, and capture metadata.

## Network boundaries and limitations

Native HTTP requests use a shared destination policy for resources, robots, and sitemap retrieval. The target origin is explicitly authorized, including when it is local. Additional resource origins require `--authorize-resource-origin`. Other destinations must resolve entirely to public, non-multicast addresses. Mixed public/private answers, loopback, link-local, private addresses, and private redirect pivots are rejected.

For public destinations, the transport connects to checked addresses while retaining the original Host header, TLS server name, and certificate verification. It can fail over among checked addresses. Native capture sessions use direct connections, ignore environment proxies and netrc credentials, and accept the documented CA bundle variables.

This native transport policy is not a firewall for the browser. Waterfox executes the original site's JavaScript. Replay scripts may also construct external URLs that were not rewritten. The replay server has no network fallback, but that alone does not establish browser network isolation.

During replay, external HTML, XHTML, SVG, and XML documents receive a response sandbox. It blocks parent-document reads and automatic top-level navigation while allowing clicked navigation, popups, scripts, forms, and downloads under the configured sandbox permissions. External scripts and stylesheets loaded as resources are not sandboxed as documents. Widgets relying on original-origin storage, authentication, modules, or requests may need an integration.

The tool does not recover backend source or prove logins, payments, mutations, WebSockets, streaming, DRM, hidden routes, or unexercised states. DOM screenshots cannot establish those behaviors. Large graphs, all encodings, minimum runtime versions, alternative platforms, and every dependency version are not covered by the recorded Windows evidence.

## Captured data and sharing

Diagnostic network logs remove cookies and authorization headers, including proxy authorization. Resource records retain only selected headers. URLs, query values, response bodies, rendered DOM, screenshots, console/error content, and browser capabilities can still contain sensitive data.

Export copies raw responses and artifacts along with the replay project. It is a faithful workspace copy, not a publication sanitizer. Review the output separately before sharing it. Capturing a website does not change ownership or grant reproduction rights.
