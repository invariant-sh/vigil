"""Unit tests for fingerprints and correlation helpers."""

from __future__ import annotations

import pytest

from vigil.correlation import (
    HEADER_PROJECT,
    HEADER_WORKFLOW_ID,
    CorrelationContext,
    correlation_headers,
    merge_openai_client_kwargs,
)
from vigil.domain.fingerprints import request_fingerprint


def test_fingerprint_stable_for_equivalent_messages() -> None:
    a = request_fingerprint(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": " hello "}],
    )
    b = request_fingerprint(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hello"}],
    )
    assert a == b


def test_fingerprint_changes_with_model() -> None:
    a = request_fingerprint(model="a", messages=[{"role": "user", "content": "x"}])
    b = request_fingerprint(model="b", messages=[{"role": "user", "content": "x"}])
    assert a != b


def test_correlation_headers() -> None:
    headers = correlation_headers(
        CorrelationContext(project="p", environment="prod", workflow_id="wf", request_id="r1")
    )
    assert headers[HEADER_PROJECT] == "p"
    assert headers[HEADER_WORKFLOW_ID] == "wf"
    assert headers["X-Vigil-Request-Id"] == "r1"


def test_merge_openai_client_kwargs() -> None:
    kwargs = merge_openai_client_kwargs(
        CorrelationContext(project="p", environment="prod", workflow_id="wf"),
        base_url="http://localhost:8080/v1/",
        extra={"api_key": "sk-test", "default_headers": {"X-Custom": "1"}},
    )
    assert kwargs["base_url"] == "http://localhost:8080/v1"
    assert kwargs["api_key"] == "sk-test"
    assert kwargs["default_headers"]["X-Custom"] == "1"
    assert kwargs["default_headers"][HEADER_PROJECT] == "p"


def test_correlation_rejects_empty_project() -> None:
    with pytest.raises(ValueError, match="project"):
        CorrelationContext(project="", environment="e", workflow_id="w")
