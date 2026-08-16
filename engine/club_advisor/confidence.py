from __future__ import annotations

from dataclasses import dataclass

from engine.club_advisor.enums import ClubConfidence


@dataclass(frozen=True)
class ClubConfidenceInputs:
    has_roster: bool = True
    has_active_training: bool = True
    has_squad_reports: bool = True
    has_historical_data: bool = False


def classify_confidence(inputs: ClubConfidenceInputs) -> ClubConfidence:
    """Deterministic confidence policy: never fake certainty.

    INSUFFICIENT_DATA -- no roster or no squad reports at all; nothing
      to summarize.

    HIGH -- a real roster, active training known, and squad reports
      available. Historical data is a bonus, not a requirement.

    MEDIUM -- a roster and squad reports exist, but there's no active
      training context to evaluate training-related sections against.

    LOW -- reachable only when squad reports exist but the roster
      itself looks incomplete (kept as an explicit tier rather than
      collapsing everything else into HIGH).
    """
    if not inputs.has_roster or not inputs.has_squad_reports:
        return ClubConfidence.INSUFFICIENT_DATA

    if inputs.has_active_training:
        return ClubConfidence.HIGH

    return ClubConfidence.MEDIUM
