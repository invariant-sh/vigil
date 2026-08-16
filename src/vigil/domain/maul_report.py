"""Typed view of a Maul reliability_report.json (schema 0.1 or 0.2)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MaulRequestFinding:
    """One request row relevant to policy suggestions."""

    index: int
    fault_injected: str | None
    budget_decision: str | None
    model: str | None
    session_id: str | None = None
    sequence: int | None = None
    status: int | None = None


@dataclass(frozen=True, slots=True)
class MaulReport:
    """Parsed Maul reliability report used by from-maul conversion."""

    schema_version: str
    source_path: str | None
    seed: int | None
    budget_rejections: int
    request_findings: tuple[MaulRequestFinding, ...]
    observed_cost_micro_usd: int | None = None
    calls_limit: int | None = None
    cost_limit_micro_usd: int | None = None
    run_id: str | None = None
    unrecovered_sessions: int = 0
    recovery_events: int = 0
    faults_injected: int = 0
