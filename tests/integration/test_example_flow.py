"""Integration tests over example fixtures."""

from __future__ import annotations

from pathlib import Path

from vigil.adapters.audit.jsonl_sink import JsonlAuditSink, JsonlDecisionSink
from vigil.adapters.config.loader import YamlPolicyLoader
from vigil.adapters.events.jsonl import JsonlEventSource
from vigil.adapters.maul.report_reader import JsonMaulReportReader
from vigil.adapters.runtime import SystemClock, UuidFactory
from vigil.adapters.suggestions_writer import YamlSuggestionWriter
from vigil.application.dry_run import DryRunService
from vigil.application.from_maul import FromMaulService
from vigil.application.validate import ValidatePolicyService


def test_validate_example_policy() -> None:
    result = ValidatePolicyService(policy_loader=YamlPolicyLoader()).execute(
        Path("examples/support_agent/vigil.yaml")
    )
    assert result.policy.scope.project == "support-agent"


def test_from_maul_example(tmp_path: Path) -> None:
    out = tmp_path / "suggestions.yaml"
    result = FromMaulService(
        report_reader=JsonMaulReportReader(),
        suggestion_writer=YamlSuggestionWriter(),
    ).execute(
        Path("examples/support_agent/reliability_report.json"),
        output_path=out,
        project="support-agent",
    )
    assert out.exists()
    assert len(result.draft.suggestions) >= 3


def test_dry_run_example(tmp_path: Path) -> None:
    decisions = tmp_path / "decisions.jsonl"
    audit = tmp_path / "audit.jsonl"
    result = DryRunService(
        policy_loader=YamlPolicyLoader(),
        event_source=JsonlEventSource(),
        decision_sink=JsonlDecisionSink(),
        audit_sink=JsonlAuditSink(),
        clock=SystemClock(),
        ids=UuidFactory(),
    ).execute(
        policy_path=Path("examples/support_agent/vigil.yaml"),
        events_path=Path("examples/support_agent/events.jsonl"),
        decisions_path=decisions,
        audit_path=audit,
    )
    assert decisions.exists()
    assert audit.exists()
    assert result.blocked_count >= 3
    assert result.routed_count >= 1
    codes = {record.reason_code for record in result.records}
    assert "call_cap_exceeded" in codes
    assert "circuit_breaker_tripped" in codes
    assert "tool_content_blocked" in codes
    assert "model_not_allowed" in codes
    assert "routed_to_fallback" in codes
