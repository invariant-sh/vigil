"""Request events consumed by dry-run evaluation (no prompt bodies retained)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vigil.domain.money import MicroUsd


@dataclass(frozen=True, slots=True)
class RequestEvent:
    """One attributed LLM request for policy evaluation.

    Sensitive fields (prompt bodies, Authorization) must never appear here.
    Callers pass a precomputed fingerprint instead of raw messages.
    """

    request_id: str
    workflow_id: str
    project: str
    environment: str
    model: str
    request_fingerprint: str
    estimated_cost: MicroUsd | None = None
    tool_content_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            msg = "request_id must be non-empty"
            raise ValueError(msg)
        if not self.workflow_id.strip():
            msg = "workflow_id must be non-empty"
            raise ValueError(msg)
        if not self.model.strip():
            msg = "model must be non-empty"
            raise ValueError(msg)
        if not self.request_fingerprint.strip():
            msg = "request_fingerprint must be non-empty"
            raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSONL persistence."""
        return {
            "request_id": self.request_id,
            "workflow_id": self.workflow_id,
            "project": self.project,
            "environment": self.environment,
            "model": self.model,
            "request_fingerprint": self.request_fingerprint,
            "estimated_cost": None
            if self.estimated_cost is None
            else self.estimated_cost.to_dict(),
            "tool_content_flags": list(self.tool_content_flags),
        }
