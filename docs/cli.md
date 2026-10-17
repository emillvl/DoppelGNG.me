# Command reference

Run npm commands from the repository root. Arguments after npm's `--` go to the underlying command. Python commands use the project interpreter through `scripts/python.mjs`.

## Capture

```sh
npm run crawl -- --url URL --authorized [options]
npm run crawl -- --help
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--url URL` | Required | HTTP or HTTPS target without embedded credentials. The crawler normalizes the URL. |
| `--authorized` | Required | Confirm permission to reproduce the target. |
| `--output PATH` | Target authority converted to a folder name | Create or resume this capture workspace. |
| `--crawler PATH` | `DOPPELGNG_CRAWLER`, otherwise `.tools/webcrawler` | Load a compatible crawler directory containing `webcrawler.py` and `signatures.py`. |
| `--port N` | `4173` | Port for the temporary local replay server used during capture. |
| `--viewport WIDTHxHEIGHT` | `1440x900` and `390x844` | Repeat to replace the default viewport list. Each dimension must be 240 through 7680. |
| `--visual-tolerance RATIO` | `0.01` | Maximum changed-pixel ratio for page screenshots, between 0 and 1. |
| `--scenarios FILE` | Saved mapping on resume, otherwise none | JSON mapping original page paths to interaction arrays. |
| `--authorize-resource-origin URL` | Saved list on resume, otherwise none | Repeat to allow additional resource origins, including private addresses. Does not add page scope. |
| `--respect-robots` | Enabled | Load and apply robots.txt rules. |
| `--ignore-robots` | Disabled | Skip robots.txt. Cannot be combined with `--respect-robots`. |
| `--checkpoint-every N` | `1` | Save upstream crawler state every N processed pages. `0` disables periodic saves. Negative values are rejected. |
| `-q`, `--quiet` | Disabled | Suppress capture/navigation progress. Keep final JSON and errors. |
| `--login` | Disabled | Prompt for hidden username/password fields and use an in-memory HTML-form cookie session. Takes no value. |
| `--login-check SELECTOR` | Required with `--login` | Visible signed-in marker required on every original HTML page. |
| `--login-url URL` | Target URL | Follow this same-origin URL to the login form. |
| `--login-form SELECTOR` | Unique password form | Select a form when automatic selection is ambiguous. |
| `--login-user-field NAME` | Detected username field | HTML username input name. |
| `--login-password-field NAME` | Detected password field | HTML password input name. |
| `-h`, `--help` | | Print usage and exit. |

`--checkpoint-every 0` retains final saves, RAM-triggered crawler offloading, and reconstruction recovery records. It does not disable the manifest.

Robots rules apply by default. If robots.txt is unavailable, the adapter keeps the upstream policy of proceeding without loaded rules. A discovered URL blocked by loaded rules stops the capture with an incomplete result.

Examples:

```sh
npm run crawl -- --url https://your-authorized-site.example --authorized --output captures/example --viewport 1280x800 --viewport 390x844
npm run crawl -- --url https://your-authorized-site.example --authorized --ignore-robots --checkpoint-every 25 -q
npm --silent run crawl -- --url https://your-authorized-site.example --authorized -q
```

The last form also suppresses npm's banner. The upstream crawler's banners, state-save messages, findings, and summary are suppressed in every capture mode. DoppelGNG.me emits completion only after reconstruction and validation finish.

For an owned private asset server:

```sh
npm run crawl -- --url http://localhost:4318 --authorized --authorize-resource-origin http://localhost:4319
```

An authorization covers that exact scheme, hostname, and effective port. Paths do not narrow it. A redirect to a different private origin still needs its own authorization. The setting does not expand link crawling beyond the target origin.

## Status

```sh
npm run status -- [--output PATH]
```

Prints capture status, every page state, resource count, and manifest path as JSON. Without `--output`, reads `.doppelgng/current.json` relative to the current directory. A successfully read status exits 0 even when the capture is incomplete. Use the JSON `status` field to decide whether work is complete.

## Validate

```sh
npm run validate -- [--output PATH] [--port N] [--login --login-check SELECTOR]
```

Uses saved original baselines, stored page screenshot tolerance, stored scenarios, and the current local resources. `--port` defaults to `4173`. It checks downloads for raw/local hash integrity and runs page and navigation checks again. Original-site interaction checks require network access to the original site.

This command has no `--viewport`, `--visual-tolerance`, or `--scenarios` options. Change those through capture. It returns 0 only if the resulting capture is complete.

All six login options from capture also apply to validate. An authenticated capture requires a fresh login and explicit signed-in selector for validation. See [authenticated capture](authentication.md). Login settings and credentials are not saved. Authenticated capture requires a fresh output directory; public resume is unchanged.

## Export

```sh
npm run export -- [--output PATH] [--destination PATH]
```

`--output` selects the source capture; omitting it uses the saved current pointer. `--destination` selects the delivery directory; omitting it uses the target's domain-based name in the current directory. Success prints the project path, start command, and status as JSON.

