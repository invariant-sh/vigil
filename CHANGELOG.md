# Changelog

All notable changes to the Vigil SDK are documented here. The PyPI distribution name is `invariant-vigil`. The import package and the `vigil` command stay `vigil`.

## 0.2.0 — 2026-10-24

### Added

- PyPI release metadata for distribution `invariant-vigil` at version 0.2.0. The name `vigil` is already registered on PyPI to an unrelated project, so this SDK publishes as `invariant-vigil`. `import vigil` and the `vigil` console script are unchanged.
- GitHub Actions workflow `.github/workflows/release.yml`. A `v*` tag builds the sdist and wheel with uv, publishes to PyPI with Trusted Publishing (OIDC, environment `pypi`), and attaches those artifacts to a GitHub release. The repository stores no PyPI API token.
- Install instructions for the checksum-verified [Maul v0.1.0](https://github.com/invariant-sh/maul/releases/tag/v0.1.0) release assets (Linux and macOS, x86_64 and aarch64).

### Changed

- Development dependencies moved from `[tool.uv] dev-dependencies` to `[dependency-groups] dev`. Use `uv sync --group dev`. The `dev` extra remains for `uv sync --extra dev`.

### Unchanged

- Maul report schemas `0.1` and `0.2` are still accepted. The correlation header `X-Vigil-Sdk-Version` remains the protocol value `0.1.0`.

## 0.1.0

- Open policy foundation: `vigil.yaml` validation, Maul-report suggestions (routing gated on a Holds baseline), explainable dry-run with redacted audit events, and OpenAI-compatible correlation helpers.
