from __future__ import annotations

from engine.club_advisor.enums import ClubWarningType, DepthStatus
from engine.club_advisor.evidence import ClubEvidence
from engine.club_advisor.models import ClubWarning
from engine.squad_intelligence.enums import RecommendedRole

_HIGH_UNTRAINED_RATIO = 0.3
_HIGH_VETERAN_RATIO = 0.25


def _position(depth_summary, name):
    return next((item for item in depth_summary.positions if item.position == name), None)


def generate_warnings(context, training_summary, squad_summary, depth_summary):
    """Every warning states a reason (`reason_key` + `reason_params`),
    never just an unexplained label."""
    warnings = []

    goalkeeper = _position(depth_summary, "GOALKEEPER")
    if goalkeeper is not None and goalkeeper.status == DepthStatus.NO_REPLACEMENT.value:
        warnings.append(
            ClubWarning(
                ClubWarningType.NO_GOALKEEPER_BACKUP,
                reason_key="club_advisor.warning_reason.no_goalkeeper_backup",
                reason_params={"count": goalkeeper.player_count},
                evidence=(ClubEvidence("goalkeeper_count", value=goalkeeper.player_count),),
            )
        )

    if (
        context.has_active_training
        and training_summary.total_players_evaluated
        and training_summary.full_effect_slots_used == 0
    ):
        warnings.append(
            ClubWarning(
                ClubWarningType.TRAINING_CAPACITY_UNDERUSED,
                reason_key="club_advisor.warning_reason.training_capacity_underused",
                reason_params={"training_type": context.active_training_type},
                evidence=(
                    ClubEvidence(
                        "full_effect_slots_used", value=training_summary.full_effect_slots_used
                    ),
                ),
            )
        )

    key_starters = [
        r for r in context.squad_reports if r.recommended_role == RecommendedRole.KEY_STARTER
    ]
    no_replacement_positions = [
        item for item in depth_summary.positions if item.status == DepthStatus.NO_REPLACEMENT.value
    ]
    if key_starters and no_replacement_positions:
        warnings.append(
            ClubWarning(
                ClubWarningType.STARTER_HAS_NO_REPLACEMENT,
                reason_key="club_advisor.warning_reason.starter_has_no_replacement",
                reason_params={"count": len(key_starters)},
                evidence=tuple(
                    ClubEvidence("no_replacement_position", value=item.position)
                    for item in no_replacement_positions
                ),
            )
        )

    if training_summary.total_players_evaluated:
        ratio = training_summary.players_without_training / training_summary.total_players_evaluated
        if ratio >= _HIGH_UNTRAINED_RATIO:
            warnings.append(
                ClubWarning(
                    ClubWarningType.PLAYERS_NOT_RECEIVING_TRAINING,
                    reason_key="club_advisor.warning_reason.players_not_receiving_training",
                    reason_params={"count": training_summary.players_without_training},
                    evidence=(
                        ClubEvidence(
                            "players_without_training",
                            value=training_summary.players_without_training,
                        ),
                    ),
                )
            )

    if context.roster_size and (squad_summary.veteran_count / context.roster_size) >= _HIGH_VETERAN_RATIO:
        warnings.append(
            ClubWarning(
                ClubWarningType.HIGH_EXPERIENCE_CONCENTRATION,
                reason_key="club_advisor.warning_reason.high_experience_concentration",
                reason_params={"count": squad_summary.veteran_count},
                evidence=(ClubEvidence("veteran_count", value=squad_summary.veteran_count),),
            )
        )

    specialists = sum(
        1
        for report in context.squad_reports
        if report.recommended_role == RecommendedRole.TACTICAL_SPECIALIST
    )
    if context.roster_size >= 10 and specialists == 0:
        warnings.append(
            ClubWarning(
                ClubWarningType.LOW_POSITIONAL_FLEXIBILITY,
                reason_key="club_advisor.warning_reason.low_positional_flexibility",
                reason_params={},
                evidence=(ClubEvidence("tactical_specialist_count", value=0),),
            )
        )

    return tuple(warnings)
