from __future__ import annotations

from engine.club_advisor.enums import ClubStrengthType, DepthStatus
from engine.club_advisor.evidence import ClubEvidence
from engine.club_advisor.models import ClubStrength
from engine.squad_intelligence.enums import RecommendedRole

_PRIMARY_TRAINEE_PIPELINE_MIN = 2
_HIGH_VETERAN_RATIO = 0.25
_TACTICAL_SPECIALIST_MIN = 1


def detect_strengths(context, training_summary, squad_summary, depth_summary):
    strengths = []

    if (
        training_summary.players_without_training == 0
        and training_summary.full_effect_slots_used > 0
    ):
        strengths.append(
            ClubStrength(
                ClubStrengthType.TRAINING_FULLY_UTILIZED,
                (
                    ClubEvidence(
                        "full_effect_slots_used",
                        value=training_summary.full_effect_slots_used,
                    ),
                ),
            )
        )

    if training_summary.primary_trainee_count >= _PRIMARY_TRAINEE_PIPELINE_MIN:
        strengths.append(
            ClubStrength(
                ClubStrengthType.EXCELLENT_TRAINEE_PIPELINE,
                (
                    ClubEvidence(
                        "primary_trainee_count",
                        value=training_summary.primary_trainee_count,
                    ),
                ),
            )
        )

    midfield = next(
        (item for item in depth_summary.positions if item.position == "INNER_MIDFIELDER"), None
    )
    if midfield is not None and midfield.status in (
        DepthStatus.HEALTHY_COMPETITION.value,
        DepthStatus.ONE_REPLACEMENT.value,
    ):
        strengths.append(
            ClubStrength(
                ClubStrengthType.BALANCED_MIDFIELD,
                (ClubEvidence("midfield_depth", value=midfield.player_count),),
            )
        )

    specialists = sum(
        1
        for report in context.squad_reports
        if report.recommended_role == RecommendedRole.TACTICAL_SPECIALIST
    )
    if specialists >= _TACTICAL_SPECIALIST_MIN:
        strengths.append(
            ClubStrength(
                ClubStrengthType.GOOD_TACTICAL_FLEXIBILITY,
                (ClubEvidence("tactical_specialist_count", value=specialists),),
            )
        )

    roster_size = context.roster_size
    if roster_size and (squad_summary.veteran_count / roster_size) < _HIGH_VETERAN_RATIO:
        if training_summary.primary_trainee_count or training_summary.secondary_trainee_count:
            strengths.append(
                ClubStrength(
                    ClubStrengthType.HEALTHY_AGE_DISTRIBUTION,
                    (
                        ClubEvidence("veteran_count", value=squad_summary.veteran_count),
                        ClubEvidence(
                            "trainee_count",
                            value=training_summary.primary_trainee_count
                            + training_summary.secondary_trainee_count,
                        ),
                    ),
                )
            )

    no_replacement_positions = [
        item for item in depth_summary.positions if item.status == DepthStatus.NO_REPLACEMENT.value
    ]
    if not no_replacement_positions:
        strengths.append(
            ClubStrength(
                ClubStrengthType.STRONG_POSITIONAL_COVERAGE,
                (ClubEvidence("positions_without_replacement", value=0),),
            )
        )

    return tuple(strengths)
