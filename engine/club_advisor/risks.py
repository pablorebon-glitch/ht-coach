from __future__ import annotations

from engine.club_advisor.enums import ClubRiskType, DepthStatus
from engine.club_advisor.evidence import ClubEvidence
from engine.club_advisor.models import ClubRisk
from engine.squad_intelligence.enums import RecommendedRole

_HIGH_UNTRAINED_RATIO = 0.3
_HIGH_VETERAN_RATIO = 0.25
_TRAINABLE_POSITIONS_FOR_SLOT_PRESSURE = ("INNER_MIDFIELDER", "WINGER")


def _position(depth_summary, name):
    return next((item for item in depth_summary.positions if item.position == name), None)


def detect_risks(context, training_summary, squad_summary, depth_summary):
    risks = []

    goalkeeper = _position(depth_summary, "GOALKEEPER")
    if goalkeeper is not None and goalkeeper.status == DepthStatus.NO_REPLACEMENT.value:
        risks.append(
            ClubRisk(
                ClubRiskType.ONLY_ONE_GOALKEEPER,
                (ClubEvidence("goalkeeper_count", value=goalkeeper.player_count),),
            )
        )

    central_defender = _position(depth_summary, "CENTRAL_DEFENDER")
    if central_defender is not None and central_defender.status == DepthStatus.NO_REPLACEMENT.value:
        risks.append(
            ClubRisk(
                ClubRiskType.NO_CENTRAL_DEFENDER_REPLACEMENT,
                (ClubEvidence("central_defender_count", value=central_defender.player_count),),
            )
        )

    if training_summary.total_players_evaluated:
        ratio = training_summary.players_without_training / training_summary.total_players_evaluated
        if ratio >= _HIGH_UNTRAINED_RATIO:
            risks.append(
                ClubRisk(
                    ClubRiskType.PLAYERS_WITHOUT_TRAINING,
                    (
                        ClubEvidence(
                            "players_without_training",
                            value=training_summary.players_without_training,
                        ),
                    ),
                )
            )

    for position_name in _TRAINABLE_POSITIONS_FOR_SLOT_PRESSURE:
        position = _position(depth_summary, position_name)
        if position is not None and position.status == DepthStatus.EXCESS_PLAYERS.value:
            risks.append(
                ClubRisk(
                    ClubRiskType.TOO_MANY_PLAYERS_PER_TRAINING_SLOT,
                    (ClubEvidence("position", value=position_name),),
                )
            )
            break

    key_starters = [
        r for r in context.squad_reports if r.recommended_role == RecommendedRole.KEY_STARTER
    ]
    no_replacement_positions = [
        item for item in depth_summary.positions if item.status == DepthStatus.NO_REPLACEMENT.value
    ]
    if key_starters and no_replacement_positions:
        risks.append(
            ClubRisk(
                ClubRiskType.STARTER_DEPENDENCY,
                (ClubEvidence("key_starter_count", value=len(key_starters)),),
            )
        )

    if no_replacement_positions:
        risks.append(
            ClubRisk(
                ClubRiskType.WEAK_POSITIONAL_DEPTH,
                tuple(
                    ClubEvidence("no_replacement_position", value=item.position)
                    for item in no_replacement_positions
                ),
            )
        )

    specialists = sum(
        1
        for report in context.squad_reports
        if report.recommended_role == RecommendedRole.TACTICAL_SPECIALIST
    )
    if context.roster_size >= 10 and specialists == 0:
        risks.append(
            ClubRisk(
                ClubRiskType.POOR_TACTICAL_FLEXIBILITY,
                (ClubEvidence("tactical_specialist_count", value=0),),
            )
        )

    if context.roster_size and (squad_summary.veteran_count / context.roster_size) >= _HIGH_VETERAN_RATIO:
        risks.append(
            ClubRisk(
                ClubRiskType.HIGH_AGE_CONCENTRATION,
                (ClubEvidence("veteran_count", value=squad_summary.veteran_count),),
            )
        )

    return tuple(risks)
