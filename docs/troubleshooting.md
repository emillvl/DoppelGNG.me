# Troubleshooting

## Setup cannot find Python or pip

Select a real Python 3.10+ executable through `DOPPELGNG_PYTHON` and rerun setup. A Windows app-execution alias may exist without a usable interpreter. Setup first tries normal venv creation, then creation without pip. If the venv has no pip module, it uses the base interpreter's pip with `--python` to install into the venv.

An existing `.venv/` takes precedence for normal commands. Keep the interpreter installation used to create it available. Preserve any local environment changes before replacing a broken environment.

## First setup needs Git or 7-Zip

Git is needed to fetch the managed crawler from a source checkout. Windows source setup also needs `7z` on PATH or at `C:\Program Files\7-Zip\7z.exe` to unpack the official Waterfox installer. A complete Windows distribution already includes those fetched files and does not require either tool.

## Managed files differ from the pinned revision

Run `npm run runtime:check` to identify the missing or changed file. Setup refuses altered managed crawler/browser contents; it does not overwrite local modifications. Preserve those files and use a separate project cache or a deliberate crawler override. Setup can repair crawler provenance metadata when the pinned source contents are intact; offline verification reports the problem without repairing it.

Do not edit pinned hashes merely to make a check pass. A deliberate runtime update requires a reviewed lockfile, matching source/download information, and renewed verification.

## Browser fails to start or response bodies are unavailable

Check `artifacts/geckodriver.log`, `npm run runtime:check`, and explicit executable paths. Overrides must point to compatible Waterfox/geckodriver binaries. Response-body collection depends on browser protocol support; a driver that can navigate pages may still lack the required collector. The browser identity records collector setup errors.

On a platform without automatic provisioning, configure both executables. The recorded compatibility evidence covers the pinned Windows runtime.

## Local port is busy

Capture and validate start a temporary replay server on port 4173. Use another unused port:

```sh
npm run crawl -- --url https://your-authorized-site.example --authorized --port 4180
npm run validate -- --output example.com --port 4180
npm run dev -- --manifest example.com/manifest.json --port 4180
```

Stop a preview you started before reusing its port. Preview startup errors are retained in `artifacts/server.log` and the incomplete manifest.

## The workspace is busy

`Another capture or validation owns ...` means an operation holds the workspace lock, or an active legacy PID owner was detected. Let it finish or stop the process you started. A persistent `capture.lock` file after exit is expected. Deleting it while another process runs can undermine workspace protection and does not release that process's OS lock.

Separate captures can use separate output directories and preview ports.

## No current capture, wrong target, or unrelated output folder

Use an explicit `--output` for status/validate/export and `--manifest` for preview. Current selection lives in `.doppelgng/current.json` relative to the command's working directory. A copied project should be served from its own directory.

Capture refuses an unrelated existing folder, another target's manifest, or a changed crawler identity. Select a new output path rather than mixing archives. Folder names from earlier captures remain usable through `--output`.

## Robots or sitemap discovery stops capture

Inspect the page's `reason` and `manifest.json` discovery observations. `--respect-robots` is the default. For a site whose owner has authorized ignoring those rules, use `--ignore-robots` explicitly.

An undeclared default sitemap returning 404 or 410 is optional. Other sitemap HTTP/XML failures stop discovery. Sitemap processing permits at most 100 maps and 10,000,000 bytes per map; reaching a bound is an explicit failure. Linked-page discovery does not establish coverage of hidden URLs.

## A private dependency is rejected

The target's origin is authorized. Other private resource origins need separate authorization:

```sh
npm run crawl -- --url http://localhost:4318 --authorized --authorize-resource-origin http://localhost:4319
```

Authorize only origins you own or may reproduce. Scheme, hostname, and effective port must match, including redirect destinations. Extra resource authorization does not expand page scope. Native capture does not inherit proxy settings; a proxy-only network needs separate integration. Custom CA files can be supplied through the [documented variables](cli.md#environment-variables).

## A page remains incomplete

Read that page's `error` and `validation.errors` in the manifest, then inspect its `artifacts/` directory. `baseline.json` identifies original screenshots. `validation.json` records measured snapshot differences. `interactions.json` identifies untested controls or failed scenarios. Integration results in the manifest identify failed navigation edges.

Run status to inspect the saved state, then repeat the capture command to retry. Integrity failures require intact original/local bytes. Changing checks can invalidate earlier passes. Raising tolerance does not repair a missing image, browser error, incorrect route, or unsupported control.

Animations, changing content, timed widgets, font availability, encodings, and services can produce real differences. Diagnose the specific state before changing a threshold. There is no universal setting that makes an arbitrary website equivalent.

## An interactive control needs a scenario

Add a path mapping and read-only action to a scenario file, then rerun capture with `--scenarios`. Use an assertion selector that identifies the resulting state. Every action starts from a fresh page; the format does not support a chain of dependent actions.

The runner refuses controls associated with forms. Backend behavior needs a separately authorized service test or implementation. A visually matching button does not establish that its remote operation was reconstructed.

## Local requests return 404 or 501

404 means no matching archived resource or available local file exists. Check the original URL, query, final redirect URL, and manifest record. Exact queries matter. 501 means the request method was not captured for replay. The server deliberately reports it rather than inventing a successful service response.

Inspect `/__doppelgng__/failures` while the server runs. Some scripts construct external URLs at runtime; an archived asset can exist while the script still calls its original host. Offline replay must be tested separately for that site. External frames can also fail because their replay sandbox gives them an opaque origin.

## Export or packaging fails

Export requires complete status, intact raw/local hashes, and an unused destination outside the capture. A retained `.partial` directory is evidence of a prior interrupted/failed copy. Inspect and preserve it before choosing a different destination.

Packaging requires the managed runtime. External overrides do not supply the packaged files. Run setup and offline verification in the source project. Check destination permissions and disk space. A failed ZIP build can leave a `.part` file; the final ZIP is installed only after its entries pass hash verification.

## Tests fail on localhost permissions

Some tests create owned loopback HTTP servers and connections. A restricted runner can deny sockets with Windows error 10013 or Node `EACCES`. Run the same suite in an environment that permits those local fixtures. Report an environment failure separately from a failing assertion; do not suppress network tests to obtain a passing count.
