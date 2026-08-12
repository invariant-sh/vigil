"""Policy domain models for Vigil schema v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from vigil.domain.money import MicroUsd

ControlType = Literal["circuit_breaker", "tool_content_guard"]
CircuitCondition = Literal["repeated_equivalent_request"]
GuardMode = Literal["block", "redact", "quarantine", "escalate"]
PolicyLifecycleStatus = Literal["suggested", "approved", "deployed", "rejected"]


@dataclass(frozen=True, slots=True)
class Scope:
    """Project and environment attribution for a policy."""

    project: str
    environment: str

    def __post_init__(self) -> None:
        if not self.project.strip():
            msg = "scope.project must be non-empty"
            raise ValueError(msg)
        if not self.environment.strip():
            msg = "scope.environment must be non-empty"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Budgets:
    """Per-workflow spend and call limits."""

    max_llm_calls_per_workflow: int | None = None
    max_cost_usd_per_workflow: MicroUsd | None = None

    def __post_init__(self) -> None:
        if self.max_llm_calls_per_workflow is not None and self.max_llm_calls_per_workflow < 1:
            msg = "budgets.max_llm_calls_per_workflow must be >= 1"
            raise ValueError(msg)
        if (
            self.max_cost_usd_per_workflow is not None
            and self.max_cost_usd_per_workflow.micro_usd < 1
        ):
            msg = "budgets.max_cost_usd_per_workflow must be > 0"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ModelPolicy:
    """Allowlist and optional cost-based routing."""

    allow: tuple[str, ...]
    route_after_cost_usd: MicroUsd | None = None
    fallback_model: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "allow", _normalize_allowlist(self.allow))
        object.__setattr__(self, "fallback_model", _normalize_fallback(self))


def _normalize_allowlist(allow: tuple[str, ...]) -> tuple[str, ...]:
    if not allow:
        msg = "models.allow must contain at least one model"
        raise ValueError(msg)
    normalized = tuple(model.strip() for model in allow)
    if any(not model for model in normalized):
        msg = "models.allow entries must be non-empty"
        raise ValueError(msg)
    return normalized


def _normalize_fallback(policy: ModelPolicy) -> str | None:
    if policy.route_after_cost_usd is not None and policy.fallback_model is None:
        msg = "models.fallback_model is required when route_after_cost_usd is set"
        raise ValueError(msg)
    if policy.fallback_model is None:
        return None
    fallback = policy.fallback_model.strip()
    if not fallback:
        msg = "models.fallback_model must be non-empty"
        raise ValueError(msg)
    if fallback not in policy.allow:
        msg = "models.fallback_model must be present in models.allow"
        raise ValueError(msg)
    return fallback


@dataclass(frozen=True, slots=True)
class CircuitBreakerControl:
    """Break loops of equivalent requests within a workflow."""

    condition: CircuitCondition
    max_occurrences: int
    type: Literal["circuit_breaker"] = "circuit_breaker"

    def __post_init__(self) -> None:
        if self.max_occurrences < 1:
            msg = "circuit_breaker.max_occurrences must be >= 1"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ToolContentGuardControl:
    """Block or quarantine known unsafe tool-result patterns."""

    mode: GuardMode
    patterns: tuple[str, ...]
    type: Literal["tool_content_guard"] = "tool_content_guard"

    def __post_init__(self) -> None:
        if not self.patterns:
            msg = "tool_content_guard.patterns must be non-empty"
            raise ValueError(msg)
        normalized = tuple(pattern.strip() for pattern in self.patterns)
        if any(not pattern for pattern in normalized):
            msg = "tool_content_guard.patterns entries must be non-empty"
            raise ValueError(msg)
        object.__setattr__(self, "patterns", normalized)


Control = CircuitBreakerControl | ToolContentGuardControl


@dataclass(frozen=True, slots=True)
class AuditConfig:
    """Audit emission settings."""

    emit: bool = True


@dataclass(frozen=True, slots=True)
class Policy:
    """Versioned Vigil policy document."""

    version: int
    scope: Scope
    budgets: Budgets
    models: ModelPolicy
    controls: tuple[Control, ...]
    audit: AuditConfig
    source_path: str | None = None
    content_hash: str | None = None
    status: PolicyLifecycleStatus = "approved"
    owner: str | None = None

    def __post_init__(self) -> None:
        if self.version != 1:
            msg = f"unsupported policy version `{self.version}`; Vigil accepts version 1"
            raise ValueError(msg)
