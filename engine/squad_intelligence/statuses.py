from __future__ import annotations

from engine.squad_intelligence.enums import (
    ManagementStatus,
    RecommendedRole,
    SalaryEfficiency,
    StrategicValue,
    TrainingFit,
    TrainingPotential,
)
from engine.squad_intelligence.evidence import IntelligenceEvidence
from engine.squad_intelligence.rule import StatusRule

_TRAINEE_ROLES = (
    RecommendedRole.PRIMARY_TRAINEE,
    RecommendedRole.SECONDARY_TRAINEE,
    RecommendedRole.DEVELOPMENT_PROJECT,
)


class ReviewAtNextSkillLevelStatusRule(StatusRule):
    """More specific than plain TRAIN for a primary trainee with very
    high potential: there's an identifiable near-term milestone worth
    flagging, not just "keep training indefinitely"."""

    rule_id = "status.review_at_next_skill_level"
    priority = 85

    def evaluate(self, context, resolved_role):
        if resolved_role != RecommendedRole.PRIMARY_TRAINEE:
            return None
        if context.training_potential != TrainingPotential.VERY_HIGH:
            return None
        evidence = (
            IntelligenceEvidence(
                "training_potential",
                label_key="squad_intelligence.evidence.training_potential",
                value=context.training_potential.value,
            ),
        )
        return (ManagementStatus.REVIEW_AT_NEXT_SKILL_LEVEL, self.priority, evidence)


class TrainStatusRule(StatusRule):
    rule_id = "status.train"
    priority = 80

    def evaluate(self, context, resolved_role):
        if resolved_role not in _TRAINEE_ROLES:
            return None
        if context.training_fit not in (
            TrainingFit.EXCELLENT,
            TrainingFit.COMPATIBLE,
            TrainingFit.PARTIAL,
        ):
            return None
        evidence = (
            IntelligenceEvidence(
                "training_fit",
                label_key="squad_intelligence.evidence.training_fit",
                value=context.training_fit.value,
            ),
        )
        return (ManagementStatus.TRAIN, self.priority, evidence)


class KeepStatusRule(StatusRule):
    rule_id = "status.keep"
    priority = 75

    def evaluate(self, context, resolved_role):
        if resolved_role not in (
            RecommendedRole.KEY_STARTER,
            RecommendedRole.STARTER,
            RecommendedRole.TACTICAL_SPECIALIST,
        ):
            return None
        if context.strategic_value not in (
            StrategicValue.KEY,
            StrategicValue.HIGH,
            StrategicValue.MEDIUM,
        ):
            return None
        evidence = (
            IntelligenceEvidence(
                "recommended_role",
                label_key="squad_intelligence.evidence.recommended_role",
                value=resolved_role.value,
            ),
            IntelligenceEvidence(
                "strategic_value",
                label_key="squad_intelligence.evidence.strategic_value",
                value=context.strategic_value.value,
            ),
        )
        return (ManagementStatus.KEEP, self.priority, evidence)


class EvaluateSaleStatusRule(StatusRule):
    rule_id = "status.evaluate_sale"
    priority = 70

    def evaluate(self, context, resolved_role):
        if resolved_role != RecommendedRole.TRANSFER_CANDIDATE:
            return None
        evidence = (
            IntelligenceEvidence(
                "recommended_role",
                label_key="squad_intelligence.evidence.recommended_role",
                value=resolved_role.value,
            ),
        )
        return (ManagementStatus.EVALUATE_SALE, self.priority, evidence)


class GraduallyReplaceStatusRule(StatusRule):
    rule_id = "status.gradually_replace"
    priority = 65

    def evaluate(self, context, resolved_role):
        if resolved_role != RecommendedRole.REPLACEABLE:
            return None
        evidence = (
            IntelligenceEvidence(
                "recommended_role",
                label_key="squad_intelligence.evidence.recommended_role",
                value=resolved_role.value,
            ),
        )
        return (ManagementStatus.GRADUALLY_REPLACE, self.priority, evidence)


class DoNotInvestMoreTrainingStatusRule(StatusRule):
    rule_id = "status.do_not_invest_more_training"
    priority = 60

    def evaluate(self, context, resolved_role):
        if resolved_role in (RecommendedRole.KEY_STARTER, RecommendedRole.STARTER):
            return None
        if context.training_fit not in (TrainingFit.NO_TRAINING, TrainingFit.NOT_PRIORITIZED):
            return None
        if context.training_potential not in (
            TrainingPotential.LOW,
            TrainingPotential.EXHAUSTED,
            TrainingPotential.NOT_APPLICABLE,
        ):
            return None
        evidence = (
            IntelligenceEvidence(
                "training_fit",
                label_key="squad_intelligence.evidence.training_fit",
                value=context.training_fit.value,
            ),
            IntelligenceEvidence(
                "training_potential",
                label_key="squad_intelligence.evidence.training_potential",
                value=context.training_potential.value,
            ),
        )
        return (ManagementStatus.DO_NOT_INVEST_MORE_TRAINING, self.priority, evidence)


class MaintainAsDepthStatusRule(StatusRule):
    rule_id = "status.maintain_as_depth"
    priority = 55

    def evaluate(self, context, resolved_role):
        if resolved_role not in (
            RecommendedRole.USEFUL_ROTATION,
            RecommendedRole.DEPTH_PLAYER,
            RecommendedRole.VETERAN_MENTOR,
        ):
            return None
        if context.salary_efficiency == SalaryEfficiency.VERY_LOW:
            return None
        evidence = (
            IntelligenceEvidence(
                "recommended_role",
                label_key="squad_intelligence.evidence.recommended_role",
                value=resolved_role.value,
            ),
        )
        return (ManagementStatus.MAINTAIN_AS_DEPTH, self.priority, evidence)


class MonitorStatusRule(StatusRule):
    """The guaranteed fallback: incomplete evidence or a mixed profile
    that doesn't clearly match any other status still needs an actual
    action, not silence."""

    rule_id = "status.monitor"
    priority = 1

    def evaluate(self, context, resolved_role):
        evidence = (
            IntelligenceEvidence(
                "fallback_status",
                label_key="squad_intelligence.evidence.fallback_status",
            ),
        )
        return (ManagementStatus.MONITOR, self.priority, evidence)


def default_status_rules() -> tuple:
    return (
        ReviewAtNextSkillLevelStatusRule(),
        TrainStatusRule(),
        KeepStatusRule(),
        EvaluateSaleStatusRule(),
        GraduallyReplaceStatusRule(),
        DoNotInvestMoreTrainingStatusRule(),
        MaintainAsDepthStatusRule(),
        MonitorStatusRule(),
    )
