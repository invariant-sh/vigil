"""Redacted append-only JSONL audit sink."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vigil.domain.decision import DecisionRecord
from vigil.domain.errors import AuditError

AUDIT_SCHEMA_VERSION = "1"


class JsonlAuditSink:
    """Write redacted audit events derived from decision records."""

    def write(self, path: Path, records: tuple[DecisionRecord, ...]) -> Path:
        """Append audit events; create parent directories as needed."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(_to_audit_event(record), sort_keys=True))
                    handle.write("\n")
        except OSError as error:
            msg = f"unable to write audit file `{path}`: {error}"
            raise AuditError(msg) from error
        return path


class JsonlDecisionSink:
    """Write dry-run decision records as JSONL."""

    def write(self, path: Path, records: tuple[DecisionRecord, ...]) -> Path:
        """Overwrite destination with decision records."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record.to_dict(), sort_keys=True))
                    handle.write("\n")
        except OSError as error:
            msg = f"unable to write decisions file `{path}`: {error}"
            raise AuditError(msg) from error
        return path


def _to_audit_event(record: DecisionRecord) -> dict[str, Any]:
    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "timestamp": record.timestamp,
        "decision_id": record.decision_id,
        "policy_hash": record.policy_hash,
        "project": record.project,
        "environment": record.environment,
        "workflow_id": record.workflow_id,
        "request_id": record.request_id,
        "request_fingerprint": record.request_fingerprint,
        "action": record.action,
        "reason_code": record.reason_code,
        "requested_model": record.requested_model,
        "effective_model": record.effective_model,
        "estimated_cost": None
        if record.estimated_cost is None
        else record.estimated_cost.to_dict(),
        "workflow_call_count": record.workflow_call_count,
        "workflow_cost": record.workflow_cost.to_dict(),
    }
