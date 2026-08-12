"""Shared fakes for Vigil tests."""

from __future__ import annotations

from pathlib import Path

from vigil.domain.decision import DecisionRecord
from vigil.domain.events import RequestEvent
from vigil.domain.maul_report import MaulReport
from vigil.domain.policy import Policy
from vigil.domain.suggestions import SuggestionDraft


class FakeClock:
    def __init__(self, stamp: str = "2026-01-01T00:00:00Z") -> None:
        self._stamp = stamp

    def now_iso(self) -> str:
        return self._stamp


class FakeIds:
    def __init__(self) -> None:
        self._n = 0

    def decision_id(self) -> str:
        self._n += 1
        return f"dec-{self._n}"


class InMemoryDecisionSink:
    def __init__(self) -> None:
        self.records: tuple[DecisionRecord, ...] = ()
        self.path: Path | None = None

    def write(self, path: Path, records: tuple[DecisionRecord, ...]) -> Path:
        self.path = path
        self.records = records
        return path


class InMemoryAuditSink:
    def __init__(self) -> None:
        self.records: tuple[DecisionRecord, ...] = ()
        self.path: Path | None = None

    def write(self, path: Path, records: tuple[DecisionRecord, ...]) -> Path:
        self.path = path
        self.records = records
        return path


class StaticPolicyLoader:
    def __init__(self, policy: Policy) -> None:
        self._policy = policy

    def load(self, path: Path) -> Policy:
        del path
        return self._policy


class StaticEventSource:
    def __init__(self, events: tuple[RequestEvent, ...]) -> None:
        self._events = events

    def load(self, path: Path) -> tuple[RequestEvent, ...]:
        del path
        return self._events


class StaticMaulReader:
    def __init__(self, report: MaulReport) -> None:
        self._report = report

    def read(self, path: Path) -> MaulReport:
        del path
        return self._report


class CapturingSuggestionWriter:
    def __init__(self) -> None:
        self.draft: SuggestionDraft | None = None
        self.path: Path | None = None

    def write(self, path: Path, draft: SuggestionDraft) -> Path:
        self.path = path
        self.draft = draft
        return path
