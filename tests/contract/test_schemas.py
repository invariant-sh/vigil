"""Contract tests for decision and audit schemas."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from vigil.adapters.audit.jsonl_sink import _to_audit_event
from vigil.domain.decision import DECISION_SCHEMA_VERSION, DecisionRecord
from vigil.domain.money import MicroUsd


def _record() -> DecisionRecord:
    return DecisionRecord(
        schema_version=DECISION_SCHEMA_VERSION,
        decision_id="dec-1",
        timestamp="2026-01-01T00:00:00Z",
        policy_hash="abc",
        project="support-agent",
        environment="production",
        workflow_id="wf",
        request_id="r1",
        request_fingerprint="fp",
        action="allow",
        reason_code="allowed",
        message="ok",
        requested_model="gpt-4o-mini",
        effective_model="gpt-4o-mini",
        estimated_cost=MicroUsd(micro_usd=10),
        workflow_call_count=1,
        workflow_cost=MicroUsd(micro_usd=10),
    )


def test_decision_record_matches_schema() -> None:
    schema = json.loads(Path("contracts/decision.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(_record().to_dict(), schema)


def test_audit_event_matches_schema() -> None:
    schema = json.loads(Path("contracts/audit_event.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(_to_audit_event(_record()), schema)


def test_example_policy_loads() -> None:
    from vigil.adapters.config.loader import YamlPolicyLoader

    policy = YamlPolicyLoader().load(Path("contracts/policy.v1.example.yaml"))
    assert policy.version == 1
