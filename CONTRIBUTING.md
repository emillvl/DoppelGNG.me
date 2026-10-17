# Contributing

Read the [architecture](docs/architecture.md) and [development guide](docs/development.md) before changing capture or validation behavior. The project reconstructs authorized frontend resources and records what it verified. Keep backend behavior and unexercised states explicit.

## Work on a change

Create a branch, prepare dependencies, and run `npm test`. Make the change, run the affected checks, and update the relevant documentation. For browser changes, use the owned fixture and inspect the resulting screenshots, browser errors, and manifest. Explain the concrete trigger and resulting behavior in the commit or pull request.

Add a regression test when it exercises a meaningful failure or contract. Preserve real failures; do not remove an error or raise a tolerance simply to obtain completion. Keep the original and reconstructed files distinct and retain request provenance.

## What belongs in Git

Commit source, tests, lockfiles, license notices, documentation, and small factual evidence summaries. The owned documentation screenshots under `docs/assets/` also belong in Git.

Keep downloaded runtimes, virtual environments, captures, raw responses, browser profiles, secrets, logs, and ZIP builds out of commits. The documented `captures/` and `delivery/` directories are ignored. Explicit custom output paths may need their own ignore rule. Review staged filenames and the diff before pushing.

## Dependency changes

Update direct ranges and exact Python pins together when required. Browser/crawler updates also need matching download/file hashes, source links, notices, runtime verification, and browser tests. Preserve upstream source and license text. A working local binary is not a substitute for a reviewed pin.

The Windows packager uses an allowlist. If a new runtime source file or documentation asset is needed in the ZIP, update that list and verify a built archive. Never include a captured website to make a fixture pass.

## Documentation and comments

Describe current behavior with runnable commands, exact defaults, and clear limits. Use sentence-case headings and plain words. Remove sales claims, canned introductions, repeated conclusions, decorative emoji, and comments that narrate the next line of code. Retain short comments that explain a non-obvious constraint or decision.

Keep historical counts and measurements attached to their recorded runs. Do not claim a test passed because an earlier report says it did. Use read-only actions in scenario examples and owned fixtures for screenshots.

## License

Contributions to the project's source and documentation are covered by the [MIT License](LICENSE). Dependency notices and captured website permissions remain separate.
