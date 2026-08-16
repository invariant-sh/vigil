"""Typed view of a Holds baseline used to gate model-routing suggestions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HoldsQualityEvidence:
    """Minimum Holds evidence required before suggesting model routing."""

    source_path: str
    threshold_passed: bool
    pass_rate: float
    model_id: str | None
    suite_hash: str | None
    run_id: str | None
