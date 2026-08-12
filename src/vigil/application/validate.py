"""Validate a Vigil policy document."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vigil.domain.policy import Policy
from vigil.ports import PolicyLoader


@dataclass(frozen=True, slots=True)
class ValidateResult:
    """Outcome of validating a policy file."""

    policy: Policy
    path: Path


class ValidatePolicyService:
    """Load and validate a policy through the PolicyLoader port."""

    def __init__(self, *, policy_loader: PolicyLoader) -> None:
        self._policy_loader = policy_loader

    def execute(self, path: Path) -> ValidateResult:
        """Validate the policy at `path` and return the typed document."""
        policy = self._policy_loader.load(path)
        return ValidateResult(policy=policy, path=path)
