"""Correlation metadata helpers for OpenAI-compatible clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

HEADER_PROJECT = "X-Vigil-Project"
HEADER_ENVIRONMENT = "X-Vigil-Environment"
HEADER_WORKFLOW_ID = "X-Vigil-Workflow-Id"
HEADER_REQUEST_ID = "X-Vigil-Request-Id"
HEADER_ORGANIZATION_ID = "X-Vigil-Organization-Id"
HEADER_SDK_VERSION = "X-Vigil-Sdk-Version"
HEADER_APPLICATION_KEY = "X-Vigil-Key"
SDK_PROTOCOL_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class CorrelationContext:
    """Attribution metadata injected into gateway-bound requests."""

    project: str
    environment: str
    workflow_id: str
    request_id: str | None = None
    organization_id: str | None = None
    sdk_version: str = SDK_PROTOCOL_VERSION

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
        if self.organization_id is not None and not self.organization_id.strip():
            msg = "organization_id must be non-empty when provided"
            raise ValueError(msg)
        if not self.sdk_version.strip():
            msg = "sdk_version must be non-empty"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class GatewayConfig:
    """Connection data for a managed or customer-VPC Vigil gateway.

    The application key authenticates to Vigil. Provider credentials remain
    caller-owned and may be passed to the OpenAI client separately.
    """

    base_url: str
    application_key: str

    def __post_init__(self) -> None:
        if not self.base_url.strip():
            msg = "gateway base_url must be non-empty"
            raise ValueError(msg)
        if not self.application_key.strip():
            msg = "gateway application_key must be non-empty"
            raise ValueError(msg)


def correlation_headers(context: CorrelationContext) -> dict[str, str]:
    """Return HTTP headers for OpenAI-compatible clients pointing at Vigil."""
    headers = {
        HEADER_PROJECT: context.project,
        HEADER_ENVIRONMENT: context.environment,
        HEADER_WORKFLOW_ID: context.workflow_id,
        HEADER_SDK_VERSION: context.sdk_version,
    }
    if context.request_id:
        headers[HEADER_REQUEST_ID] = context.request_id
    if context.organization_id:
        headers[HEADER_ORGANIZATION_ID] = context.organization_id
    return headers


def gateway_headers(context: CorrelationContext, gateway: GatewayConfig) -> dict[str, str]:
    """Return attribution and gateway authentication headers without provider secrets."""
    return {**correlation_headers(context), HEADER_APPLICATION_KEY: gateway.application_key}


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


def merge_gateway_client_kwargs(
    context: CorrelationContext,
    *,
    gateway: GatewayConfig,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build OpenAI-compatible kwargs for a Vigil gateway endpoint.

    This only adds `X-Vigil-Key` and correlation headers. The caller controls
    the provider `api_key`, which OpenAI-compatible clients send as
    `Authorization`; Vigil forwards it in memory and does not persist it.
    """
    payload: dict[str, Any] = {
        "base_url": gateway.base_url.rstrip("/"),
        "default_headers": gateway_headers(context, gateway),
    }
    if extra:
        merged_headers = dict(extra.get("default_headers") or {})
        merged_headers.update(payload["default_headers"])
        payload = {**extra, **payload, "default_headers": merged_headers}
    return payload
