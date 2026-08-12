"""Extra coverage for adapter and domain error paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from vigil.adapters.config.loader import YamlPolicyLoader
from vigil.adapters.events.jsonl import JsonlEventSource
from vigil.correlation import CorrelationContext, merge_openai_client_kwargs
from vigil.domain.errors import EventSourceError, PolicyValidationError
from vigil.domain.events import RequestEvent
from vigil.domain.fingerprints import request_fingerprint
from vigil.domain.money import MicroUsd
from vigil.domain.policy import (
    AuditConfig,
    Budgets,
    CircuitBreakerControl,
    ModelPolicy,
    Policy,
    Scope,
    ToolContentGuardControl,
)
from vigil.domain.suggestions import EvidenceRef, PolicySuggestion


def test_loader_rejects_bad_yaml(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(":\n  -", encoding="utf-8")
    with pytest.raises(PolicyValidationError, match="invalid YAML"):
        YamlPolicyLoader().load(path)


def test_loader_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(PolicyValidationError, match="unable to read"):
        YamlPolicyLoader().load(tmp_path / "missing.yaml")


def test_loader_rejects_non_mapping(tmp_path: Path) -> None:
    path = tmp_path / "list.yaml"
    path.write_text("- just a list\n", encoding="utf-8")
    with pytest.raises(PolicyValidationError, match="mapping"):
        YamlPolicyLoader().load(path)


def test_loader_rejects_bad_control_type(tmp_path: Path) -> None:
    path = tmp_path / "policy.yaml"
    path.write_text(
        """
version: 1
scope: {project: p, environment: e}
models: {allow: [gpt-4o-mini]}
controls:
  - type: unknown_control
    mode: block
""",
        encoding="utf-8",
    )
    with pytest.raises(PolicyValidationError, match="type"):
        YamlPolicyLoader().load(path)


def test_loader_rejects_bad_audit_emit(tmp_path: Path) -> None:
    path = tmp_path / "policy.yaml"
    path.write_text(
        """
version: 1
scope: {project: p, environment: e}
models: {allow: [gpt-4o-mini]}
audit: {emit: yes-please}
""",
        encoding="utf-8",
    )
    with pytest.raises(PolicyValidationError, match=r"audit\.emit"):
        YamlPolicyLoader().load(path)


def test_event_source_rejects_empty(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    path.write_text("\n\n", encoding="utf-8")
    with pytest.raises(EventSourceError, match="no request events"):
        JsonlEventSource().load(path)


def test_event_source_rejects_unknown_field(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(
        '{"request_id":"r","workflow_id":"w","project":"p","environment":"e",'
        '"model":"m","request_fingerprint":"f","prompt":"secret"}\n',
        encoding="utf-8",
    )
    with pytest.raises(EventSourceError, match="unknown fields"):
        JsonlEventSource().load(path)


def test_request_event_invariants() -> None:
    with pytest.raises(ValueError, match="request_id"):
        RequestEvent(
            request_id=" ",
            workflow_id="w",
            project="p",
            environment="e",
            model="m",
            request_fingerprint="f",
        )


def test_policy_version_invariant() -> None:
    with pytest.raises(ValueError, match="unsupported policy version"):
        Policy(
            version=2,
            scope=Scope(project="p", environment="e"),
            budgets=Budgets(),
            models=ModelPolicy(allow=("gpt-4o-mini",)),
            controls=(),
            audit=AuditConfig(),
        )


def test_control_invariants() -> None:
    with pytest.raises(ValueError, match="max_occurrences"):
        CircuitBreakerControl(condition="repeated_equivalent_request", max_occurrences=0)
    with pytest.raises(ValueError, match="patterns"):
        ToolContentGuardControl(mode="block", patterns=())


def test_fingerprint_skips_non_dict_messages() -> None:
    digest = request_fingerprint(model="m", messages=[{"role": "user", "content": "x"}])
    assert len(digest) == 64


def test_correlation_rejects_empty_env() -> None:
    with pytest.raises(ValueError, match="environment"):
        CorrelationContext(project="p", environment=" ", workflow_id="w")


def test_merge_openai_requires_base_url() -> None:
    with pytest.raises(ValueError, match="base_url"):
        merge_openai_client_kwargs(
            CorrelationContext(project="p", environment="e", workflow_id="w"),
            base_url=" ",
        )


def test_money_from_usd_rejects_negative() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        MicroUsd.from_usd(-0.1)


def test_suggestion_to_dict_includes_optional_fields() -> None:
    suggestion = PolicySuggestion(
        kind="max_llm_calls",
        confidence="high",
        rationale="because",
        evidence=EvidenceRef(
            report_path="r.json",
            scenario_id=None,
            seed=1,
            request_index=0,
            budget_decision="CallCapExceeded",
        ),
        proposed_max_llm_calls=12,
        proposed_max_cost_usd=MicroUsd.from_usd(0.5),
        proposed_fallback_model="gpt-4o-mini",
        proposed_route_after_cost_usd=MicroUsd.from_usd(0.2),
        proposed_control=CircuitBreakerControl(
            condition="repeated_equivalent_request", max_occurrences=3
        ),
    )
    payload = suggestion.to_dict()
    assert payload["proposed_max_llm_calls"] == 12
    assert "proposed_control" in payload
