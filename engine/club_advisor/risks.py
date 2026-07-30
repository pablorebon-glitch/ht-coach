from __future__ import annotations

from engine.club_advisor.enums import ClubRiskType, DepthStatus
from engine.club_advisor.evidence import ClubEvidence
from engine.club_advisor.models import ClubRisk
from engine.squad_intelligence.enums import RecommendedRole
from engine.weekly_training.training_priority_policy import formation_position_maximums

_HIGH_VETERAN_RATIO = 0.25


def _position(depth_summary, name):
    return next((item for item in depth_summary.positions if item.position == name), None)


def _affected_players(context, *position_names):
    names = []
    for position_name in position_names:
        names.extend(context.players_by_position.get(position_name, ()))
    return tuple(names)


def _formation_slots_for(*position_names):
    maximums = formation_position_maximums()
    return sum(maximums.get(_position_enum(name), 0) for name in position_names)


def _position_enum(position_value):
    from models.position import Position

    try:
        return Position(position_value)
    except ValueError:
        return None


def detect_risks(context, training_summary, squad_summary, depth_summary):
    """Every risk here answers, concretely: which position, why, how
    much it matters (impact), how soon it matters (urgency), which
    real players are affected, and what would need to change to revisit
    it -- never an abstract "weak positional depth" statement alone
    (Alpha 0.6.3, Part 5). Player-without-training is deliberately NOT
    reported here -- that's a training-plan concern (see warnings.py),
    not a squad-structure risk, since a position being outside the
    active training's effect is often entirely expected."""
    risks = []

    goalkeeper = _position(depth_summary, "GOALKEEPER")
    if goalkeeper is not None and goalkeeper.status == DepthStatus.NO_REPLACEMENT.value:
        affected = _affected_players(context, "GOALKEEPER")
        risks.append(
            ClubRisk(
                risk_type=ClubRiskType.ONLY_ONE_GOALKEEPER,
                evidence=(ClubEvidence("goalkeeper_count", value=goalkeeper.player_count),),
                position="GOALKEEPER",
                reason_key="club_advisor.risk_reason.only_one_goalkeeper",
                reason_params={"count": goalkeeper.player_count},
                impact="high",
                urgency="medium",
                affected_players=affected,
                review_condition_key="club_advisor.risk_review.goalkeeper_injury_or_signing",
            )
        )

    central_defender = _position(depth_summary, "CENTRAL_DEFENDER")
    wing_back = _position(depth_summary, "WING_BACK")
    if central_defender is not None and central_defender.status == DepthStatus.NO_REPLACEMENT.value:
        slots = _formation_slots_for("CENTRAL_DEFENDER", "WING_BACK")
        combined_count = central_defender.player_count + (wing_back.player_count if wing_back else 0)
        # Formation-aware impact: if combined central-defense-area
        # coverage still clears what the preferred formations actually
        # field, the gap is real but the immediate impact is lower.
        impact = "low" if combined_count >= slots else "high"
        affected = _affected_players(context, "CENTRAL_DEFENDER", "WING_BACK")
        risks.append(
            ClubRisk(
                risk_type=ClubRiskType.NO_CENTRAL_DEFENDER_REPLACEMENT,
                evidence=(
                    ClubEvidence("central_defender_count", value=central_defender.player_count),
                    ClubEvidence("formation_demand", value=slots),
                ),
                position="CENTRAL_DEFENDER",
                reason_key=(
                    "club_advisor.risk_reason.central_defense_covered_by_formation"
                    if impact == "low"
                    else "club_advisor.risk_reason.central_defense_uncovered"
                ),
                reason_params={"count": central_defender.player_count, "slots": slots},
                impact=impact,
                urgency="low" if impact == "low" else "medium",
                affected_players=affected,
                review_condition_key="club_advisor.risk_review.another_defender_unavailable",
            )
        )

    key_starters = [
        r for r in context.squad_reports if r.recommended_role == RecommendedRole.KEY_STARTER
    ]
    no_replacement_positions = [
        item for item in depth_summary.positions if item.status == DepthStatus.NO_REPLACEMENT.value
    ]
    if key_starters and no_replacement_positions:
        risks.append(
            ClubRisk(
                risk_type=ClubRiskType.STARTER_DEPENDENCY,
                evidence=(ClubEvidence("key_starter_count", value=len(key_starters)),),
                position=no_replacement_positions[0].position,
                reason_key="club_advisor.risk_reason.starter_dependency",
                reason_params={"count": len(key_starters)},
                impact="medium",
                urgency="low",
                affected_players=tuple(r.player_name for r in key_starters),
                review_condition_key="club_advisor.risk_review.key_starter_unavailable",
            )
        )

    for item in no_replacement_positions:
        risks.append(
            ClubRisk(
                risk_type=ClubRiskType.WEAK_POSITIONAL_DEPTH,
                evidence=(ClubEvidence("no_replacement_position", value=item.position),),
                position=item.position,
                reason_key="club_advisor.risk_reason.weak_positional_depth",
                reason_params={"position": item.position, "count": item.player_count},
                impact="medium",
                urgency="low",
                affected_players=_affected_players(context, item.position),
                review_condition_key="club_advisor.risk_review.position_unavailable",
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
                risk_type=ClubRiskType.POOR_TACTICAL_FLEXIBILITY,
                evidence=(ClubEvidence("tactical_specialist_count", value=0),),
                position="",
                reason_key="club_advisor.risk_reason.poor_tactical_flexibility",
                reason_params={},
                impact="low",
                urgency="low",
                affected_players=(),
                review_condition_key="club_advisor.risk_review.formation_change",
            )
        )

    if context.roster_size and (squad_summary.veteran_count / context.roster_size) >= _HIGH_VETERAN_RATIO:
        risks.append(
            ClubRisk(
                risk_type=ClubRiskType.HIGH_AGE_CONCENTRATION,
                evidence=(ClubEvidence("veteran_count", value=squad_summary.veteran_count),),
                position="",
                reason_key="club_advisor.risk_reason.high_age_concentration",
                reason_params={"count": squad_summary.veteran_count},
                impact="low",
                urgency="low",
                affected_players=squad_summary.veteran_players,
                review_condition_key="club_advisor.risk_review.next_season_planning",
            )
        )

    return tuple(risks)
