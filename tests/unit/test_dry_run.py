"""Tests for DryRunService."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.support.fakes import (
    FakeClock,
    FakeIds,
    InMemoryAuditSink,
    InMemoryDecisionSink,
    StaticEventSource,
    StaticPolicyLoader,
)

from vigil.application.dry_run import DryRunService
from vigil.domain.errors import DryRunError
from vigil.domain.events import RequestEvent
from vigil.domain.money import MicroUsd
from vigil.domain.policy import (
    AuditConfig,
    Budgets,
    CircuitBreakerControl,
    ModelPolicy,
    Policy,
    Scope,
    ToolContentGuardControl,
)


def _policy() -> Policy:
    return Policy(
        version=1,
        scope=Scope(project="support-agent", environment="production"),
        budgets=Budgets(max_llm_calls_per_workflow=2),
        models=ModelPolicy(allow=("gpt-4o-mini",)),
        controls=(
            CircuitBreakerControl(condition="repeated_equivalent_request", max_occurrences=2),
            ToolContentGuardControl(mode="block", patterns=("instruction_override",)),
        ),
        audit=AuditConfig(emit=True),
        content_hash="hash",
    )


def test_dry_run_folds_workflow_state() -> None:
    events = (
        RequestEvent(
            request_id="1",
            workflow_id="wf",
            project="support-agent",
            environment="production",
            model="gpt-4o-mini",
            request_fingerprint="a",
            estimated_cost=MicroUsd(micro_usd=100),
        ),
        RequestEvent(
            request_id="2",
            workflow_id="wf",
            project="support-agent",
            environment="production",
            model="gpt-4o-mini",
            request_fingerprint="b",
            estimated_cost=MicroUsd(micro_usd=100),
        ),
        RequestEvent(
            request_id="3",
            workflow_id="wf",
            project="support-agent",
            environment="production",
            model="gpt-4o-mini",
            request_fingerprint="c",
            estimated_cost=MicroUsd(micro_usd=100),
        ),
    )
    decisions = InMemoryDecisionSink()
    audit = InMemoryAuditSink()
    service = DryRunService(
        policy_loader=StaticPolicyLoader(_policy()),
        event_source=StaticEventSource(events),
        decision_sink=decisions,
        audit_sink=audit,
        clock=FakeClock(),
        ids=FakeIds(),
    )
    result = service.execute(
        policy_path=Path("p.yaml"),
        events_path=Path("e.jsonl"),
        decisions_path=Path("d.jsonl"),
        audit_path=Path("a.jsonl"),
    )
    assert result.allowed_count == 2
    assert result.blocked_count == 1
    assert result.records[-1].reason_code == "call_cap_exceeded"
    assert audit.path is not None


def test_dry_run_rejects_scope_mismatch() -> None:
    events = (
        RequestEvent(
            request_id="1",
            workflow_id="wf",
            project="other",
            environment="production",
            model="gpt-4o-mini",
            request_fingerprint="a",
        ),
    )
    service = DryRunService(
        policy_loader=StaticPolicyLoader(_policy()),
        event_source=StaticEventSource(events),
        decision_sink=InMemoryDecisionSink(),
        audit_sink=InMemoryAuditSink(),
        clock=FakeClock(),
        ids=FakeIds(),
    )
    with pytest.raises(DryRunError, match="scope"):
        service.execute(
            policy_path=Path("p.yaml"),
            events_path=Path("e.jsonl"),
            decisions_path=Path("d.jsonl"),
        )
