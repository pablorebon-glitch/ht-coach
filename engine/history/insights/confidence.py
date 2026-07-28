from __future__ import annotations

from dataclasses import dataclass

from engine.history.insights.enums import InsightConfidence


@dataclass(frozen=True)
class ConfidenceInputs:
    """The signals a rule must honestly report about its own insight.
    `classify_confidence` turns these into a label deterministically —
    rules never assign a confidence label themselves."""

    has_required_evidence: bool = True
    scales_compatible: bool = True
    snapshots_comparable: bool = True
    structural_change: bool = False
    data_complete: bool = True
    deterministic_sector_effect: bool = False
    contradictory_evidence: bool = False
    supporting_signal_count: int = 0


def classify_confidence(inputs: ConfidenceInputs) -> InsightConfidence:
    """Deterministic confidence policy (documented, not hardcoded per
    rule):

    INSUFFICIENT_DATA — required evidence is missing, rating scales are
      incompatible, or the snapshots aren't meaningfully comparable.
      This check always wins first, regardless of everything else.

    HIGH — a direct structural change, complete data in both snapshots,
      a known deterministic sector effect, and no contradictory
      evidence. All four must hold.

    MEDIUM — a plausible contributing change with sufficient (if
      incomplete) data and at least two supporting signals, and no
      contradictory evidence.

    LOW — everything else that still has at least one signal to point
      to (a weak/indirect association).
    """
    if (
        not inputs.has_required_evidence
        or not inputs.scales_compatible
        or not inputs.snapshots_comparable
    ):
        return InsightConfidence.INSUFFICIENT_DATA

    if (
        inputs.structural_change
        and inputs.data_complete
        and inputs.deterministic_sector_effect
        and not inputs.contradictory_evidence
    ):
        return InsightConfidence.HIGH

    if (
        inputs.data_complete
        and inputs.supporting_signal_count >= 2
        and not inputs.contradictory_evidence
    ):
        return InsightConfidence.MEDIUM

    if inputs.supporting_signal_count >= 1:
        return InsightConfidence.LOW

    return InsightConfidence.INSUFFICIENT_DATA
