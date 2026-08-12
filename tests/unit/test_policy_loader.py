"""Tests for YamlPolicyLoader."""

from __future__ import annotations

from pathlib import Path

import pytest

from vigil.adapters.config.loader import YamlPolicyLoader
from vigil.domain.errors import PolicyValidationError


def test_loads_example_policy(tmp_path: Path) -> None:
    example = Path("contracts/policy.v1.example.yaml")
    policy = YamlPolicyLoader().load(example)
    assert policy.version == 1
    assert policy.scope.project == "support-agent"
    assert policy.budgets.max_llm_calls_per_workflow == 12
    assert policy.content_hash is not None
    assert len(policy.controls) == 2


def test_rejects_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        """
version: 1
scope: {project: p, environment: e}
models: {allow: [gpt-4o-mini]}
extra: true
""",
        encoding="utf-8",
    )
    with pytest.raises(PolicyValidationError, match="unknown top-level"):
        YamlPolicyLoader().load(path)


def test_rejects_unsupported_version(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        """
version: 99
scope: {project: p, environment: e}
models: {allow: [gpt-4o-mini]}
""",
        encoding="utf-8",
    )
    with pytest.raises(PolicyValidationError, match="unsupported policy version"):
        YamlPolicyLoader().load(path)


def test_routing_without_fallback_fails(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        """
version: 1
scope: {project: p, environment: e}
models:
  allow: [gpt-4o-mini]
  route_after_cost_usd: 0.1
""",
        encoding="utf-8",
    )
    with pytest.raises(PolicyValidationError, match="fallback_model"):
        YamlPolicyLoader().load(path)
