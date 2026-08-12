"""Correlation metadata helpers for OpenAI-compatible clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

HEADER_PROJECT = "X-Vigil-Project"
HEADER_ENVIRONMENT = "X-Vigil-Environment"
HEADER_WORKFLOW_ID = "X-Vigil-Workflow-Id"
HEADER_REQUEST_ID = "X-Vigil-Request-Id"


@dataclass(frozen=True, slots=True)
class CorrelationContext:
    """Attribution metadata injected into gateway-bound requests."""

    project: str
    environment: str
    workflow_id: str
    request_id: str | None = None

    def __post_init__(self) -> None:
        if not self.project.strip():
            msg = "project must be non-empty"
            raise ValueError(msg)
        if not self.environment.strip():
            msg = "environment must be non-empty"
            raise ValueError(msg)
        if not self.workflow_id.strip():
            msg = "workflow_id must be non-empty"
            raise ValueError(msg)


def correlation_headers(context: CorrelationContext) -> dict[str, str]:
    """Return HTTP headers for OpenAI-compatible clients pointing at Vigil."""
    headers = {
        HEADER_PROJECT: context.project,
        HEADER_ENVIRONMENT: context.environment,
        HEADER_WORKFLOW_ID: context.workflow_id,
    }
    if context.request_id:
        headers[HEADER_REQUEST_ID] = context.request_id
    return headers


def merge_openai_client_kwargs(
    context: CorrelationContext,
    *,
    base_url: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build kwargs suitable for OpenAI-compatible client constructors.

    Without correlation headers Vigil can enforce per-request limits but cannot
    honestly claim precise per-workflow spend or loop detection.
    """
    if not base_url.strip():
        msg = "base_url must be non-empty"
        raise ValueError(msg)
    payload: dict[str, Any] = {
        "base_url": base_url.rstrip("/"),
        "default_headers": correlation_headers(context),
    }
    if extra:
        merged_headers = dict(extra.get("default_headers") or {})
        merged_headers.update(payload["default_headers"])
        payload = {**extra, **payload, "default_headers": merged_headers}
    return payload
