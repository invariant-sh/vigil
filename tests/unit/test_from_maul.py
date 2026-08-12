"""Tests for Maul report reader and from-maul conversion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.support.fakes import CapturingSuggestionWriter, StaticMaulReader

from vigil.adapters.maul.report_reader import JsonMaulReportReader
from vigil.application.from_maul import FromMaulService
from vigil.domain.errors import UnsupportedReportVersionError
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
