from __future__ import annotations

from engine.squad_intelligence.enums import (
    IntelligenceConfidence,
    MilestoneType,
    RecommendedRole,
    TrainingPotential,
)
from engine.squad_intelligence.models import PlayerMilestone

DEFAULT_REVIEW_AFTER_MATCHES = 6


def select_milestone(evaluation_context, recommended_role, confidence, squad_context=None):
    """Deterministic milestone selection. Never predicts an exact
    calendar date or invents a skill sub-level the CSV doesn't already
    expose -- milestones describe *when to look again*, not a forecast."""
    if confidence == IntelligenceConfidence.INSUFFICIENT_DATA:
        return PlayerMilestone(MilestoneType.INSUFFICIENT_DATA)

    player_context = evaluation_context.player_context
    training = player_context.training

    if recommended_role == RecommendedRole.PRIMARY_TRAINEE and evaluation_context.training_potential in (
        TrainingPotential.VERY_HIGH,
        TrainingPotential.HIGH,
    ):
        trained_skill = training.trained_skills[0] if training.trained_skills else ""
        return PlayerMilestone(
            MilestoneType.REACH_TRAINED_SKILL_LEVEL,
            {"skill": trained_skill, "current_level": training.current_trained_skill_level},
        )

    if recommended_role == RecommendedRole.VETERAN_MENTOR:
        age = getattr(player_context.player, "age", None)
        return PlayerMilestone(
            MilestoneType.REVIEW_AT_AGE, {"age": (age + 1) if age is not None else None}
        )

    if recommended_role in (
        RecommendedRole.SECONDARY_TRAINEE,
        RecommendedRole.DEVELOPMENT_PROJECT,
    ):
        return PlayerMilestone(MilestoneType.REVIEW_AFTER_TRAINING_CYCLE)

    if recommended_role in (RecommendedRole.USEFUL_ROTATION, RecommendedRole.DEPTH_PLAYER):
        return PlayerMilestone(
            MilestoneType.REVIEW_AFTER_MATCHES, {"matches": DEFAULT_REVIEW_AFTER_MATCHES}
        )

    if recommended_role in (RecommendedRole.REPLACEABLE, RecommendedRole.TRANSFER_CANDIDATE):
        position = player_context.position
        depth = squad_context.depth_at(position.best_position) if squad_context else 0
        if depth <= 1:
            return PlayerMilestone(MilestoneType.REVIEW_WHEN_REPLACEMENT_EXISTS)
        return PlayerMilestone(MilestoneType.REVIEW_WHEN_SALARY_THRESHOLD_CONTEXT_EXISTS)

    return PlayerMilestone(MilestoneType.NO_MILESTONE)
