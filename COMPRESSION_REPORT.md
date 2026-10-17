# Waterfox compression experiment

Historical run record from 17 October 2026. Source states, counts, and archive hashes below refer to that run. Absolute artifact links refer to the original local workspace and are not included in this repository.

Executed on 2026-10-17 against the pinned Waterfox 6.7.6 Windows x64 runtime, reporting browser version 153.5.0, on this project's NTFS volume.

## Measured results

All sizes use decimal MB. File storage was measured through Windows `GetCompressedFileSizeW`, summed across the 64 browser-core files; directory metadata is excluded.

| Mode | File storage on disk | Saved | Median browser launch | Median page ready |
| --- | ---: | ---: | ---: | ---: |
| Uncompressed | 543.989 MB |; | 5.375 s | 5.890 s |
| XPRESS4K | 265.146 MB | 51.26% | 5.324 s | 5.838 s |
| LZX | 175.767 MB | 67.69% | 5.333 s | 5.842 s |

LZX saves 368,222,380 bytes, approximately 368 MB. Its compression and integrity verification took 9.9 seconds on the test copy; applying it to the actual runtime took 9.7 seconds including verification.

Timing used three sequential launches per mode with fresh browser profiles and a warm filesystem cache. Launch timing ends when the WebDriver browser session is ready; page-ready timing includes viewport setup and navigation. These samples do not establish cold-start performance or a general speed improvement.

## Quality checks

- All 66 pinned runtime and notice file hashes matched before and after compression. The 64 browser-core files retain their original 543,988,971 logical bytes.
- Nine headless browser launches passed across the three modes. Exact desktop and mobile viewports, authentic response-body capture, download byte equality, and computed script execution passed.
- The first desktop and mobile screenshots in each compressed mode were pixel-identical to the uncompressed reference images.
- LZX passed 24 existing desktop/mobile visual comparisons and all 11 navigation checks against baselines captured with the uncompressed runtime.
- Local replay worked after stopping the original test website, with all observed HTTP requests confined to the local preview.
- Decompression of the test copy restored its original size and hashes. Windows `compact.exe /U /EXE` was used on the same explicit runtime-file list.
- All 126 protected files in the user's existing website copy retained their hashes.
- After applying LZX to the actual project runtime, a further headless desktop/mobile launch and response-body check passed. The project suite passed 53 Python and 2 Node tests; the pinned upstream suite passed 33 tests, for 88 tests total. `npm run runtime:check` passed offline.

## Applied result and scope

LZX has been applied to this project's private `.tools/waterfox/core/` runtime. Only the 64 verified browser files were passed explicitly to `compact.exe /C /F /EXE:LZX`; no whole-volume or operating-system compression was requested. The extra experimental runtime was removed after testing; measurements, logs, screenshots, and the validation copy remain under ignored `.tools/compression-_a20ytxi/`.

Windows still reports a logical file size of approximately 544 MB, while actual file storage is approximately 176 MB. Use Size on disk when inspecting the result. Browser code and functionality are retained unchanged.

At the experiment milestone, the distribution ZIP remained 175,994,091 bytes with SHA256 `7fccb626cbfdfa1d3ee376632757ab989f16f2b08f463ac5de5c02498e4b56ff`. The ZIP does not carry NTFS compression state to a recipient.

Setup now automatically applies LZX to the manifest-verified private browser on Windows NTFS drives, including after extracting a delivery ZIP. It checks all runtime hashes before and after compression, passes only the explicit browser file list to `compact.exe`, and reuses a compression receipt only when the runtime manifest and measured storage still match. Unsupported filesystems retain the verified uncompressed runtime. Offline `runtime:check` does not modify storage. Explicit external browser overrides remain outside this process.

The updated delivery ZIP contains 120 application/runtime files, is 175,997,888 bytes, and has SHA256 `33744f1b6b8601b1341085dde829ea8e452d4c692fc9a47d1d80d4ee08407424`. Fresh extraction measured 543,988,971 browser-core bytes on disk; the recipient setup automatically reduced this to 175,766,591 bytes. Repeated setup reused LZX, offline verification passed, and two fresh packaged-browser sessions retained pixel-identical desktop/mobile rendering without creating a Waterfox Start Menu shortcut.

The measurement and compression mechanisms follow Microsoft's documentation for [compact](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/compact) and [GetCompressedFileSizeW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getcompressedfilesizew).
