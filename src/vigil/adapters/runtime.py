"""Runtime helpers: clock and id factory."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


class SystemClock:
    """UTC clock returning ISO-8601 timestamps."""

    def now_iso(self) -> str:
        """Return current UTC time in ISO-8601 format."""
        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class UuidFactory:
    """UUID-based decision identifiers."""

    def decision_id(self) -> str:
        """Create a decision identifier."""
        return str(uuid.uuid4())
