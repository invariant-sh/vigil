# Contributing to Vigil

By participating you agree to the [Code of Conduct](./CODE_OF_CONDUCT.md).
Org-wide process lives in [invariant-sh/.github](https://github.com/invariant-sh/.github/blob/main/CONTRIBUTING.md).

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --group dev
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest --cov=vigil --cov-report=term-missing
uv run python scripts/check_crap.py
uv build
uvx twine check --strict dist/*
```

This repository is the open policy SDK. Do not treat `vigil policy dry-run` as
live enforcement, and do not auto-deploy Maul suggestions.

## Pull requests

Target `main`. Keep PRs small. Do not commit `.env`, live `vigil.yaml` secrets,
prompt bodies, or `Authorization` material.

## Releasing

Publishing uses PyPI Trusted Publishing. Do not create a PyPI API token, and do not `twine upload` from a laptop.

The distribution name is `invariant-vigil`. The import package and the `vigil` command stay `vigil`.

1. Set `version` in `pyproject.toml` and `__version__` in `src/vigil/__init__.py` to the same value, and update `CHANGELOG.md`.
2. Merge to `main`.
3. Push a tag `vX.Y.Z` that matches that version (for example `v0.2.0`). `.github/workflows/release.yml` builds with `uv build`, publishes to PyPI, and creates the GitHub release. Do not push a tag until the [pending publisher](https://pypi.org/manage/account/publishing/) below exists.

One-time PyPI pending publisher (the project does not exist yet, so this is under the account Publishing page, not a project page):

| Field | Value |
|---|---|
| PyPI project name | `invariant-vigil` |
| Owner | `invariant-sh` |
| Repository name | `vigil` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

Also create a GitHub environment named `pypi` with no secrets. The workflow filename and environment name must match the publisher exactly.

## Security

Report vulnerabilities privately. See [SECURITY.md](./SECURITY.md).
