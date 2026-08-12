"""Unit tests for policy domain invariants."""

from __future__ import annotations

import pytest

from vigil.domain.money import MicroUsd
from vigil.domain.policy import Budgets, ModelPolicy, Scope


def test_scope_requires_non_empty() -> None:
    with pytest.raises(ValueError, match="project"):
        Scope(project=" ", environment="production")


def test_model_policy_requires_fallback_when_routing() -> None:
    with pytest.raises(ValueError, match="fallback_model"):
        ModelPolicy(allow=("gpt-4o-mini",), route_after_cost_usd=MicroUsd.from_usd(0.1))


def test_fallback_must_be_allowlisted() -> None:
    with pytest.raises(ValueError, match="allow"):
        ModelPolicy(
            allow=("gpt-4o-mini",),
            route_after_cost_usd=MicroUsd.from_usd(0.1),
            fallback_model="gpt-4o",
        )


def test_budget_call_cap_must_be_positive() -> None:
    with pytest.raises(ValueError, match="max_llm_calls"):
        Budgets(max_llm_calls_per_workflow=0)
