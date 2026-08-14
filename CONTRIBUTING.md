# Contributing to Vigil

By participating you agree to the [Code of Conduct](./CODE_OF_CONDUCT.md).
Org-wide process lives in [invariant-sh/.github](https://github.com/invariant-sh/.github/blob/main/CONTRIBUTING.md).

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest --cov=vigil --cov-report=term-missing
uv run python scripts/check_crap.py
```

This repository is the open policy SDK. Do not treat `vigil policy dry-run` as
live enforcement, and do not auto-deploy Maul suggestions.

## Pull requests

Target `main`. Keep PRs small. Do not commit `.env`, live `vigil.yaml` secrets,
prompt bodies, or `Authorization` material.

## Security

Report vulnerabilities privately. See [SECURITY.md](./SECURITY.md).
