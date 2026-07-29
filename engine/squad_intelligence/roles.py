from __future__ import annotations

from engine.squad_intelligence.enums import (
    CurrentPerformance,
    RecommendedRole,
    SalaryEfficiency,
    StrategicValue,
    TrainingFit,
    TrainingPotential,
)
from engine.squad_intelligence.evidence import IntelligenceEvidence
from engine.squad_intelligence.rule import RoleRule

_REQUIRED_PRIORITIES = ("REQUIRED_100", "REQUIRED_50")
VETERAN_AGE_THRESHOLD = 30


class KeyStarterRule(RoleRule):
    """Takes priority over PrimaryTraineeRule when a player is both a
    very-high performer and hard to replace: being currently
    irreplaceable is treated as more urgent than training status. This
    is a deliberate, documented resolution of the "qualifies as both"
    conflict described in the sprint brief -- see
    docs/SQUAD_INTELLIGENCE.md."""

    rule_id = "role.key_starter"
    priority = 95

    def evaluate(self, context):
        if context.current_performance != CurrentPerformance.VERY_HIGH:
            return None
        if context.strategic_value not in (StrategicValue.KEY, StrategicValue.HIGH):
            return None
        evidence = (
            IntelligenceEvidence(
                "current_performance",
                label_key="squad_intelligence.evidence.current_performance",
                value=context.current_performance.value,
            ),
            IntelligenceEvidence(
                "strategic_value",
                label_key="squad_intelligence.evidence.strategic_value",
                value=context.strategic_value.value,
            ),
        )
        return (RecommendedRole.KEY_STARTER, self.priority, evidence)


class PrimaryTraineeRule(RoleRule):
    rule_id = "role.primary_trainee"
    priority = 90

    def evaluate(self, context):
        if context.training_potential not in (
            TrainingPotential.VERY_HIGH,
            TrainingPotential.HIGH,
        ):
            return None
        if context.training_fit != TrainingFit.EXCELLENT:
            return None
        player = context.player_context
        priority = player.training.priority
        if priority not in _REQUIRED_PRIORITIES:
            return None
        evidence = (
            IntelligenceEvidence(
                "training_potential",
                label_key="squad_intelligence.evidence.training_potential",
                value=context.training_potential.value,
            ),
            IntelligenceEvidence(
                "training_fit",
                label_key="squad_intelligence.evidence.training_fit",
                value=context.training_fit.value,
            ),
            IntelligenceEvidence(
                "priority",
                label_key="squad_intelligence.evidence.priority",
                value=priority,
            ),
        )
        return (RecommendedRole.PRIMARY_TRAINEE, self.priority, evidence)


class StarterRule(RoleRule):
    rule_id = "role.starter"
    priority = 80

    def evaluate(self, context):
        if context.current_performance not in (
            CurrentPerformance.HIGH,
            CurrentPerformance.VERY_HIGH,
        ):
            return None
        evidence = (
            IntelligenceEvidence(
                "current_performance",
                label_key="squad_intelligence.evidence.current_performance",
                value=context.current_performance.value,
            ),
        )
        return (RecommendedRole.STARTER, self.priority, evidence)


class TacticalSpecialistRule(RoleRule):
    rule_id = "role.tactical_specialist"
    priority = 75

    def evaluate(self, context):
        speciality = getattr(context.player_context.player, "speciality", "") or ""
        speciality = speciality.strip()
        if not speciality or speciality.lower() in ("none", "unknown", "no especialidad"):
            return None
        if context.current_performance in (
            CurrentPerformance.VERY_LOW,
            CurrentPerformance.INSUFFICIENT_DATA,
        ):
            return None
        evidence = (
            IntelligenceEvidence(
                "speciality",
                label_key="squad_intelligence.evidence.speciality",
                value=speciality,
            ),
        )
        return (RecommendedRole.TACTICAL_SPECIALIST, self.priority, evidence)


