"""Decision types produced by the evaluation engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from vigil.domain.money import MicroUsd

DecisionAction = Literal["allow", "block", "route"]
DecisionReasonCode = Literal[
    "allowed",
    "model_not_allowed",
    "call_cap_exceeded",
    "cost_cap_exceeded",
    "circuit_breaker_tripped",
    "tool_content_blocked",
    "routed_to_fallback",
    "no_compliant_fallback",
]


@dataclass(frozen=True, slots=True)
class Decision:
    """Outcome of evaluating one request against a policy."""

    action: DecisionAction
    reason_code: DecisionReasonCode
    message: str
    requested_model: str
    effective_model: str | None = None

    @property
    def allowed(self) -> bool:
        """True when the request may proceed (possibly after routing)."""
        return self.action in {"allow", "route"}


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """Explainable dry-run decision with provenance (never contains prompts)."""

    schema_version: str
    decision_id: str
    timestamp: str
    policy_hash: str | None
    project: str
    environment: str
    workflow_id: str
    request_id: str
    request_fingerprint: str
    action: DecisionAction
    reason_code: DecisionReasonCode
    message: str
    requested_model: str
    effective_model: str | None
    estimated_cost: MicroUsd | None
    workflow_call_count: int
    workflow_cost: MicroUsd

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON persistence."""
        return {
            "schema_version": self.schema_version,
            "decision_id": self.decision_id,
            "timestamp": self.timestamp,
            "policy_hash": self.policy_hash,
            "project": self.project,
            "environment": self.environment,
            "workflow_id": self.workflow_id,
            "request_id": self.request_id,
            "request_fingerprint": self.request_fingerprint,
            "action": self.action,
            "reason_code": self.reason_code,
            "message": self.message,
            "requested_model": self.requested_model,
            "effective_model": self.effective_model,
            "estimated_cost": None
            if self.estimated_cost is None
            else self.estimated_cost.to_dict(),
            "workflow_call_count": self.workflow_call_count,
            "workflow_cost": self.workflow_cost.to_dict(),
        }


DECISION_SCHEMA_VERSION = "1"
