"""Ports (protocols) for injectable dependencies."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from vigil.domain.decision import DecisionRecord
from vigil.domain.events import RequestEvent
from vigil.domain.maul_report import MaulReport
from vigil.domain.policy import Policy
from vigil.domain.suggestions import SuggestionDraft


class PolicyLoader(Protocol):
    """Loads and validates a policy document."""

    def load(self, path: Path) -> Policy:
        """Parse and validate a policy file."""


class MaulReportReader(Protocol):
    """Reads a versioned Maul reliability report."""

    def read(self, path: Path) -> MaulReport:
        """Parse a Maul report into a typed view."""


class EventSource(Protocol):
    """Provides recorded request events for dry-run."""

    def load(self, path: Path) -> tuple[RequestEvent, ...]:
        """Load request events from a path."""


class AuditSink(Protocol):
    """Persists redacted audit events."""

    def write(self, path: Path, records: tuple[DecisionRecord, ...]) -> Path:
        """Append or write decision records as audit events."""


class DecisionSink(Protocol):
    """Persists dry-run decision records."""

    def write(self, path: Path, records: tuple[DecisionRecord, ...]) -> Path:
        """Write decision records."""


class SuggestionWriter(Protocol):
    """Persists from-maul suggestion drafts."""

    def write(self, path: Path, draft: SuggestionDraft) -> Path:
        """Write a suggestion draft."""


class Clock(Protocol):
    """Provides timestamps."""

    def now_iso(self) -> str:
        """Return an ISO-8601 UTC timestamp."""


class IdFactory(Protocol):
    """Creates identifiers for decisions."""

    def decision_id(self) -> str:
        """Create a decision identifier."""


__all__ = [
    "AuditSink",
    "Clock",
    "DecisionSink",
    "EventSource",
    "IdFactory",
    "MaulReportReader",
    "PolicyLoader",
    "SuggestionWriter",
]
