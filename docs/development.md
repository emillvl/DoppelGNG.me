# Development

## Prepare the checkout

```sh
npm ci
npm run setup
npm run runtime:check
npm test
```

Use Node.js 22+ and Python 3.10+. The recorded browser runs use Windows x64. The project has no configured lint, type-check, or remote CI workflow. Do not describe those checks as passed unless you add and execute them.

`requirements.txt` lists direct dependency ranges. `requirements.lock.txt` supplies the exact installation pins, including transitive packages. Setup hashes the requirements file and checks installed package versions before reusing the venv. `runtime-lock.json` separately pins the crawler files, browser archives, driver, license, and browser source revision.

## Test coverage

`npm test` runs unittest discovery under `tests/`, then `node --test tests/server.test.mjs`. Python must pass before the Node stage starts. These suites cover parser behavior, crawler integration, resource extraction, rewriting/SRI, runtime provisioning, compression, network destination policy, storage recovery and locks, validation, export, and packaging. Node tests exercise actual local HTTP behavior, ranges, queries, path containment, and document sandbox headers.

Some tests use controlled loopback services. Others replace browser/transport objects to isolate a contract. The suite does not replace a real browser workflow or establish arbitrary-site compatibility.

Run a focused Python module through the same launcher:

```sh
node scripts/python.mjs -m unittest discover -s tests -p test_resources.py -v
node --test tests/server.test.mjs
```

To run the pinned crawler's own suite in PowerShell:

```powershell
Push-Location .tools/webcrawler
try {
    ..\..\.venv\Scripts\python.exe -m unittest discover -s tests -v
} finally {
    Pop-Location
}
```

The upstream tests belong to that pinned source revision. Keep their count separate from the project suite.

## Owned browser fixture

Start the repository's test website in one terminal:

```sh
node scripts/python.mjs tests/fixture_site.py --port 4318
```

In another terminal, from the repository root:

```sh
npm run crawl -- --url http://127.0.0.1:4318 --authorized --output .tools/docs-fixture --port 4174 --scenarios tests/fixture-scenarios.json
npm run status -- --output .tools/docs-fixture
npm run validate -- --output .tools/docs-fixture --port 4174
npm run export -- --output .tools/docs-fixture --destination .tools/docs-fixture-export
```

Use a fresh output path for a fresh extraction and a fresh export destination. Stop the fixture with Ctrl+C when finished. Capture updates `.doppelgng/current.json`; explicitly select manifests afterward if another capture should remain your working target.

The fixture includes nested redirects, relative images, CSS imports/SRI, browser-generated and disclosure-only links, a computed script URL, JSON, an anchor, native details, a disclosure button, and a binary whose HEAD request returns 405. It supplies an owned example for extraction and replay. It is not evidence for unrelated websites.

For offline replay checks, stop the fixture and serve the copied project's manifest. Verify the archived resource hashes, page content, browser requests, navigation, and download behavior. Full `validate` revisits originals for interaction checks, so it should run while the fixture is available.

## Documentation screenshots

The documentation image generator uses this owned fixture and the project's headless browser. It records real capture/status output and screenshots of the local replay. Terminal panels are browser-rendered transcripts, with the workspace path replaced by `<workspace>`; they are not photographs of a desktop terminal.

```sh
node scripts/python.mjs scripts/docs_screenshots.py
```

The script creates a fresh ignored workspace under `.tools/`, restores the previous current-capture pointer, and writes reviewed assets and text transcripts under `docs/assets/`. It never captures an existing user website. Rendering requires the prepared browser and permission to use local sockets.

## Changing the implementation

Keep original responses separate from rewritten output. Preserve explicit failure states and resource provenance. A change to shared bytes or verification requirements must invalidate stale passes. Keep private-origin authorization scoped by scheme, hostname, and port. Maintain response sandboxing for external active documents.

When changing browser or replay behavior, run the affected unit tests and the owned browser workflow. Check actual screenshots and browser errors; matching HTTP status alone is insufficient. Packaging changes need a built archive whose files and notices match the tested source.

Use Git's whitespace check before committing:

```sh
git diff --check
```

Generated runtimes, captured websites, environments, profiles, logs, and ZIPs stay outside Git. `captures/` and `delivery/` are ignored working directories for the documented examples. If you choose another custom output name, add its path to your local exclusions before staging changes. Documentation screenshots from the owned fixture are intentional source assets.

## Reading historical evidence

[VALIDATION.md](../VALIDATION.md) records implementation milestones. The [audit](../AUDIT_REPORT.md), [follow-up verification](../POST_AUDIT_VERIFICATION.md), [real-site test](../REAL_WORLD_TEST_EMILVALIYEV.md), and [compression experiment](../COMPRESSION_REPORT.md) record specific runs, environments, defects, measurements, and limits.

Their test counts, local paths, source states, and build hashes describe those runs. They do not certify a later revision. Full local QA artifacts are intentionally omitted from the repository; the reports identify that evidence for the original workspace.
