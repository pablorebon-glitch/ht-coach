from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IntelligenceEvidence:
    """One inspectable fact backing a dimension, role, status or
    milestone conclusion. Every visible conclusion must be traceable to
    at least one of these -- domain rules never assert a category
    without attaching the evidence that produced it."""

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
