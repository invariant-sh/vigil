"""Stable process exit codes for the Vigil CLI."""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Public CLI exit status contract."""

    SUCCESS = 0
    USAGE = 2
    INVALID_POLICY = 10
    INVALID_MAUL_REPORT = 20
    UNSUPPORTED_REPORT_VERSION = 21
    EVENT_SOURCE_FAILURE = 30
    DRY_RUN_FAILURE = 40
    AUDIT_FAILURE = 50
    INTERNAL = 70
