from __future__ import annotations

from dataclasses import dataclass

from engine.club_advisor.enums import OperationalUrgency, StrategicNeed
from engine.club_advisor.evidence import ClubEvidence

_URGENCY_ORDER = [
    OperationalUrgency.NONE,
    OperationalUrgency.DEFERRED,
    OperationalUrgency.LOW,
    OperationalUrgency.MEDIUM,
    OperationalUrgency.HIGH,
    OperationalUrgency.IMMEDIATE,
]

# The "prior": a need level's urgency before any season-context modifier is
# applied. Deliberately one tier gentler than a naive "need == urgency"
# reading, since sustainable-growth strategy itself already implies patience
# -- see docs/CLUB_ADVISOR.md's "need vs urgency" section.
_NEED_TO_BASE_URGENCY_INDEX = {
    StrategicNeed.CRITICAL: 4,  # HIGH
    StrategicNeed.HIGH: 3,  # MEDIUM
    StrategicNeed.MEDIUM: 2,  # LOW
    StrategicNeed.LOW: 1,  # DEFERRED
    StrategicNeed.NONE: 0,  # NONE
}

# A genuine need is never fully erased by favorable season context -- these
# floors are the documented minimum urgency tier reducers can bring a need
# down to. A CRITICAL need can never be reduced below MEDIUM urgency; a HIGH
# need never below LOW; and so on. This is what keeps "high need, low
# urgency" (the sprint's own worked example) from silently collapsing into
# "no need to look at this at all".
_MINIMUM_URGENCY_FLOOR_INDEX = {
    StrategicNeed.CRITICAL: 3,  # MEDIUM
    StrategicNeed.HIGH: 2,  # LOW
    StrategicNeed.MEDIUM: 1,  # DEFERRED
    StrategicNeed.LOW: 0,  # NONE
    StrategicNeed.NONE: 0,
}

_BOT_OPPONENT_THRESHOLD = 2


@dataclass(frozen=True)
class UrgencyInputs:
    """Area-specific facts the season context alone can't know --
    supplied by the caller (e.g. Club Advisor's existing depth/risk
    detection) rather than recomputed here."""

    area_matches_recent_signing: bool = False
    has_no_internal_replacement: bool = False
    player_unavailable: bool = False


def compute_urgency(strategic_need, season_context, inputs: UrgencyInputs | None = None):
    """Computes OperationalUrgency from StrategicNeed and SeasonContext.
    Never derives urgency from need alone -- see docs/CLUB_ADVISOR.md's
    "need vs urgency" section for the full policy this implements.

    Returns (OperationalUrgency, evidence_tuple).
    """
    inputs = inputs or UrgencyInputs()
    evidence = []

    if strategic_need == StrategicNeed.INSUFFICIENT_DATA:
        return OperationalUrgency.INSUFFICIENT_DATA, ()
    if strategic_need == StrategicNeed.NONE:
        return OperationalUrgency.NONE, ()

    index = _NEED_TO_BASE_URGENCY_INDEX[strategic_need]

    if season_context.is_dominant_or_strong:
        index -= 1
        evidence.append(
            ClubEvidence(
                "competitiveness_reduces_urgency",
                label_key="club_advisor.evidence.competitiveness_reduces_urgency",
                value=season_context.current_competitiveness.value,
            )
        )
    if (season_context.bot_opponent_count or 0) >= _BOT_OPPONENT_THRESHOLD:
        index -= 1
        evidence.append(
            ClubEvidence(
                "bot_opponents_reduce_urgency",
                label_key="club_advisor.evidence.bot_opponents_reduce_urgency",
                value=season_context.bot_opponent_count,
            )
        )
    if season_context.is_early_season_like:
        index -= 1
        evidence.append(
            ClubEvidence(
                "early_season_reduces_urgency",
                label_key="club_advisor.evidence.early_season_reduces_urgency",
                value=season_context.season_phase.value,
            )
        )
    if inputs.area_matches_recent_signing:
        index -= 1
        evidence.append(
            ClubEvidence(
                "recent_signing_reduces_urgency",
                label_key="club_advisor.evidence.recent_signing_reduces_urgency",
                value=season_context.recent_signing_position,
            )
        )
    if season_context.promotion_is_deprioritized:
        index -= 1
        evidence.append(
            ClubEvidence(
                "promotion_deprioritized_reduces_urgency",
                label_key="club_advisor.evidence.promotion_deprioritized_reduces_urgency",
                value=season_context.promotion_objective.value,
            )
        )

    if inputs.has_no_internal_replacement:
        index += 2
        evidence.append(
            ClubEvidence(
                "no_replacement_increases_urgency",
                label_key="club_advisor.evidence.no_replacement_increases_urgency",
            )
        )
    if inputs.player_unavailable:
        index += 2
        evidence.append(
            ClubEvidence(
                "player_unavailable_increases_urgency",
                label_key="club_advisor.evidence.player_unavailable_increases_urgency",
            )
        )
    if season_context.is_late_season_like:
        index += 1
        evidence.append(
            ClubEvidence(
                "late_season_increases_urgency",
                label_key="club_advisor.evidence.late_season_increases_urgency",
                value=season_context.season_phase.value,
            )
        )
    if season_context.promotion_is_urgent:
        index += 1
        evidence.append(
            ClubEvidence(
                "promotion_targeted_increases_urgency",
                label_key="club_advisor.evidence.promotion_targeted_increases_urgency",
                value=season_context.promotion_objective.value,
            )
        )

    floor = _MINIMUM_URGENCY_FLOOR_INDEX[strategic_need]
    index = max(floor, min(index, len(_URGENCY_ORDER) - 1))
    return _URGENCY_ORDER[index], tuple(evidence)
