"""Integer micro-USD money type (mirrors Maul's MicroUsd contract)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MicroUsd:
    """Cost expressed in millionths of a US dollar."""

    micro_usd: int

    def __post_init__(self) -> None:
        if self.micro_usd < 0:
            msg = "micro_usd must be non-negative"
            raise ValueError(msg)

    @classmethod
    def from_usd(cls, usd: float) -> MicroUsd:
        """Convert a display USD float into integer micro-USD (rounded)."""
        if usd < 0:
            msg = "usd must be non-negative"
            raise ValueError(msg)
        return cls(micro_usd=round(usd * 1_000_000))

    @classmethod
    def zero(cls) -> MicroUsd:
        """Return a zero cost."""
        return cls(micro_usd=0)

    @property
    def display(self) -> str:
        """Stable display string matching Maul report formatting."""
        return f"${self.micro_usd / 1_000_000:.6f}"

    def to_dict(self) -> dict[str, Any]:
        """Serialize as `{micro_usd, display}`."""
        return {"micro_usd": self.micro_usd, "display": self.display}

    def __add__(self, other: MicroUsd) -> MicroUsd:
        return MicroUsd(micro_usd=self.micro_usd + other.micro_usd)

    def __lt__(self, other: MicroUsd) -> bool:
        return self.micro_usd < other.micro_usd

    def __le__(self, other: MicroUsd) -> bool:
        return self.micro_usd <= other.micro_usd

    def __gt__(self, other: MicroUsd) -> bool:
        return self.micro_usd > other.micro_usd

    def __ge__(self, other: MicroUsd) -> bool:
        return self.micro_usd >= other.micro_usd
