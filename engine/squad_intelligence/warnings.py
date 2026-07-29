from __future__ import annotations

from engine.squad_intelligence.dimensions import FORM_LOW, STAMINA_LOW
from engine.squad_intelligence.enums import (
    CurrentPerformance,
    LimitationType,
    RecommendedRole,
    RiskType,
    SalaryEfficiency,
    StrategicValue,
    StrengthType,
    TrainingFit,
    TrainingPotential,
)
from engine.squad_intelligence.evidence import IntelligenceEvidence
from engine.squad_intelligence.models import PlayerRisk, PlayerStrength

MAX_VISIBLE_STRENGTHS = 3
MAX_VISIBLE_RISKS = 3


def _is_valuable_speciality(player):
    speciality = (getattr(player, "speciality", "") or "").strip()
    return speciality and speciality.lower() not in ("none", "unknown", "no especialidad")


def detect_strengths(evaluation_context, squad_context, recommended_role):
    player_context = evaluation_context.player_context
    player = player_context.player
    position = player_context.position
    strengths = []

    if evaluation_context.current_performance in (
        CurrentPerformance.HIGH,
        CurrentPerformance.VERY_HIGH,
    ):
        strengths.append(
            PlayerStrength(
                StrengthType.STRONG_CURRENT_CONTRIBUTION,
                (
                    IntelligenceEvidence(
                        "current_performance",
                        value=evaluation_context.current_performance.value,
                    ),
                ),
            )
        )

    if evaluation_context.training_fit == TrainingFit.EXCELLENT:
        strengths.append(
            PlayerStrength(
                StrengthType.EXCELLENT_TRAINING_FIT,
                (IntelligenceEvidence("training_fit", value="EXCELLENT"),),
            )
        )

    age = getattr(player, "age", None)
    if age is not None and age <= 23:
        strengths.append(
            PlayerStrength(
                StrengthType.FAVORABLE_AGE,
                (IntelligenceEvidence("age", value=age),),
            )
        )

    if len(position.alternative_positions) >= 2:
        strengths.append(
            PlayerStrength(
                StrengthType.TACTICAL_VERSATILITY,
                (
                    IntelligenceEvidence(
                        "alternative_positions",
                        value=", ".join(position.alternative_positions),
                    ),
                ),
            )
        )

    if _is_valuable_speciality(player):
        strengths.append(
            PlayerStrength(
                StrengthType.VALUABLE_SPECIALTY,
                (IntelligenceEvidence("speciality", value=player.speciality),),
            )
        )

    if evaluation_context.salary_efficiency in (
        SalaryEfficiency.EXCELLENT,
        SalaryEfficiency.GOOD,
    ):
        strengths.append(
            PlayerStrength(
                StrengthType.LOW_SALARY_RELATIVE_TO_ROLE,
                (
                    IntelligenceEvidence(
                        "salary_efficiency",
                        value=evaluation_context.salary_efficiency.value,
                    ),
                ),
            )
        )

    if squad_context is not None and position.best_position:
        depth = squad_context.depth_at(position.best_position)
        if 0 < depth <= 1:
            strengths.append(
                PlayerStrength(
                    StrengthType.HARD_TO_REPLACE,
                    (IntelligenceEvidence("positional_depth", value=depth),),
                )
            )

    if recommended_role in (RecommendedRole.KEY_STARTER, RecommendedRole.STARTER):
        strengths.append(
            PlayerStrength(
                StrengthType.FIRST_TEAM_IMPORTANCE,
                (IntelligenceEvidence("recommended_role", value=recommended_role.value),),
            )
        )

    return tuple(strengths[:MAX_VISIBLE_STRENGTHS])


def detect_risks(evaluation_context, squad_context, recommended_role, limitations):
    player_context = evaluation_context.player_context
    player = player_context.player
    position = player_context.position
    risks = []

    if evaluation_context.training_fit in (TrainingFit.NO_TRAINING, TrainingFit.NOT_PRIORITIZED):
        risks.append(
            PlayerRisk(
                RiskType.NO_MEANINGFUL_ACTIVE_TRAINING,
                (IntelligenceEvidence("training_fit", value=evaluation_context.training_fit.value),),
            )
        )
    elif player_context.training.effect_for_best_position == "REDUCED":
        risks.append(
            PlayerRisk(
                RiskType.REDUCED_TRAINING_ONLY,
                (IntelligenceEvidence("training_effect", value="REDUCED"),),
            )
        )

    if evaluation_context.training_potential in (
        TrainingPotential.LOW,
        TrainingPotential.EXHAUSTED,
    ):
        risks.append(
            PlayerRisk(
                RiskType.DECLINING_DEVELOPMENT_RUNWAY,
                (
                    IntelligenceEvidence(
                        "training_potential",
                        value=evaluation_context.training_potential.value,
                    ),
                ),
            )
        )

    if evaluation_context.salary_efficiency in (
        SalaryEfficiency.LOW,
        SalaryEfficiency.VERY_LOW,
    ):
        risks.append(
            PlayerRisk(
                RiskType.HIGH_SALARY_RELATIVE_TO_ROLE,
                (
                    IntelligenceEvidence(
                        "salary_efficiency",
                        value=evaluation_context.salary_efficiency.value,
                    ),
                ),
            )
        )

    stamina = getattr(player, "stamina", None)
    if stamina is not None and stamina <= STAMINA_LOW:
        risks.append(
            PlayerRisk(RiskType.POOR_STAMINA, (IntelligenceEvidence("stamina", value=stamina),))
        )

    form = getattr(player, "form", None)
    if form is not None and form <= FORM_LOW:
        risks.append(
            PlayerRisk(RiskType.POOR_FORM, (IntelligenceEvidence("form", value=form),))
        )

    if not player_context.is_available:
        risks.append(
            PlayerRisk(
                RiskType.INJURED_OR_UNAVAILABLE,
                (IntelligenceEvidence("availability", value=player_context.availability_label),),
            )
        )

    if position.is_available and not position.alternative_positions:
        risks.append(
            PlayerRisk(
                RiskType.LIMITED_POSITIONAL_FLEXIBILITY,
                (IntelligenceEvidence("best_position", value=position.best_position),),
            )
        )

    if (
        position.is_available
        and position.rank_in_best_position is not None
        and position.rank_in_best_position > 1
        and position.candidates_in_best_position >= 2
    ):
        risks.append(
            PlayerRisk(
                RiskType.BLOCKED_BY_STRONGER_PLAYERS,
                (
                    IntelligenceEvidence(
                        "squad_rank",
                        value=f"{position.rank_in_best_position}/{position.candidates_in_best_position}",
                    ),
                ),
            )
        )

    if recommended_role in (RecommendedRole.DEPTH_PLAYER, RecommendedRole.REPLACEABLE):
        risks.append(
            PlayerRisk(
                RiskType.NO_CLEAR_SQUAD_ROLE,
                (IntelligenceEvidence("recommended_role", value=recommended_role.value),),
            )
        )

    if limitations:
        risks.append(
            PlayerRisk(
                RiskType.MISSING_DATA,
                tuple(
                    IntelligenceEvidence("limitation", value=item.value)
                    for item in limitations
                ),
            )
        )

    return tuple(risks[:MAX_VISIBLE_RISKS])
