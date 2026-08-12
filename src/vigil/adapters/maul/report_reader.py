"""Maul reliability_report.json reader (schema_version 0.1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vigil.domain.errors import MaulReportError, UnsupportedReportVersionError
from vigil.domain.maul_report import MaulReport, MaulRequestFinding

SUPPORTED_SCHEMA_VERSIONS = frozenset({"0.1"})


class JsonMaulReportReader:
    """Parse and validate Maul reliability reports."""

    def read(self, path: Path) -> MaulReport:
        """Load a Maul report from disk."""
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as error:
            msg = f"unable to read Maul report `{path}`: {error}"
            raise MaulReportError(msg) from error
        try:
            document = json.loads(raw)
        except json.JSONDecodeError as error:
            msg = f"invalid JSON in Maul report `{path}`: {error}"
            raise MaulReportError(msg) from error
        if not isinstance(document, dict):
            msg = "Maul report must be a JSON object"
            raise MaulReportError(msg)
        return self._parse(document, source_path=str(path.resolve()))

    def _parse(self, document: dict[str, Any], *, source_path: str) -> MaulReport:
        schema_version = document.get("schema_version")
        if not isinstance(schema_version, str):
            msg = "Maul report missing string schema_version"
            raise MaulReportError(msg)
        if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            msg = (
                f"unsupported Maul report schema_version `{schema_version}`; "
                f"supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
            )
            raise UnsupportedReportVersionError(msg)

        summary = document.get("summary") or {}
        if not isinstance(summary, dict):
            msg = "Maul report summary must be an object"
            raise MaulReportError(msg)
        budget_rejections = summary.get("budget_rejections", 0)
        if isinstance(budget_rejections, bool) or not isinstance(budget_rejections, int):
            msg = "summary.budget_rejections must be an integer"
            raise MaulReportError(msg)

        budget_snapshot = document.get("budget_snapshot") or {}
        if budget_snapshot is not None and not isinstance(budget_snapshot, dict):
            msg = "budget_snapshot must be an object when present"
            raise MaulReportError(msg)
        calls_limit = None
        cost_limit_micro = None
        if isinstance(budget_snapshot, dict):
            calls_limit = _optional_int(budget_snapshot.get("calls_limit"))
            cost_limit = budget_snapshot.get("cost_limit_usd")
            cost_limit_micro = _micro_from_money(cost_limit)

        observed = summary.get("observed_cost_usd")
        observed_micro = _micro_from_money(observed)

        seed = _optional_int(document.get("seed"))

        requests_raw = document.get("requests") or []
        if not isinstance(requests_raw, list):
            msg = "requests must be a list"
            raise MaulReportError(msg)
        findings = tuple(_parse_finding(item, index) for index, item in enumerate(requests_raw))

        return MaulReport(
            schema_version=schema_version,
            source_path=source_path,
            seed=seed,
            budget_rejections=budget_rejections,
            request_findings=findings,
            observed_cost_micro_usd=observed_micro,
            calls_limit=calls_limit,
            cost_limit_micro_usd=cost_limit_micro,
        )


def _parse_finding(raw: Any, index: int) -> MaulRequestFinding:
    if not isinstance(raw, dict):
        msg = f"requests[{index}] must be an object"
        raise MaulReportError(msg)
    fault = raw.get("fault_injected")
    if fault is not None and not isinstance(fault, str):
        msg = f"requests[{index}].fault_injected must be a string when present"
        raise MaulReportError(msg)
    budget_decision = raw.get("budget_decision")
    if budget_decision is not None and not isinstance(budget_decision, str):
        msg = f"requests[{index}].budget_decision must be a string when present"
        raise MaulReportError(msg)
    model = raw.get("model")
    if model is not None and not isinstance(model, str):
        msg = f"requests[{index}].model must be a string when present"
        raise MaulReportError(msg)
    return MaulRequestFinding(
        index=index,
        fault_injected=fault,
        budget_decision=budget_decision,
        model=model,
    )


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _micro_from_money(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, dict):
        micro = value.get("micro_usd")
        if isinstance(micro, bool) or not isinstance(micro, int):
            return None
        return micro
    return None
