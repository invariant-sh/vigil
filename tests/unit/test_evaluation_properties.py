"""Property tests for evaluation invariants."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from vigil.domain.evaluation import WorkflowState, evaluate
from vigil.domain.events import RequestEvent
from vigil.domain.money import MicroUsd
from vigil.domain.policy import (
    AuditConfig,
    Budgets,
    ModelPolicy,
    Policy,
    Scope,
)


def _base_policy(*, allow: tuple[str, ...], call_cap: int | None) -> Policy:
    return Policy(
        version=1,
        scope=Scope(project="p", environment="e"),
        budgets=Budgets(max_llm_calls_per_workflow=call_cap),
        models=ModelPolicy(allow=allow),
        controls=(),
        audit=AuditConfig(emit=False),
    )


@given(
    model=st.sampled_from(["gpt-a", "gpt-b", "gpt-c"]),
    call_count=st.integers(min_value=0, max_value=5),
)
def test_disallowed_model_always_blocks(model: str, call_count: int) -> None:
    policy = _base_policy(allow=("gpt-a",), call_cap=10)
    event = RequestEvent(
        request_id="r",
        workflow_id="w",
        project="p",
        environment="e",
        model=model,
        request_fingerprint="fp",
        estimated_cost=MicroUsd.zero(),
    )
    decision = evaluate(policy, WorkflowState(workflow_id="w", call_count=call_count), event)
    if model == "gpt-a":
        assert decision.allowed
    else:
        assert decision.action == "block"
        assert decision.reason_code == "model_not_allowed"


@given(prior_calls=st.integers(min_value=0, max_value=20))
def test_call_cap_is_monotonic(prior_calls: int) -> None:
    policy = _base_policy(allow=("gpt-a",), call_cap=5)
    event = RequestEvent(
        request_id="r",
        workflow_id="w",
        project="p",
        environment="e",
        model="gpt-a",
        request_fingerprint="fp",
    )
    decision = evaluate(policy, WorkflowState(workflow_id="w", call_count=prior_calls), event)
    if prior_calls + 1 > 5:
        assert decision.reason_code == "call_cap_exceeded"
    else:
        assert decision.allowed
