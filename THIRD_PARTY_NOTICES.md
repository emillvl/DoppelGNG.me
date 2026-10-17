# Included dependency notices

The Windows distribution retains dependency files and notices separately from DoppelGNG.me source. The browser runtime is included intact, rather than extracting only its executable.

- **WebCrawler** — [emillvl/webcrawler](https://github.com/emillvl/webcrawler), revision pinned in `runtime-lock.json`. Its original MIT license is included at `.tools/webcrawler/LICENSE`, alongside the selected, unmodified source files and upstream tests.
- **Waterfox** — official release pinned in `runtime-lock.json`. Its complete `core/` runtime, including embedded third-party notices accessible at `about:license`, is included at `.tools/waterfox/core/`. The exact source revision is linked in `runtime-lock.json` and `.tools/runtime-manifest.json`.
- **geckodriver** — [Mozilla geckodriver](https://github.com/mozilla/geckodriver), release pinned in `runtime-lock.json`. Its Mozilla Public License 2.0 text is included at `.tools/licenses/MPL-2.0.txt`; corresponding source is available at the linked release tag.
- **Python dependencies** — versions are pinned in `requirements.lock.txt` and installed into the user's project environment during setup. Their installed distributions retain their respective license metadata.

Copied-website output contains captured frontend resources supplied by the authorized target. It does not include Waterfox or require the crawler to run its local development server.
