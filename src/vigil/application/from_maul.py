"""Convert reviewed Maul findings into human-reviewable policy suggestions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vigil.domain.maul_report import MaulReport, MaulRequestFinding
from vigil.domain.money import MicroUsd
from vigil.domain.policy import CircuitBreakerControl, ToolContentGuardControl
from vigil.domain.suggestions import (
    EvidenceRef,
    PolicySuggestion,
    SuggestionDraft,
)
from vigil.ports import MaulReportReader, SuggestionWriter

DEFAULT_CIRCUIT_MAX = 3
DEFAULT_CALL_CAP = 12
DEFAULT_COST_CAP_USD = 0.75


@dataclass(frozen=True, slots=True)
class FromMaulResult:
    """Outcome of converting a Maul report into a suggestion draft."""

    draft: SuggestionDraft
    output_path: Path


class FromMaulService:
    """Map Maul reliability evidence to Vigil policy stubs (never auto-deployed)."""

    def __init__(
        self,
        *,
        report_reader: MaulReportReader,
        suggestion_writer: SuggestionWriter,
    ) -> None:
        self._report_reader = report_reader
        self._suggestion_writer = suggestion_writer

    def execute(
        self,
        report_path: Path,
        *,
        output_path: Path,
        project: str = "unnamed-project",
        environment: str = "production",
    ) -> FromMaulResult:
        """Read a Maul report and write a suggestion draft."""
        report = self._report_reader.read(report_path)
        suggestions = _suggestions_from_report(report)
        draft = SuggestionDraft(
            version=1,
            status="suggested",
            owner=None,
            project=project,
            environment=environment,
            suggestions=suggestions,
            source_report_schema_version=report.schema_version,
            source_report_path=report.source_path,
        )
        written = self._suggestion_writer.write(output_path, draft)
        return FromMaulResult(draft=draft, output_path=written)


def _suggestions_from_report(report: MaulReport) -> tuple[PolicySuggestion, ...]:
    suggestions: list[PolicySuggestion] = []
    suggestions.extend(_budget_suggestions(report))
    suggestions.extend(_fault_suggestions(report))
    return tuple(_dedupe(suggestions))


def _budget_suggestions(report: MaulReport) -> list[PolicySuggestion]:
    results: list[PolicySuggestion] = []
    call_suggestion = _call_cap_suggestion(report)
    if call_suggestion is not None:
        results.append(call_suggestion)
    cost_suggestion = _cost_cap_suggestion(report)
    if cost_suggestion is not None:
        results.append(cost_suggestion)
    return results


def _findings_with_budget(report: MaulReport, decision: str) -> list[MaulRequestFinding]:
    return [finding for finding in report.request_findings if finding.budget_decision == decision]


def _call_cap_suggestion(report: MaulReport) -> PolicySuggestion | None:
    hits = _findings_with_budget(report, "CallCapExceeded")
    if not hits and report.budget_rejections <= 0:
        return None
    if report.calls_limit and report.calls_limit > 0:
        proposed = report.calls_limit
    else:
        proposed = DEFAULT_CALL_CAP
    return PolicySuggestion(
        kind="max_llm_calls",
        confidence="high" if hits else "medium",
        rationale=(
            "Maul observed budget call-cap pressure; propose a per-workflow "
            "max_llm_calls limit for human review."
        ),
        evidence=_evidence(report, hits[0] if hits else None, budget_decision="CallCapExceeded"),
        proposed_max_llm_calls=proposed,
    )


def _cost_cap_suggestion(report: MaulReport) -> PolicySuggestion | None:
    hits = _findings_with_budget(report, "CostCapExceeded")
    if not hits:
        return None
    if report.cost_limit_micro_usd and report.cost_limit_micro_usd > 0:
        proposed_cost = MicroUsd(micro_usd=report.cost_limit_micro_usd)
    else:
        proposed_cost = MicroUsd.from_usd(DEFAULT_COST_CAP_USD)
    return PolicySuggestion(
        kind="max_cost_usd",
        confidence="high",
        rationale=(
            "Maul observed CostCapExceeded decisions; propose a per-workflow "
            "cost budget for human review."
        ),
        evidence=_evidence(report, hits[0], budget_decision="CostCapExceeded"),
        proposed_max_cost_usd=proposed_cost,
    )


def _fault_suggestions(report: MaulReport) -> list[PolicySuggestion]:
    results: list[PolicySuggestion] = []
    retry = _circuit_breaker_suggestion(report)
    if retry is not None:
        results.append(retry)
    guard = _tool_guard_suggestion(report)
    if guard is not None:
        results.append(guard)
    return results


def _circuit_breaker_suggestion(report: MaulReport) -> PolicySuggestion | None:
    retry_faults = ("force_429", "force_500")
    hits = [
        finding for finding in report.request_findings if finding.fault_injected in retry_faults
    ]
    if not hits:
        return None
    return PolicySuggestion(
        kind="circuit_breaker",
        confidence="medium",
        rationale=(
            "Maul injected retry/availability faults; a circuit breaker on "
            "repeated_equivalent_request can bound retry loops in production."
        ),
        evidence=_evidence(report, hits[0]),
        proposed_control=CircuitBreakerControl(
            condition="repeated_equivalent_request",
            max_occurrences=DEFAULT_CIRCUIT_MAX,
        ),
    )


def _tool_guard_suggestion(report: MaulReport) -> PolicySuggestion | None:
    hits = [
        finding
        for finding in report.request_findings
        if finding.fault_injected == "malformed_tool_call_json"
    ]
    if not hits:
        return None
    return PolicySuggestion(
        kind="tool_content_guard",
        confidence="medium",
        rationale=(
            "Maul injected malformed tool-call JSON; a tool content guard can "
            "block known instruction-override patterns at runtime."
        ),
        evidence=_evidence(report, hits[0]),
        proposed_control=ToolContentGuardControl(
            mode="block",
            patterns=("instruction_override",),
        ),
    )


def _evidence(
    report: MaulReport,
    finding: MaulRequestFinding | None,
    *,
    budget_decision: str | None = None,
) -> EvidenceRef:
    return EvidenceRef(
        report_path=report.source_path,
        scenario_id=None if finding is None else finding.fault_injected,
        seed=report.seed,
        request_index=None if finding is None else finding.index,
        budget_decision=budget_decision
        if budget_decision is not None
        else (None if finding is None else finding.budget_decision),
    )


def _dedupe(suggestions: list[PolicySuggestion]) -> list[PolicySuggestion]:
    seen: set[str] = set()
    unique: list[PolicySuggestion] = []
    for item in suggestions:
        if item.kind in seen:
            continue
        seen.add(item.kind)
        unique.append(item)
    return unique