class SecondaryTraineeRule(RoleRule):
    rule_id = "role.secondary_trainee"
    priority = 70

    def evaluate(self, context):
        if context.training_fit not in (TrainingFit.COMPATIBLE, TrainingFit.PARTIAL):
            return None
        if context.training_potential not in (
            TrainingPotential.MEDIUM,
            TrainingPotential.HIGH,
            TrainingPotential.VERY_HIGH,
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
        return (RecommendedRole.SECONDARY_TRAINEE, self.priority, evidence)


class VeteranMentorRule(RoleRule):
    rule_id = "role.veteran_mentor"
    priority = 65

    def evaluate(self, context):
        player = context.player_context.player
        age = getattr(player, "age", None)
        if age is None or age < VETERAN_AGE_THRESHOLD:
            return None
        leadership = getattr(player, "leadership", None) or 0
        experience = getattr(player, "experience", None) or 0
        if leadership < 5 and experience < 5:
            return None
        if context.current_performance in (
            CurrentPerformance.VERY_LOW,
            CurrentPerformance.INSUFFICIENT_DATA,
        ):
            return None
        evidence = (
            IntelligenceEvidence(
                "age", label_key="squad_intelligence.evidence.age", value=age
            ),
            IntelligenceEvidence(
                "leadership_or_experience",
                label_key="squad_intelligence.evidence.leadership_or_experience",
                value=max(leadership, experience),
            ),
        )
        return (RecommendedRole.VETERAN_MENTOR, self.priority, evidence)


class DevelopmentProjectRule(RoleRule):
    rule_id = "role.development_project"
    priority = 55

    def evaluate(self, context):
        player = context.player_context.player
        age = getattr(player, "age", None)
        if age is None or age > 23:
            return None
        if context.training_potential not in (
            TrainingPotential.HIGH,
            TrainingPotential.VERY_HIGH,
            TrainingPotential.MEDIUM,
        ):
            return None
        if context.training_fit == TrainingFit.EXCELLENT:
            return None  # that's PrimaryTraineeRule's territory
        if context.current_performance not in (
            CurrentPerformance.LOW,
            CurrentPerformance.MEDIUM,
            CurrentPerformance.INSUFFICIENT_DATA,
        ):
            return None
        evidence = (
            IntelligenceEvidence(
                "age", label_key="squad_intelligence.evidence.age", value=age
            ),
            IntelligenceEvidence(
                "training_potential",
                label_key="squad_intelligence.evidence.training_potential",
                value=context.training_potential.value,
            ),
        )
        return (RecommendedRole.DEVELOPMENT_PROJECT, self.priority, evidence)


class UsefulRotationRule(RoleRule):
    rule_id = "role.useful_rotation"
    priority = 50

    def evaluate(self, context):
        if context.current_performance != CurrentPerformance.MEDIUM:
            return None
        if context.strategic_value in (StrategicValue.LOW, StrategicValue.INSUFFICIENT_DATA):
            return None
        evidence = (
            IntelligenceEvidence(
                "current_performance",
                label_key="squad_intelligence.evidence.current_performance",
                value=context.current_performance.value,
            ),
        )
        return (RecommendedRole.USEFUL_ROTATION, self.priority, evidence)


class TransferCandidateRule(RoleRule):
    rule_id = "role.transfer_candidate"
    priority = 40

    def evaluate(self, context):
        if context.training_potential not in (
            TrainingPotential.LOW,
            TrainingPotential.EXHAUSTED,
            TrainingPotential.NOT_APPLICABLE,
        ):
            return None
        if context.strategic_value != StrategicValue.LOW:
            return None
        if context.salary_efficiency not in (
            SalaryEfficiency.LOW,
            SalaryEfficiency.VERY_LOW,
        ):
            return None
        evidence = (
            IntelligenceEvidence(
                "strategic_value",
                label_key="squad_intelligence.evidence.strategic_value",
                value=context.strategic_value.value,
            ),
            IntelligenceEvidence(
                "salary_efficiency",
                label_key="squad_intelligence.evidence.salary_efficiency",
                value=context.salary_efficiency.value,
            ),
        )
        return (RecommendedRole.TRANSFER_CANDIDATE, self.priority, evidence)


class ReplaceableRule(RoleRule):
    rule_id = "role.replaceable"
    priority = 30

    def evaluate(self, context):
        if context.current_performance not in (
            CurrentPerformance.LOW,
            CurrentPerformance.VERY_LOW,
        ):
            return None
        if context.strategic_value != StrategicValue.LOW:
            return None
        evidence = (
            IntelligenceEvidence(
                "current_performance",
                label_key="squad_intelligence.evidence.current_performance",
                value=context.current_performance.value,
            ),
            IntelligenceEvidence(
                "strategic_value",
                label_key="squad_intelligence.evidence.strategic_value",
                value=context.strategic_value.value,
            ),
        )
        return (RecommendedRole.REPLACEABLE, self.priority, evidence)


class DepthPlayerRule(RoleRule):
    """The guaranteed fallback: every player must receive exactly one
    primary role, and this always matches, at the lowest priority."""

    rule_id = "role.depth_player"
    priority = 1

    def evaluate(self, context):
        evidence = (
            IntelligenceEvidence(
                "fallback_role",
                label_key="squad_intelligence.evidence.fallback_role",
            ),
        )
        return (RecommendedRole.DEPTH_PLAYER, self.priority, evidence)


def default_role_rules() -> tuple:
    return (
        KeyStarterRule(),
        PrimaryTraineeRule(),
        StarterRule(),
        TacticalSpecialistRule(),
        SecondaryTraineeRule(),
        VeteranMentorRule(),
        DevelopmentProjectRule(),
        UsefulRotationRule(),
        TransferCandidateRule(),
        ReplaceableRule(),
        DepthPlayerRule(),
    )
