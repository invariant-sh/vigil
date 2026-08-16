"""Domain errors for Vigil."""

from __future__ import annotations


class VigilError(Exception):
    """Base error for all Vigil failures."""


class PolicyValidationError(VigilError):
    """Raised when a policy document is invalid or unsupported."""


class MaulReportError(VigilError):
    """Raised when a Maul reliability report cannot be consumed."""


class UnsupportedReportVersionError(MaulReportError):
    """Raised when a Maul report schema_version is not supported."""


class HoldsBaselineError(VigilError):
    """Raised when a Holds baseline cannot be used to gate routing suggestions."""


class EventSourceError(VigilError):
    """Raised when dry-run request events cannot be loaded."""


class AuditError(VigilError):
    """Raised when audit records cannot be written."""


class DryRunError(VigilError):
    """Raised when a dry-run evaluation cannot complete."""
