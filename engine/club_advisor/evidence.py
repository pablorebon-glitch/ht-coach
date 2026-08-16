from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ClubEvidence:
    """One inspectable fact backing a club-level conclusion. Every
    priority, strength, risk and warning must carry at least one of
    these -- never an assertion without a traceable fact behind it."""

    evidence_type: str
    label_key: str = ""
    value: Any = None
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_type": self.evidence_type,
            "label_key": self.label_key,
            "value": self.value,
            "detail": self.detail,
        }
