"""Policy suggestions derived from Maul evidence (never auto-enforced)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from vigil.domain.money import MicroUsd
from vigil.domain.policy import Control, PolicyLifecycleStatus

SuggestionKind = Literal[
    "max_llm_calls",
    "max_cost_usd",
    "circuit_breaker",
    "tool_content_guard",
    "model_routing",
]

Confidence = Literal["low", "medium", "high"]


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """Pointer into a Maul reliability report without embedding secrets."""

    report_path: str | None
    scenario_id: str | None
    seed: int | None
    request_index: int | None
    budget_decision: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize evidence for draft YAML/JSON."""
        return {
            "report_path": self.report_path,
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "request_index": self.request_index,
            "budget_decision": self.budget_decision,
        }


@dataclass(frozen=True, slots=True)
class PolicySuggestion:
    """A human-reviewable control proposal derived from Maul findings."""

    kind: SuggestionKind
    confidence: Confidence
    rationale: str
    evidence: EvidenceRef
    proposed_max_llm_calls: int | None = None
    proposed_max_cost_usd: MicroUsd | None = None
    proposed_control: Control | None = None
    proposed_fallback_model: str | None = None
    proposed_route_after_cost_usd: MicroUsd | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for draft output."""
        payload: dict[str, Any] = {
            "kind": self.kind,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "evidence": self.evidence.to_dict(),
        }
        if self.proposed_max_llm_calls is not None:
            payload["proposed_max_llm_calls"] = self.proposed_max_llm_calls
        if self.proposed_max_cost_usd is not None:
            payload["proposed_max_cost_usd"] = self.proposed_max_cost_usd.to_dict()
        if self.proposed_control is not None:
            payload["proposed_control"] = _control_to_dict(self.proposed_control)
        if self.proposed_fallback_model is not None:
            payload["proposed_fallback_model"] = self.proposed_fallback_model
        if self.proposed_route_after_cost_usd is not None:
            payload["proposed_route_after_cost_usd"] = self.proposed_route_after_cost_usd.to_dict()
        return payload


@dataclass(frozen=True, slots=True)
class SuggestionDraft:
    """Draft policy document marked as suggested, awaiting human review."""

    version: int
    status: PolicyLifecycleStatus
    owner: str | None
    project: str
    environment: str
    suggestions: tuple[PolicySuggestion, ...]
    source_report_schema_version: str
    source_report_path: str | None

    def to_dict(self) -> dict[str, Any]:
        """Serialize a draft for YAML/JSON emission."""
        return {
            "version": self.version,
            "status": self.status,
            "owner": self.owner,
            "scope": {
                "project": self.project,
                "environment": self.environment,
            },
            "source": {
                "maul_report_schema_version": self.source_report_schema_version,
                "maul_report_path": self.source_report_path,
            },
            "suggestions": [item.to_dict() for item in self.suggestions],
            "review": {
                "note": (
                    "These are suggestions only. A policy owner must review scope, "
                    "limits, exceptions, and false-positive risk before deployment."
                ),
            },
        }


def _control_to_dict(control: Control) -> dict[str, Any]:
    if control.type == "circuit_breaker":
        return {
            "type": control.type,
            "condition": control.condition,
            "max_occurrences": control.max_occurrences,
        }
    return {
        "type": control.type,
        "mode": control.mode,
        "patterns": list(control.patterns),
    }
