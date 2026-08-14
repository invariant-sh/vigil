"""Language-neutral policy and fingerprint conformance vectors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from vigil.adapters.config.loader import YamlPolicyLoader
from vigil.domain.evaluation import WorkflowState, evaluate
from vigil.domain.events import RequestEvent
from vigil.domain.fingerprints import request_fingerprint
from vigil.domain.money import MicroUsd

_ROOT = Path(__file__).resolve().parents[2]
_VECTORS = _ROOT / "contracts" / "conformance" / "v1"


def test_example_policy_matches_machine_schema() -> None:
    schema = _load_json(_ROOT / "contracts" / "policy.v1.schema.json")
    document = yaml.safe_load((_ROOT / "contracts" / "policy.v1.example.yaml").read_text())
    jsonschema.validate(document, schema)


def test_policy_evaluation_vectors_match_reference_engine() -> None:
    payload = _load_json(_VECTORS / "policy_evaluation.json")
    for case in payload["cases"]:
        policy = _policy(case["policy"])
        state = _state(case["state"])
        event = _event(case["event"])
        decision = evaluate(policy, state, event)

        assert decision.action == case["expected"]["action"], case["name"]
        assert decision.reason_code == case["expected"]["reason_code"], case["name"]
        assert decision.effective_model == case["expected"]["effective_model"], case["name"]
        assert decision.allowed is case["expected"]["billed"], case["name"]


def test_fingerprint_vectors_match_reference_algorithm() -> None:
    payload = _load_json(_VECTORS / "request_fingerprints.json")
    for case in payload["cases"]:
        fingerprint = request_fingerprint(model=case["model"], messages=case["messages"])
        assert fingerprint == case["fingerprint"], case["name"]


def _policy(document: dict[str, Any]) -> Any:
    return YamlPolicyLoader()._parse(
        document,
        source_path="<conformance>",
        content_hash="0" * 64,
    )


def _state(raw: dict[str, Any]) -> WorkflowState:
    return WorkflowState(
        workflow_id=raw["workflow_id"],
        call_count=raw["call_count"],
        cost=MicroUsd(micro_usd=raw["cost_micro_usd"]),
        fingerprint_counts=tuple(
            (fingerprint, count) for fingerprint, count in raw["fingerprint_counts"]
        ),
    )


def _event(raw: dict[str, Any]) -> RequestEvent:
    cost = raw["estimated_cost_micro_usd"]
    return RequestEvent(
        request_id=raw["request_id"],
        workflow_id=raw["workflow_id"],
        project=raw["project"],
        environment=raw["environment"],
        model=raw["model"],
        request_fingerprint=raw["request_fingerprint"],
        estimated_cost=None if cost is None else MicroUsd(micro_usd=cost),
        tool_content_flags=tuple(raw["tool_content_flags"]),
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
