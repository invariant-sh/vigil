"""Read a Holds baseline JSON used to gate model-routing suggestions."""

from __future__ import annotations

import json
from pathlib import Path

from vigil.domain.errors import HoldsBaselineError
from vigil.domain.holds_baseline import HoldsQualityEvidence


class JsonHoldsBaselineReader:
    """Parse the minimum Holds baseline fields needed for routing gates."""

    def read(self, path: Path) -> HoldsQualityEvidence:
        """Load Holds quality evidence from a baseline file."""
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as error:
            msg = f"unable to read Holds baseline `{path}`: {error}"
            raise HoldsBaselineError(msg) from error
        try:
            document = json.loads(raw)
        except json.JSONDecodeError as error:
            msg = f"invalid JSON in Holds baseline `{path}`: {error}"
            raise HoldsBaselineError(msg) from error
        if not isinstance(document, dict):
            msg = "Holds baseline must be a JSON object"
            raise HoldsBaselineError(msg)
        summary = document.get("summary") or {}
        if not isinstance(summary, dict):
            msg = "Holds baseline summary must be an object"
            raise HoldsBaselineError(msg)
        threshold_passed = summary.get("threshold_passed")
        if not isinstance(threshold_passed, bool):
            msg = "summary.threshold_passed must be a boolean"
            raise HoldsBaselineError(msg)
        pass_rate = summary.get("pass_rate")
        if isinstance(pass_rate, bool) or not isinstance(pass_rate, int | float):
            msg = "summary.pass_rate must be a number"
            raise HoldsBaselineError(msg)
        model_id = document.get("model_id")
        if model_id is not None and not isinstance(model_id, str):
            msg = "model_id must be a string when present"
            raise HoldsBaselineError(msg)
        suite_hash = document.get("suite_hash")
        if suite_hash is not None and not isinstance(suite_hash, str):
            msg = "suite_hash must be a string when present"
            raise HoldsBaselineError(msg)
        run_id = document.get("run_id")
        if run_id is not None and not isinstance(run_id, str):
            msg = "run_id must be a string when present"
            raise HoldsBaselineError(msg)
        return HoldsQualityEvidence(
            source_path=str(path.resolve()),
            threshold_passed=threshold_passed,
            pass_rate=float(pass_rate),
            model_id=model_id,
            suite_hash=suite_hash,
            run_id=run_id,
        )
