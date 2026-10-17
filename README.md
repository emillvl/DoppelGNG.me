# DoppelGNG.me

DoppelGNG.me captures a website's frontend and checks whether its local copy renders and behaves like the original. It uses [WebCrawler](https://github.com/emillvl/webcrawler) for discovery and headless Waterfox for response bodies, rendered pages, and browser checks.

Use it for websites you own or have permission to reproduce. A capture preserves original responses, rewrites resources for local replay, and records screenshots, hashes, and validation results. Each completed capture is a standalone npm project.

The tool captures browser-visible files and exercised states. It cannot recover backend source, recreate an unavailable service, or guarantee that every computed external request will work offline.

## Start a capture

Source setup requires Node.js 22+, Python 3.10+, Git, and, on Windows x64, 7-Zip. Automatic browser provisioning supports Windows x64. Other platforms need explicit browser and driver paths and have not been validated. See [installation](docs/getting-started.md) for prerequisites and overrides.

```sh
git clone https://github.com/emillvl/DoppelGNG.me.git
cd DoppelGNG.me
npm install
npm run setup
npm run crawl -- --url https://your-authorized-site.example --authorized
npm run dev
```

Open the local address printed by the last command, normally `http://127.0.0.1:4173`. The example hostname is a placeholder. Replace it with your authorized target.

Setup downloads pinned crawler and browser files into `.tools/` and installs Python packages in `.venv/`. Subsequent setup verifies and reuses them. You do not need a separate Waterfox installation. On Windows NTFS, setup compresses the private browser with LZX; the measured runtime occupied about 176 MB on disk with 544 MB of logical contents.

The default output folder is the target's domain, such as `example.com/`. Choose `--output captures/example` to use another directory. Repeat the same capture command to resume that workspace. Existing unrelated folders are refused.

## What a completed capture contains

- Original response bytes in `raw/`, separate from rewritten files in `site/`.
- A manifest with resources, page states, source hashes, discovery policy, and validation results.
- Original rendered DOM, network evidence, desktop/mobile screenshots, and difference images in `artifacts/`.
- A Node replay server and `package.json`. The replay server serves archived files without fetching missing resources from the network.

By default, the browser checks 1440x900 and 390x844 content viewports at the top, middle, and bottom of each HTML page. It also compares text, headings and fonts, layout, links, controls, image loading, and browser errors. Internal navigation must pass before the capture becomes `complete`.

Disclosures such as native `details` and buttons with `aria-expanded`/`aria-controls` are discovered automatically. Other controls need [interaction scenarios](docs/cli.md#interaction-scenarios). Forms and backend operations need separate service work.

## Commands

| Task | Command |
| --- | --- |
| Prepare dependencies | `npm run setup` |
| Check cached runtime without downloads | `npm run runtime:check` |
| Capture or resume | `npm run crawl -- --url URL --authorized` |
| Show capture state | `npm run status -- --output example.com` |
| Run validation again | `npm run validate -- --output example.com` |
| Serve a capture | `npm run dev -- --manifest example.com/manifest.json` |
| Export to another directory | `npm run export -- --output example.com --destination delivery/example.com` |
| Build the Windows ZIP with browser included | `npm run package` |
| Run project tests | `npm test` |

Capture, status, validation, and export print JSON. Capture and validation exit unsuccessfully when the result is incomplete. Validation can revisit the original site for interaction checks; it is not an offline-only command.

To run a copied project, open its directory, run `npm install`, then `npm run dev`. Replay needs Node.js; it does not need Python, the crawler, or Waterfox. Export includes raw responses and browser artifacts, so review that material before sharing it.

![Completed capture status from the owned regression fixture](docs/assets/terminal-status.png)

Actual status output from the owned fixture, rendered as a terminal transcript. See [screenshots and run evidence](docs/screenshots.md) for capture output and the local replay.

## Documentation

| Guide | Contents |
| --- | --- |
| [Installation and first capture](docs/getting-started.md) | Requirements, setup, preview, resume, and export |
| [Command reference](docs/cli.md) | Every CLI option, environment variables, scenarios, and exit behavior |
| [Capture, replay, and evidence](docs/capture-and-replay.md) | Files, manifest fields, states, validation, privacy, and network boundaries |
| [Architecture](docs/architecture.md) | Modules, crawler adapter, dependency discovery, rewriting, and integrity |
| [Distribution and licensing](docs/distribution.md) | Bundled Windows ZIP, checksums, recipient setup, and dependency notices |
| [Troubleshooting](docs/troubleshooting.md) | Setup failures, incomplete captures, missing resources, and validation differences |
| [Development](docs/development.md) | Project layout, tests, owned browser fixture, and documentation screenshots |
| [Screenshots](docs/screenshots.md) | Recorded terminal output, replay image, and fixture evidence |
| [Contributing](CONTRIBUTING.md) | Scope, changes, tests, and writing conventions |

Historical measurements and test records are in [VALIDATION.md](VALIDATION.md), [COMPRESSION_REPORT.md](COMPRESSION_REPORT.md), [AUDIT_REPORT.md](AUDIT_REPORT.md), [POST_AUDIT_VERIFICATION.md](POST_AUDIT_VERIFICATION.md), and [REAL_WORLD_TEST_EMILVALIYEV.md](REAL_WORLD_TEST_EMILVALIYEV.md). Their counts and archive checksums describe the recorded milestones. Referenced local QA artifacts are not shipped in Git.

## Limits

Computed external URLs, unexercised states, origin-dependent widgets, logins, payments, mutations, WebSockets, live streaming, and DRM are outside the supplied frontend equivalence checks. A successful capture proves the recorded checks for the discovered routes. It does not establish universal offline behavior or coverage of hidden routes.

Native capture requests allow the authorized target, explicitly authorized resource origins, and public dependencies. The original browser still executes website code and can make its own requests. External active documents are sandboxed during replay; widgets that depend on their original origin may need an integration. See [network boundaries and limitations](docs/capture-and-replay.md#network-boundaries-and-limitations).

## License

DoppelGNG.me source and documentation are available under the [MIT License](LICENSE). Bundled dependencies retain their own licenses and notices; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Captured websites retain their existing rights and permissions.
