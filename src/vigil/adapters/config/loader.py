"""YAML policy loading and validation."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from vigil.domain.errors import PolicyValidationError
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

SUPPORTED_VERSION = 1
ALLOWED_CONTROL_TYPES = {"circuit_breaker", "tool_content_guard"}
ALLOWED_GUARD_MODES = {"block", "redact", "quarantine", "escalate"}
ALLOWED_CIRCUIT_CONDITIONS = {"repeated_equivalent_request"}
ALLOWED_STATUS = {"suggested", "approved", "deployed", "rejected"}


def compute_policy_hash(raw: bytes) -> str:
    """Return a stable content hash for policy provenance."""
    return hashlib.sha256(raw).hexdigest()


class YamlPolicyLoader:
    """Load and validate `vigil.yaml` documents."""

    def load(self, path: Path) -> Policy:
        """Parse a policy file into a typed Policy."""
        try:
            raw = path.read_bytes()
        except OSError as error:
            msg = f"unable to read policy file `{path}`: {error}"
            raise PolicyValidationError(msg) from error
        try:
            document = yaml.safe_load(raw)
        except yaml.YAMLError as error:
            msg = f"invalid YAML in `{path}`: {error}"
            raise PolicyValidationError(msg) from error
        if not isinstance(document, dict):
            msg = "policy document must be a mapping"
            raise PolicyValidationError(msg)
        return self._parse(
            document,
            source_path=str(path.resolve()),
            content_hash=compute_policy_hash(raw),
        )

    def _parse(self, document: dict[str, Any], *, source_path: str, content_hash: str) -> Policy:
        unknown = {
            str(key)
            for key in document
            if key
            not in {
                "version",
                "scope",
                "budgets",
                "models",
                "controls",
                "audit",
                "status",
                "owner",
            }
        }
        if unknown:
            msg = f"unknown top-level fields: {sorted(unknown)}"
            raise PolicyValidationError(msg)

        version = document.get("version")
        if version != SUPPORTED_VERSION:
            msg = (
                f"unsupported policy version `{version}`; "
                f"Vigil currently accepts version {SUPPORTED_VERSION}"
            )
            raise PolicyValidationError(msg)

        scope = self._parse_scope(document.get("scope"))
        budgets = self._parse_budgets(document.get("budgets") or {})
        models = self._parse_models(document.get("models"))
        controls = self._parse_controls(document.get("controls") or [])
        audit = self._parse_audit(document.get("audit") or {})
        status = document.get("status", "approved")
        if status not in ALLOWED_STATUS:
            msg = f"status must be one of {sorted(ALLOWED_STATUS)}"
            raise PolicyValidationError(msg)
        owner = document.get("owner")
        if owner is not None and not isinstance(owner, str):
            msg = "owner must be a string when provided"
            raise PolicyValidationError(msg)

        try:
            return Policy(
                version=int(version),
                scope=scope,
                budgets=budgets,
                models=models,
                controls=controls,
                audit=audit,
                source_path=source_path,
                content_hash=content_hash,
                status=status,  # type: ignore[arg-type]
                owner=owner,
            )
        except ValueError as error:
            raise PolicyValidationError(str(error)) from error

    def _parse_scope(self, raw: Any) -> Scope:
        if not isinstance(raw, dict):
            msg = "scope must be a mapping"
            raise PolicyValidationError(msg)
        unknown = {str(key) for key in raw if key not in {"project", "environment"}}
        if unknown:
            msg = f"scope unknown fields: {sorted(unknown)}"
            raise PolicyValidationError(msg)
        try:
            return Scope(
                project=_require_str(raw, "project", prefix="scope"),
                environment=_require_str(raw, "environment", prefix="scope"),
            )
        except ValueError as error:
            raise PolicyValidationError(str(error)) from error

    def _parse_budgets(self, raw: Any) -> Budgets:
        if not isinstance(raw, dict):
            msg = "budgets must be a mapping"
            raise PolicyValidationError(msg)
        unknown = {
            str(key)
            for key in raw
            if key not in {"max_llm_calls_per_workflow", "max_cost_usd_per_workflow"}
        }
        if unknown:
            msg = f"budgets unknown fields: {sorted(unknown)}"
            raise PolicyValidationError(msg)
        calls = raw.get("max_llm_calls_per_workflow")
        if calls is not None and (isinstance(calls, bool) or not isinstance(calls, int)):
            msg = "budgets.max_llm_calls_per_workflow must be an integer"
            raise PolicyValidationError(msg)
        cost = raw.get("max_cost_usd_per_workflow")
        cost_money = (
            None if cost is None else _parse_usd(cost, prefix="budgets.max_cost_usd_per_workflow")
        )
        try:
            return Budgets(max_llm_calls_per_workflow=calls, max_cost_usd_per_workflow=cost_money)
        except ValueError as error:
            raise PolicyValidationError(str(error)) from error

    def _parse_models(self, raw: Any) -> ModelPolicy:
        if not isinstance(raw, dict):
            msg = "models must be a mapping"
            raise PolicyValidationError(msg)
        unknown = {
            str(key)
            for key in raw
            if key not in {"allow", "route_after_cost_usd", "fallback_model"}
        }
        if unknown:
            msg = f"models unknown fields: {sorted(unknown)}"
            raise PolicyValidationError(msg)
        allow_raw = raw.get("allow")
        if not isinstance(allow_raw, list) or not allow_raw:
            msg = "models.allow must be a non-empty list"
            raise PolicyValidationError(msg)
        allow: list[str] = []
        for index, item in enumerate(allow_raw):
            if not isinstance(item, str) or not item.strip():
                msg = f"models.allow[{index}] must be a non-empty string"
                raise PolicyValidationError(msg)
            allow.append(item)
        route = raw.get("route_after_cost_usd")
        route_money = (
            None if route is None else _parse_usd(route, prefix="models.route_after_cost_usd")
        )
        fallback = raw.get("fallback_model")
        if fallback is not None and (not isinstance(fallback, str) or not fallback.strip()):
            msg = "models.fallback_model must be a non-empty string"
            raise PolicyValidationError(msg)
        try:
            return ModelPolicy(
                allow=tuple(allow),
                route_after_cost_usd=route_money,
                fallback_model=fallback,
            )
        except ValueError as error:
            raise PolicyValidationError(str(error)) from error

    def _parse_controls(self, raw: Any) -> tuple[Control, ...]:
        if not isinstance(raw, list):
            msg = "controls must be a list"
            raise PolicyValidationError(msg)
        return tuple(self._parse_control(item, index) for index, item in enumerate(raw))

    def _parse_control(self, raw: Any, index: int) -> Control:
        if not isinstance(raw, dict):
            msg = f"controls[{index}] must be a mapping"
            raise PolicyValidationError(msg)
        control_type = raw.get("type")
        if control_type not in ALLOWED_CONTROL_TYPES:
            msg = f"controls[{index}].type must be one of {sorted(ALLOWED_CONTROL_TYPES)}"
            raise PolicyValidationError(msg)
        if control_type == "circuit_breaker":
            return self._parse_circuit_breaker(raw, index)
        return self._parse_tool_guard(raw, index)

    def _parse_circuit_breaker(self, raw: dict[str, Any], index: int) -> CircuitBreakerControl:
        unknown = {str(key) for key in raw if key not in {"type", "condition", "max_occurrences"}}
        if unknown:
            msg = f"controls[{index}] unknown fields: {sorted(unknown)}"
            raise PolicyValidationError(msg)
        condition = raw.get("condition")
        if condition not in ALLOWED_CIRCUIT_CONDITIONS:
            msg = f"controls[{index}].condition must be one of {sorted(ALLOWED_CIRCUIT_CONDITIONS)}"
            raise PolicyValidationError(msg)
        max_occurrences = raw.get("max_occurrences")
        if isinstance(max_occurrences, bool) or not isinstance(max_occurrences, int):
            msg = f"controls[{index}].max_occurrences must be an integer"
            raise PolicyValidationError(msg)
        try:
            return CircuitBreakerControl(
                condition=condition,  # type: ignore[arg-type]
                max_occurrences=max_occurrences,
            )
        except ValueError as error:
            raise PolicyValidationError(str(error)) from error

    def _parse_tool_guard(self, raw: dict[str, Any], index: int) -> ToolContentGuardControl:
        unknown = {str(key) for key in raw if key not in {"type", "mode", "patterns"}}
        if unknown:
            msg = f"controls[{index}] unknown fields: {sorted(unknown)}"
            raise PolicyValidationError(msg)
        mode = raw.get("mode")
        if mode not in ALLOWED_GUARD_MODES:
            msg = f"controls[{index}].mode must be one of {sorted(ALLOWED_GUARD_MODES)}"
            raise PolicyValidationError(msg)
        patterns_raw = raw.get("patterns")
        if not isinstance(patterns_raw, list) or not patterns_raw:
            msg = f"controls[{index}].patterns must be a non-empty list"
            raise PolicyValidationError(msg)
        patterns: list[str] = []
        for pattern_index, item in enumerate(patterns_raw):
            if not isinstance(item, str) or not item.strip():
                msg = f"controls[{index}].patterns[{pattern_index}] must be a non-empty string"
                raise PolicyValidationError(msg)
            patterns.append(item)
        try:
            return ToolContentGuardControl(mode=mode, patterns=tuple(patterns))  # type: ignore[arg-type]
        except ValueError as error:
            raise PolicyValidationError(str(error)) from error

    def _parse_audit(self, raw: Any) -> AuditConfig:
        if not isinstance(raw, dict):
            msg = "audit must be a mapping"
            raise PolicyValidationError(msg)
        unknown = {str(key) for key in raw if key not in {"emit"}}
        if unknown:
            msg = f"audit unknown fields: {sorted(unknown)}"
            raise PolicyValidationError(msg)
        emit = raw.get("emit", True)
        if not isinstance(emit, bool):
            msg = "audit.emit must be a boolean"
            raise PolicyValidationError(msg)
        return AuditConfig(emit=emit)


def _require_str(raw: dict[str, Any], key: str, *, prefix: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"{prefix}.{key} must be a non-empty string"
        raise PolicyValidationError(msg)
    return value


def _parse_usd(value: Any, *, prefix: str) -> MicroUsd:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        msg = f"{prefix} must be a number"
        raise PolicyValidationError(msg)
    if value <= 0:
        msg = f"{prefix} must be > 0"
        raise PolicyValidationError(msg)
    try:
        return MicroUsd.from_usd(float(value))
    except ValueError as error:
        raise PolicyValidationError(str(error)) from error
