from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.history.insights.enums import EvidenceType


@dataclass(frozen=True)
class InsightEvidence:
    """A single, inspectable fact backing an insight. An insight with no
    evidence must either be omitted by its rule or reclassified as
    INSUFFICIENT_DATA — never asserted on its own."""

    evidence_type: EvidenceType
    entity_id: str = ""
    entity_label: str = ""
    previous_value: Any = None
    current_value: Any = None
    delta: Any = None
    source_snapshot: str = ""  # "current" | "previous" | "both"
    reliability: str = "direct"  # "direct" | "indirect"
    affected_sectors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_type": self.evidence_type.value,
            "entity_id": self.entity_id,
            "entity_label": self.entity_label,
            "previous_value": self.previous_value,
            "current_value": self.current_value,
            "delta": self.delta,
            "source_snapshot": self.source_snapshot,
            "reliability": self.reliability,
            "affected_sectors": list(self.affected_sectors),
        }
