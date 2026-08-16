"""Contract tests for supported Maul report schema versions."""

from __future__ import annotations

from pathlib import Path

from vigil.adapters.holds.baseline_reader import JsonHoldsBaselineReader
from vigil.adapters.maul.report_reader import SUPPORTED_SCHEMA_VERSIONS, JsonMaulReportReader
from vigil.adapters.suggestions_writer import YamlSuggestionWriter
from vigil.application.from_maul import FromMaulService


def test_supported_schema_versions_are_explicit() -> None:
    assert frozenset({"0.1", "0.2"}) == SUPPORTED_SCHEMA_VERSIONS


def test_schema_0_2_fixture_converts_to_non_enforcing_draft(tmp_path: Path) -> None:
    out = tmp_path / "suggestions.yaml"
    result = FromMaulService(
        report_reader=JsonMaulReportReader(),
        suggestion_writer=YamlSuggestionWriter(),
    ).execute(
        Path("contracts/maul/reliability_report.v0.2.example.json"),
        output_path=out,
        project="support-agent",
        holds_quality=JsonHoldsBaselineReader().read(
            Path("contracts/holds/baseline.v1.example.json")
        ),
    )
    assert result.draft.status == "suggested"
    assert result.draft.owner is None
    kinds = {item.kind for item in result.draft.suggestions}
    assert "max_llm_calls" in kinds
    assert "max_cost_usd" in kinds
    assert "circuit_breaker" in kinds
    assert "tool_content_guard" in kinds
    assert "model_routing" in kinds
    routing = next(item for item in result.draft.suggestions if item.kind == "model_routing")
    assert routing.proposed_fallback_model == "gpt-4o-mini"
    assert routing.evidence.applicability == "openai-compatible-agent-traffic"
