"""JSONL request event source for dry-run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vigil.domain.errors import EventSourceError
from vigil.domain.events import RequestEvent
from vigil.domain.money import MicroUsd


class JsonlEventSource:
    """Load recorded request events from a JSONL file."""

    def load(self, path: Path) -> tuple[RequestEvent, ...]:
        """Parse one RequestEvent per non-empty line."""
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            msg = f"unable to read events file `{path}`: {error}"
            raise EventSourceError(msg) from error
        events: list[RequestEvent] = []
        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as error:
                msg = f"invalid JSON on line {line_no} of `{path}`: {error}"
                raise EventSourceError(msg) from error
            events.append(_parse_event(payload, line_no=line_no))
        if not events:
            msg = f"events file `{path}` contains no request events"
            raise EventSourceError(msg)
        return tuple(events)


def _parse_event(raw: Any, *, line_no: int) -> RequestEvent:
    if not isinstance(raw, dict):
        msg = f"line {line_no}: event must be a JSON object"
        raise EventSourceError(msg)
    unknown = {
        str(key)
        for key in raw
        if key
        not in {
            "request_id",
            "workflow_id",
            "project",
            "environment",
            "model",
            "request_fingerprint",
            "estimated_cost",
            "tool_content_flags",
        }
    }
    if unknown:
        msg = f"line {line_no}: unknown fields: {sorted(unknown)}"
        raise EventSourceError(msg)

    cost_raw = raw.get("estimated_cost")
    cost = None
    if cost_raw is not None:
        cost = _parse_cost(cost_raw, line_no=line_no)

    flags_raw = raw.get("tool_content_flags") or []
    if not isinstance(flags_raw, list):
        msg = f"line {line_no}: tool_content_flags must be a list"
        raise EventSourceError(msg)
    flags: list[str] = []
    for index, item in enumerate(flags_raw):
        if not isinstance(item, str) or not item.strip():
            msg = f"line {line_no}: tool_content_flags[{index}] must be a non-empty string"
            raise EventSourceError(msg)
        flags.append(item)

    try:
        return RequestEvent(
            request_id=_require_str(raw, "request_id", line_no=line_no),
            workflow_id=_require_str(raw, "workflow_id", line_no=line_no),
            project=_require_str(raw, "project", line_no=line_no),
            environment=_require_str(raw, "environment", line_no=line_no),
            model=_require_str(raw, "model", line_no=line_no),
            request_fingerprint=_require_str(raw, "request_fingerprint", line_no=line_no),
            estimated_cost=cost,
            tool_content_flags=tuple(flags),
        )
    except ValueError as error:
        msg = f"line {line_no}: {error}"
        raise EventSourceError(msg) from error


def _require_str(raw: dict[str, Any], key: str, *, line_no: int) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"line {line_no}: {key} must be a non-empty string"
        raise EventSourceError(msg)
    return value


def _parse_cost(raw: Any, *, line_no: int) -> MicroUsd:
    if isinstance(raw, dict):
        micro = raw.get("micro_usd")
        if isinstance(micro, bool) or not isinstance(micro, int):
            msg = f"line {line_no}: estimated_cost.micro_usd must be an integer"
            raise EventSourceError(msg)
        try:
            return MicroUsd(micro_usd=micro)
        except ValueError as error:
            msg = f"line {line_no}: {error}"
            raise EventSourceError(msg) from error
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        msg = f"line {line_no}: estimated_cost must be a money object or number"
        raise EventSourceError(msg)
    try:
        return MicroUsd.from_usd(float(raw))
    except ValueError as error:
        msg = f"line {line_no}: {error}"
        raise EventSourceError(msg) from error