Export refuses incomplete captures, broken resource hashes, an existing destination, or an existing `.partial` sibling. The [installation guide](getting-started.md#export) describes the same-workspace case.

## Preview server

```sh
npm run dev -- [--manifest PATH] [--port N]
node server.mjs --manifest captures/example/manifest.json --port 4173
```

Manifest selection, in order: `--manifest`, `DOPPELGNG_MANIFEST`, `.doppelgng/current.json`, then `.doppelgng/manifest.json`. Port selection: `--port`, `PORT`, then `4173`. The server binds to `127.0.0.1`.

The generated copied project already passes its own `manifest.json` in its `dev` script. Stop the server with Ctrl+C.

| Endpoint | Response |
| --- | --- |
| `/__doppelgng__/health` | `ready`; available even before a manifest exists |
| `/__doppelgng__/report` | Manifest plus this server process's request failures, as JSON |
| `/__doppelgng__/failures` | This server process's recorded 404/501 failures |
| `/__doppelgng__/asset/KEY` | Archived resource alias used for external assets |

Failures in the server's in-memory list are not a durable access log. Restarting the server clears them.

## Setup, verification, packaging, and tests

| Command | Behavior |
| --- | --- |
| `npm run setup` | Prepare the venv, exact Python pins, crawler, and browser; verify and reuse intact caches. |
| `npm run runtime:check` | Verify the managed cached runtime offline. Report missing/altered files without repairing them. Explicit runtime overrides receive file-existence checks. |
| `npm run package` | Build `dist/doppelgng.me-windows-x64.zip` and its `.sha256` file. |
| `npm run package -- --output dist/custom.zip` | Select another ZIP filename. |
| `npm test` | Run Python unittest discovery, then Node HTTP tests if Python passes. |

The packager always requires the managed pinned crawler and Windows runtime, even if capture uses explicit overrides. See [distribution](distribution.md).

## Environment variables

| Variable | Consumer | Effect |
| --- | --- | --- |
| `DOPPELGNG_PYTHON` | Setup and Python launcher | Select the base Python executable; normal commands prefer an existing `.venv/`. |
| `DOPPELGNG_CRAWLER` | Setup, runtime check, capture default | Select an external crawler directory. `--crawler` overrides it for capture. |
| `DOPPELGNG_WATERFOX` | Setup, runtime check, browser | Select the browser executable. |
| `DOPPELGNG_GECKODRIVER` | Setup, runtime check, browser | Select the driver executable. |
| `DOPPELGNG_MANIFEST` | Standalone preview server | Select a manifest unless `--manifest` is supplied. |
| `PORT` | Standalone preview server | Select the server port unless `--port` is supplied. Capture/validate use their own port option. |
| `REQUESTS_CA_BUNDLE` | Native capture session | Custom certificate-authority bundle. Takes precedence over `CURL_CA_BUNDLE`. |
| `CURL_CA_BUNDLE` | Native capture session | Custom CA bundle when `REQUESTS_CA_BUNDLE` is unset. |

If only one browser/driver override is set, the other defaults to its managed `.tools/` path. Use compatible executables that support the required browser protocol. Crawler overrides execute Python code and must be trusted. Native capture sessions do not inherit environment proxies or automatic netrc credentials.

The launcher sets UTF-8 mode, disables Python bytecode writes, and directs temporary files into `.tools/tmp/`. Offline runtime verification skips scratch-directory creation.

## Interaction scenarios

Use a JSON object whose keys are original URL paths. Query variants of the same path share the mapping. For example, save this as `scenarios.json`:

```json
{
  "/catalogue/": [
    { "action": "click", "selector": "#filter-toggle", "assert_selector": "#filters" },
    { "action": "hover", "selector": ".menu-trigger", "assert_selector": ".submenu" }
  ]
}
```

```sh
npm run crawl -- --url https://your-authorized-site.example --authorized --scenarios scenarios.json
```

Each scenario uses a CSS selector. Supported actions are `click`, `hover`, and `details`; `details` clicks the summary selector. `assert_selector` is optional and defaults to `selector`. The assertion element must exist after the action.

Each action starts from a fresh navigation on the original and the local page. Scenarios are independent, not a sequence of steps. They compare the assertion element's text, visibility, and selected state attributes, then compare screenshots and check local browser errors. They run in the active browser viewport, not once per configured viewport. Their screenshot comparison uses the built-in 1% ratio and channel threshold of 25; `--visual-tolerance` controls page-baseline comparisons.

The tool automatically adds native details controls and suitable disclosure buttons. Other discovered controls need coverage before a page can pass. Controls associated with a form are rejected by the scenario runner. A click handler outside a form can still have remote effects; choose actions you know are read-only.

Omitting `--scenarios` on resume retains the saved mapping. Pass a file containing `{}` to clear it. The repository's [fixture scenarios](../tests/fixture-scenarios.json) provide a runnable example.

## Exit behavior

Capture and validate return 0 for a complete capture and 1 for an incomplete result. Runtime/setup/export errors also fail. Invalid capture arguments use argparse's exit code 2. Successfully reading status returns 0 regardless of capture status. `--help` returns 0. Other failures can propagate their underlying process exit code or traceback; inspect stderr and the saved manifest.
