"""Pure policy evaluation engine.

Stateless functions: `(policy, workflow_state, request) -> Decision`.
The application layer folds workflow state immutably after each decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from vigil.domain.decision import Decision
from vigil.domain.events import RequestEvent
from vigil.domain.money import MicroUsd
from vigil.domain.policy import CircuitBreakerControl, Policy, ToolContentGuardControl

_ZERO_COST = MicroUsd.zero()


@dataclass(frozen=True, slots=True)
class WorkflowState:
    """Accumulated per-workflow counters used by budget and breaker checks."""

    workflow_id: str
    call_count: int = 0
    cost: MicroUsd = field(default_factory=lambda: _ZERO_COST)
    fingerprint_counts: tuple[tuple[str, int], ...] = ()

    def count_for(self, fingerprint: str) -> int:
        """Return how many times an equivalent request has been seen."""
        for key, count in self.fingerprint_counts:
            if key == fingerprint:
                return count
        return 0

    def with_request(self, event: RequestEvent, *, billed: bool) -> WorkflowState:
        """Return a new state after admitting (or observing) a request."""
        next_count = self.call_count + 1 if billed else self.call_count
        next_cost = self.cost
        if billed and event.estimated_cost is not None:
            next_cost = self.cost + event.estimated_cost
        next_fp = _increment_fingerprint(self.fingerprint_counts, event.request_fingerprint)
        return replace(
            self,
            call_count=next_count,
            cost=next_cost,
            fingerprint_counts=next_fp,
        )


def evaluate(policy: Policy, state: WorkflowState, event: RequestEvent) -> Decision:
    """Evaluate one request against policy. Order: model → budgets → guards → breaker → route."""
    model_decision = _check_model_allowlist(policy, event)
    if model_decision is not None:
        return model_decision

    budget_decision = _check_budgets(policy, state, event)
    if budget_decision is not None:
        return budget_decision

    guard_decision = _check_tool_guards(policy, event)
    if guard_decision is not None:
        return guard_decision

    breaker_decision = _check_circuit_breaker(policy, state, event)
    if breaker_decision is not None:
        return breaker_decision

    route_decision = _check_routing(policy, state, event)
    if route_decision is not None:
        return route_decision

    return Decision(
        action="allow",
        reason_code="allowed",
        message="request permitted by policy",
        requested_model=event.model,
        effective_model=event.model,
    )


def _check_model_allowlist(policy: Policy, event: RequestEvent) -> Decision | None:
    if event.model in policy.models.allow:
        return None
    return Decision(
        action="block",
        reason_code="model_not_allowed",
        message=f"model `{event.model}` is not in the allowlist",
        requested_model=event.model,
        effective_model=None,
    )


def _check_budgets(policy: Policy, state: WorkflowState, event: RequestEvent) -> Decision | None:
    calls_limit = policy.budgets.max_llm_calls_per_workflow
    if calls_limit is not None and state.call_count + 1 > calls_limit:
        return Decision(
            action="block",
            reason_code="call_cap_exceeded",
            message=(
                f"workflow `{state.workflow_id}` would exceed max_llm_calls_per_workflow "
                f"({calls_limit})"
            ),
            requested_model=event.model,
            effective_model=None,
        )

    cost_limit = policy.budgets.max_cost_usd_per_workflow
    if cost_limit is not None and event.estimated_cost is not None:
        projected = state.cost + event.estimated_cost
        if projected > cost_limit:
            return Decision(
                action="block",
                reason_code="cost_cap_exceeded",
                message=(
                    f"workflow `{state.workflow_id}` would exceed max_cost_usd_per_workflow "
                    f"({cost_limit.display})"
                ),
                requested_model=event.model,
                effective_model=None,
            )
    return None


def _check_tool_guards(policy: Policy, event: RequestEvent) -> Decision | None:
    if not event.tool_content_flags:
        return None
    flags = set(event.tool_content_flags)
    for control in policy.controls:
        if not isinstance(control, ToolContentGuardControl):
            continue
        overlap = flags.intersection(control.patterns)
        if not overlap:
            continue
        if control.mode in {"block", "quarantine"}:
            return Decision(
                action="block",
                reason_code="tool_content_blocked",
                message=(f"tool content matched patterns {sorted(overlap)} (mode={control.mode})"),
                requested_model=event.model,
                effective_model=None,
            )
    return None


def _check_circuit_breaker(
    policy: Policy, state: WorkflowState, event: RequestEvent
) -> Decision | None:
    for control in policy.controls:
        if not isinstance(control, CircuitBreakerControl):
            continue
        if control.condition != "repeated_equivalent_request":
            continue
        seen = state.count_for(event.request_fingerprint)
        # seen is prior count; this request would be occurrence seen+1
        if seen + 1 > control.max_occurrences:
            return Decision(
                action="block",
                reason_code="circuit_breaker_tripped",
                message=(
                    f"repeated_equivalent_request exceeded max_occurrences "
                    f"({control.max_occurrences})"
                ),
                requested_model=event.model,
                effective_model=None,
            )
    return None


def _check_routing(policy: Policy, state: WorkflowState, event: RequestEvent) -> Decision | None:
    threshold = policy.models.route_after_cost_usd
    fallback = policy.models.fallback_model
    if threshold is None or fallback is None:
        return None
    if state.cost < threshold:
        return None
    if event.model == fallback:
        return None
    if fallback not in policy.models.allow:
        return Decision(
            action="block",
            reason_code="no_compliant_fallback",
            message="routing threshold reached but fallback model is not allowlisted",
            requested_model=event.model,
            effective_model=None,
        )
    return Decision(
        action="route",
        reason_code="routed_to_fallback",
        message=(
            f"workflow cost {state.cost.display} exceeded route_after_cost_usd "
            f"{threshold.display}; routing to `{fallback}`"
        ),
        requested_model=event.model,
        effective_model=fallback,
    )


def _increment_fingerprint(
    counts: tuple[tuple[str, int], ...], fingerprint: str
) -> tuple[tuple[str, int], ...]:
    updated: list[tuple[str, int]] = []
    found = False
    for key, count in counts:
        if key == fingerprint:
            updated.append((key, count + 1))
            found = True
        else:
            updated.append((key, count))
    if not found:
        updated.append((fingerprint, 1))
    return tuple(updated)
