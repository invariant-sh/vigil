"""Tests for Maul report reader and from-maul conversion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.support.fakes import CapturingSuggestionWriter, StaticMaulReader

from vigil.adapters.holds.baseline_reader import JsonHoldsBaselineReader
from vigil.adapters.maul.report_reader import JsonMaulReportReader
from vigil.application.from_maul import FromMaulService
from vigil.domain.errors import HoldsBaselineError, UnsupportedReportVersionError
from vigil.domain.holds_baseline import HoldsQualityEvidence
from vigil.domain.maul_report import MaulReport, MaulRequestFinding


def test_reads_example_report() -> None:
    report = JsonMaulReportReader().read(Path("examples/support_agent/reliability_report.json"))
    assert report.schema_version == "0.1"
    assert report.budget_rejections == 1
    assert any(f.budget_decision == "CallCapExceeded" for f in report.request_findings)
    assert any(f.fault_injected == "force_429" for f in report.request_findings)


def test_rejects_unsupported_version(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(
        json.dumps({"schema_version": "9.9", "requests": [], "summary": {}}), encoding="utf-8"
    )
    with pytest.raises(UnsupportedReportVersionError):
        JsonMaulReportReader().read(path)


def test_reads_schema_0_2_contract_fixture() -> None:
    report = JsonMaulReportReader().read(
        Path("contracts/maul/reliability_report.v0.2.example.json")
    )
    assert report.schema_version == "0.2"
    assert report.run_id == "maul-fixture-0001"
    assert report.seed == 42
    assert report.calls_limit == 12
    assert report.cost_limit_micro_usd == 750_000
    assert report.unrecovered_sessions == 1
    assert report.recovery_events == 0
    assert report.faults_injected == 3
    assert report.request_findings[0].session_id == "session-a"
    assert report.request_findings[0].sequence == 1
    assert report.request_findings[0].status == 429


def test_reads_holds_baseline_contract_fixture() -> None:
    evidence = JsonHoldsBaselineReader().read(Path("contracts/holds/baseline.v1.example.json"))
    assert evidence.threshold_passed is True
    assert evidence.model_id == "gpt-4o-mini"
    assert evidence.pass_rate == 1.0


def test_holds_baseline_rejects_missing_threshold(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps({"summary": {"pass_rate": 1.0}}), encoding="utf-8")
    with pytest.raises(HoldsBaselineError, match="threshold_passed"):
        JsonHoldsBaselineReader().read(path)


def test_from_maul_maps_findings() -> None:
    report = MaulReport(
        schema_version="0.1",
        source_path="artifacts/report.json",
        seed=7,
        budget_rejections=1,
        request_findings=(
            MaulRequestFinding(0, "force_429", "Allowed", "gpt-4o-mini"),
            MaulRequestFinding(1, "malformed_tool_call_json", "Allowed", "gpt-4o-mini"),
            MaulRequestFinding(2, None, "CallCapExceeded", "gpt-4o-mini"),
            MaulRequestFinding(3, None, "CostCapExceeded", "gpt-4o-mini"),
        ),
        calls_limit=12,
        cost_limit_micro_usd=750_000,
    )
    writer = CapturingSuggestionWriter()
    service = FromMaulService(report_reader=StaticMaulReader(report), suggestion_writer=writer)
    result = service.execute(Path("ignored.json"), output_path=Path("out.yaml"), project="p")
    kinds = {s.kind for s in result.draft.suggestions}
    assert kinds == {"max_llm_calls", "max_cost_usd", "circuit_breaker", "tool_content_guard"}
    assert result.draft.status == "suggested"
    assert result.draft.owner is None
    assert writer.draft is not None
    evidence = result.draft.suggestions[0].evidence
    assert evidence.applicability == "openai-compatible-agent-traffic"


def test_from_maul_does_not_suggest_routing_without_holds() -> None:
    report = _cost_pressure_report()
    writer = CapturingSuggestionWriter()
    service = FromMaulService(report_reader=StaticMaulReader(report), suggestion_writer=writer)
    result = service.execute(Path("ignored.json"), output_path=Path("out.yaml"))
    kinds = {s.kind for s in result.draft.suggestions}
    assert "model_routing" not in kinds
    assert "max_cost_usd" in kinds


def test_from_maul_suggests_routing_when_holds_baseline_passes() -> None:
    report = _cost_pressure_report()
    writer = CapturingSuggestionWriter()
    service = FromMaulService(report_reader=StaticMaulReader(report), suggestion_writer=writer)
    result = service.execute(
        Path("ignored.json"),
        output_path=Path("out.yaml"),
        holds_quality=HoldsQualityEvidence(
            source_path="baselines/accepted.json",
            threshold_passed=True,
            pass_rate=1.0,
            model_id="gpt-4o-mini",
            suite_hash="abc",
            run_id="run-1",
        ),
    )
    routing = next(s for s in result.draft.suggestions if s.kind == "model_routing")
    assert routing.proposed_fallback_model == "gpt-4o-mini"
    assert routing.evidence.confidence_note is not None
    assert "holds_baseline" in routing.evidence.confidence_note


def test_from_maul_skips_routing_when_holds_threshold_fails() -> None:
    report = _cost_pressure_report()
    writer = CapturingSuggestionWriter()
    service = FromMaulService(report_reader=StaticMaulReader(report), suggestion_writer=writer)
    result = service.execute(
        Path("ignored.json"),
        output_path=Path("out.yaml"),
        holds_quality=HoldsQualityEvidence(
            source_path="baselines/failed.json",
            threshold_passed=False,
            pass_rate=0.2,
            model_id="gpt-4o-mini",
            suite_hash="abc",
            run_id="run-1",
        ),
    )
    kinds = {s.kind for s in result.draft.suggestions}
    assert "model_routing" not in kinds


def test_circuit_breaker_confidence_rises_with_unrecovered_sessions() -> None:
    report = MaulReport(
        schema_version="0.2",
        source_path="artifacts/report.json",
        seed=1,
        budget_rejections=0,
        request_findings=(MaulRequestFinding(0, "force_500", "Allowed", "gpt-4o-mini"),),
        unrecovered_sessions=2,
    )
    writer = CapturingSuggestionWriter()
    service = FromMaulService(report_reader=StaticMaulReader(report), suggestion_writer=writer)
    result = service.execute(Path("ignored.json"), output_path=Path("out.yaml"))
    breaker = next(s for s in result.draft.suggestions if s.kind == "circuit_breaker")
    assert breaker.confidence == "high"


def _cost_pressure_report() -> MaulReport:
    return MaulReport(
        schema_version="0.2",
        source_path="artifacts/report.json",
        seed=7,
        budget_rejections=1,
        request_findings=(MaulRequestFinding(0, None, "CostCapExceeded", "gpt-4o-mini"),),
        cost_limit_micro_usd=750_000,
    )
