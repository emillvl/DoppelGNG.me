# Installation and first capture

## Requirements

| Dependency | Source checkout | Extracted Windows distribution | Copied website |
| --- | --- | --- | --- |
| Node.js 22+ | Required | Required | Use the same supported Node version |
| Python 3.10+ | Required | Required | Not required for replay |
| Git | Required to clone and fetch the managed crawler on first setup | Not required | Not required |
| 7-Zip | Required to unpack Waterfox on first Windows x64 setup | Not required | Not required |
| Separate Waterfox installation | Not required | Not required | Not required |

Automatic runtime installation supports Windows x64. Setup checks the official Waterfox and geckodriver downloads before unpacking them. It does not run the Waterfox installer. On other platforms, provide compatible executables through `DOPPELGNG_WATERFOX` and `DOPPELGNG_GECKODRIVER`. Those platforms and alternative runtimes have not been verified by the recorded Windows runs.

Source setup and initial Python installation need network access. A Windows distribution already contains the browser and crawler, but its first setup still installs Python packages. An intact, previously prepared checkout can reuse its cached dependencies.

## Install from source

Run these commands from the project directory:

```sh
npm install
npm run setup
npm run runtime:check
```

`npm install` prepares the npm project. The project has no npm runtime dependencies. `npm run setup` creates `.venv/`, installs the exact versions in `requirements.lock.txt`, fetches the selected crawler files, and prepares the browser. Use `npm ci` instead of `npm install` when checking the committed npm lockfile.

Setup retains the complete browser core, including its libraries and notices. Temporary browser profiles disable default-browser prompts and the Private Browsing shortcut that Waterfox can otherwise create on startup. Manually launching the internal executable can still open Waterfox.

On Windows NTFS, setup applies LZX to verified browser files and verifies them again afterward. Repeated setup checks both the runtime manifest and actual storage before reusing the compression receipt. Other filesystems keep the runtime uncompressed. `runtime:check` verifies cached files and provenance without downloading, repairing metadata, or changing compression.

If Python is installed under a different command or location, set the interpreter before setup. In PowerShell:

```powershell
$env:DOPPELGNG_PYTHON = 'C:\Python313\python.exe'
npm run setup
```

Replace that example path with your interpreter. Once `.venv/` exists, normal project commands prefer its interpreter.

## Capture

```sh
npm run crawl -- --url https://your-authorized-site.example --authorized
```

The `--authorized` flag confirms that you own the site or have permission to reproduce it. It is required on every capture invocation, including resume.

The target's scheme, hostname, and port define page scope. Same-origin links from original HTML, rendered DOM, interaction states, and sitemap indexes feed discovery. Scrolling exposes lazy assets and browser prefetches. Subdomains and alternate ports do not automatically become page targets.

By default, output goes into a directory named after the target authority. `https://example.com` produces `example.com/`; `http://127.0.0.1:4318` produces `127.0.0.1_4318/`. The `www` prefix is kept when it is part of the supplied host. Windows-reserved names are prefixed with `_`.

Use a separate explicit path for repeated experiments:

```sh
npm run crawl -- --url https://your-authorized-site.example --authorized --output captures/example
```

An existing unrelated directory causes an error. A workspace belonging to another target or crawler source also causes an error. Completed resources and raw originals remain on disk when a capture stops.

## Inspect and preview

```sh
npm run status -- --output captures/example
npm run dev -- --manifest captures/example/manifest.json --port 4173
```

Open `http://127.0.0.1:4173`. The server binds to loopback. Stop it with Ctrl+C. A missing resource returns 404; an uncaptured non-GET operation returns 501. There is no server-side network fallback.

Without an explicit output path, status, validate, and export select the manifest recorded in `.doppelgng/current.json`. The preview server also uses that pointer unless you give it `--manifest` or `DOPPELGNG_MANIFEST`. Supplying paths explicitly avoids changing targets when working with several captures.

You can serve a partial capture to inspect failures. Its manifest remains incomplete until all required checks pass.

## Resume and validate

Repeat the capture command with the same target and output:

```sh
npm run crawl -- --url https://your-authorized-site.example --authorized --output captures/example
```

The tool reuses verified page checks and retries pending, failed, or corrupt work. A changed viewport list, stricter visual tolerance, or changed scenario mapping invalidates affected page checks. Evidence that passed a stricter tolerance can be reused when the tolerance loosens. Changes to shared responses or rewritten bytes also invalidate dependent pages.

Scenarios and extra resource-origin authorizations are retained when their options are omitted on resume. Repeat custom viewport, tolerance, robots, checkpoint, and quiet settings if you want those settings again; their CLI defaults apply on each invocation.

To recheck an existing capture against its saved baselines:

```sh
npm run validate -- --output captures/example --port 4173
```

Validation checks the local replay and reruns interaction comparisons against the original site. Keep the original reachable. Validation does not refresh the original screenshot baselines; use capture when changed verification requirements need fresh extraction.

One capture, validation, or CLI export operation can own a workspace at a time. The `capture.lock` file remains after exit, but the operating-system lock releases when its owner exits. Its presence alone does not mean another process is active.

## Export

```sh
npm run export -- --output captures/example --destination delivery/example.com
cd delivery/example.com
npm install
npm run dev
```

Export requires `complete` status and verifies original and local resource hashes before copying and again afterward. It refuses an existing destination or an existing `.partial` staging folder. The destination must sit outside the capture workspace. If the destination resolves to the capture itself, export returns that path without copying.

Omitting `--destination` selects the domain-based folder in the current directory. Choose a destination explicitly when the original capture already uses that default name and you want a second copy.

The exported directory includes `site/`, `raw/`, `artifacts/`, crawler checkpoints, the manifest, and the replay project. It needs Node.js to serve; Python and browser binaries are not copied. Review raw responses, screenshots, and logs before sharing the directory.

`DOPPELGNG_LICENSE.txt` accompanies the replay server. It covers the application's code, not the captured website assets. Export adds this notice even when the source is an older capture.

See the [command reference](cli.md) for controls and [troubleshooting](troubleshooting.md) for failure messages.
