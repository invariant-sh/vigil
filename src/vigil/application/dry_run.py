"""Dry-run policy evaluation against recorded request events."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vigil.domain.decision import DECISION_SCHEMA_VERSION, DecisionRecord
from vigil.domain.errors import DryRunError
from vigil.domain.evaluation import WorkflowState, evaluate
from vigil.domain.events import RequestEvent
from vigil.domain.policy import Policy
from vigil.ports import (
    AuditSink,
    Clock,
    DecisionSink,
    EventSource,
    IdFactory,
    PolicyLoader,
)


@dataclass(frozen=True, slots=True)
class DryRunResult:
    """Outcome of a policy dry-run."""

    policy: Policy
    records: tuple[DecisionRecord, ...]
    decisions_path: Path
    audit_path: Path | None
    allowed_count: int
    blocked_count: int
    routed_count: int


class DryRunService:
    """Fold recorded events through the pure evaluation engine."""

    def __init__(
        self,
        *,
        policy_loader: PolicyLoader,
        event_source: EventSource,
        decision_sink: DecisionSink,
        audit_sink: AuditSink,
        clock: Clock,
        ids: IdFactory,
    ) -> None:
        self._policy_loader = policy_loader
        self._event_source = event_source
        self._decision_sink = decision_sink
        self._audit_sink = audit_sink
        self._clock = clock
        self._ids = ids

    def execute(
        self,
        *,
        policy_path: Path,
        events_path: Path,
        decisions_path: Path,
        audit_path: Path | None = None,
    ) -> DryRunResult:
        """Evaluate events and persist decision + optional audit artifacts."""
        policy = self._policy_loader.load(policy_path)
        events = self._event_source.load(events_path)
        records = self._evaluate_all(policy, events)
        written_decisions = self._decision_sink.write(decisions_path, records)

        written_audit: Path | None = None
        if policy.audit.emit:
            target = audit_path or decisions_path.with_name("audit.jsonl")
            written_audit = self._audit_sink.write(target, records)

        return DryRunResult(
            policy=policy,
            records=records,
            decisions_path=written_decisions,
            audit_path=written_audit,
            allowed_count=sum(1 for record in records if record.action == "allow"),
            blocked_count=sum(1 for record in records if record.action == "block"),
            routed_count=sum(1 for record in records if record.action == "route"),
        )

    def _evaluate_all(
        self, policy: Policy, events: tuple[RequestEvent, ...]
    ) -> tuple[DecisionRecord, ...]:
        states: dict[str, WorkflowState] = {}
        records: list[DecisionRecord] = []
        for event in events:
            self._assert_scope(policy, event)
            state = states.get(event.workflow_id) or WorkflowState(workflow_id=event.workflow_id)
            decision = evaluate(policy, state, event)
            next_state = state.with_request(event, billed=decision.allowed)
            states[event.workflow_id] = next_state
            records.append(
                DecisionRecord(
                    schema_version=DECISION_SCHEMA_VERSION,
                    decision_id=self._ids.decision_id(),
                    timestamp=self._clock.now_iso(),
                    policy_hash=policy.content_hash,
                    project=policy.scope.project,
                    environment=policy.scope.environment,
                    workflow_id=event.workflow_id,
                    request_id=event.request_id,
                    request_fingerprint=event.request_fingerprint,
                    action=decision.action,
                    reason_code=decision.reason_code,
                    message=decision.message,
                    requested_model=decision.requested_model,
                    effective_model=decision.effective_model,
                    estimated_cost=event.estimated_cost,
                    workflow_call_count=next_state.call_count,
                    workflow_cost=next_state.cost if decision.allowed else state.cost,
                )
            )
        if not records:
            msg = "dry-run produced no decision records"
            raise DryRunError(msg)
        return tuple(records)

    def _assert_scope(self, policy: Policy, event: RequestEvent) -> None:
        if event.project != policy.scope.project or event.environment != policy.scope.environment:
            msg = (
                f"event `{event.request_id}` scope "
                f"({event.project}/{event.environment}) does not match policy "
                f"({policy.scope.project}/{policy.scope.environment})"
            )
            raise DryRunError(msg)
