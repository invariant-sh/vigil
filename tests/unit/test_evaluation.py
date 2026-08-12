"""Unit tests for the pure evaluation engine."""

from __future__ import annotations

from vigil.domain.evaluation import WorkflowState, evaluate
from vigil.domain.events import RequestEvent
from vigil.domain.money import MicroUsd
from vigil.domain.policy import (
    AuditConfig,
    Budgets,
    CircuitBreakerControl,
    Control,
    ModelPolicy,
    Policy,
    Scope,
    ToolContentGuardControl,
)

_DEFAULT_COST = MicroUsd(micro_usd=10_000)


def _default_controls() -> tuple[Control, ...]:
    return (
        CircuitBreakerControl(condition="repeated_equivalent_request", max_occurrences=2),
        ToolContentGuardControl(mode="block", patterns=("instruction_override",)),
    )


def _policy() -> Policy:
    return Policy(
        version=1,
        scope=Scope(project="support-agent", environment="production"),
        budgets=Budgets(
            max_llm_calls_per_workflow=3,
            max_cost_usd_per_workflow=MicroUsd.from_usd(1.0),
        ),
        models=ModelPolicy(
            allow=("gpt-4o-mini", "gpt-4.1-mini"),
            route_after_cost_usd=MicroUsd.from_usd(0.2),
            fallback_model="gpt-4o-mini",
        ),
        controls=_default_controls(),
        audit=AuditConfig(emit=True),
        content_hash="abc",
    )


def _event(
    *,
    model: str = "gpt-4.1-mini",
    request_fingerprint: str = "fp1",
    estimated_cost: MicroUsd | None = None,
    tool_content_flags: tuple[str, ...] = (),
) -> RequestEvent:
    return RequestEvent(
        request_id="r1",
        workflow_id="wf1",
        project="support-agent",
        environment="production",
        model=model,
        request_fingerprint=request_fingerprint,
        estimated_cost=_DEFAULT_COST if estimated_cost is None else estimated_cost,
        tool_content_flags=tool_content_flags,
    )


def test_allows_compliant_request() -> None:
    decision = evaluate(_policy(), WorkflowState(workflow_id="wf1"), _event())
    assert decision.action == "allow"
    assert decision.reason_code == "allowed"


def test_blocks_disallowed_model() -> None:
    decision = evaluate(_policy(), WorkflowState(workflow_id="wf1"), _event(model="gpt-4o"))
    assert decision.action == "block"
    assert decision.reason_code == "model_not_allowed"


def test_blocks_call_cap() -> None:
    state = WorkflowState(workflow_id="wf1", call_count=3)
    decision = evaluate(_policy(), state, _event())
    assert decision.reason_code == "call_cap_exceeded"


def test_blocks_cost_cap() -> None:
    state = WorkflowState(workflow_id="wf1", cost=MicroUsd.from_usd(0.99))
    decision = evaluate(
        _policy(),
        state,
        _event(estimated_cost=MicroUsd.from_usd(0.02)),
    )
    assert decision.reason_code == "cost_cap_exceeded"


def test_routes_after_cost_threshold() -> None:
    state = WorkflowState(workflow_id="wf1", cost=MicroUsd.from_usd(0.25))
    decision = evaluate(_policy(), state, _event(model="gpt-4.1-mini"))
    assert decision.action == "route"
    assert decision.effective_model == "gpt-4o-mini"
    assert decision.reason_code == "routed_to_fallback"


def test_circuit_breaker_trips_on_repeat() -> None:
    state = WorkflowState(
        workflow_id="wf1",
        fingerprint_counts=(("fp1", 2),),
    )
    decision = evaluate(_policy(), state, _event(request_fingerprint="fp1"))
    assert decision.reason_code == "circuit_breaker_tripped"


def test_tool_content_guard_blocks() -> None:
    decision = evaluate(
        _policy(),
        WorkflowState(workflow_id="wf1"),
        _event(tool_content_flags=("instruction_override",)),
    )
    assert decision.reason_code == "tool_content_blocked"


def test_workflow_state_increments() -> None:
    state = WorkflowState(workflow_id="wf1")
    next_state = state.with_request(_event(), billed=True)
    assert next_state.call_count == 1
    assert next_state.cost.micro_usd == 10_000
    assert next_state.count_for("fp1") == 1
