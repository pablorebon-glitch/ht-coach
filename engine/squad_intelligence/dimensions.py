from __future__ import annotations

from engine.squad_intelligence.enums import (
    CurrentPerformance,
    SalaryEfficiency,
    StrategicValue,
    TrainingFit,
    TrainingPotential,
)
from engine.squad_intelligence.evidence import IntelligenceEvidence
from engine.squad_intelligence.scoring import (
    DEFAULT_THRESHOLDS,
    bucket_five_tier,
    match_value,
    replacement_difficulty,
    salary_efficiency_value,
    strategic_value_score,
    training_fit_value,
    training_value,
)

_PERFORMANCE_TIERS = {
    4: CurrentPerformance.VERY_HIGH,
    3: CurrentPerformance.HIGH,
    2: CurrentPerformance.MEDIUM,
    1: CurrentPerformance.LOW,
    0: CurrentPerformance.VERY_LOW,
}
_POTENTIAL_TIERS = {
    4: TrainingPotential.VERY_HIGH,
    3: TrainingPotential.HIGH,
    2: TrainingPotential.MEDIUM,
    1: TrainingPotential.LOW,
    0: TrainingPotential.LOW,
}
_SALARY_TIERS = {
    4: SalaryEfficiency.EXCELLENT,
    3: SalaryEfficiency.GOOD,
    2: SalaryEfficiency.ACCEPTABLE,
    1: SalaryEfficiency.LOW,
    0: SalaryEfficiency.VERY_LOW,
}
_STRATEGIC_TIERS = {
    4: StrategicValue.KEY,
    3: StrategicValue.HIGH,
    2: StrategicValue.MEDIUM,
    1: StrategicValue.LOW,
    0: StrategicValue.LOW,
}

# Hattrick's form and stamina scales run 1-8; these bands are a documented,
# configurable assumption, not an official Hattrick definition.
FORM_LOW = 3
FORM_HIGH = 6
STAMINA_LOW = 3


def classify_current_performance(context, thresholds=None):
    thresholds = thresholds or DEFAULT_THRESHOLDS
    position = context.position
    score = match_value(position)
    evidence = []

    if score is None:
        evidence.append(
            IntelligenceEvidence(
                "no_positional_score", label_key="squad_intelligence.evidence.no_positional_score"
            )
        )
        return CurrentPerformance.INSUFFICIENT_DATA, tuple(evidence)

    evidence.append(
        IntelligenceEvidence(
            "best_position",
            label_key="squad_intelligence.evidence.best_position",
            value=position.best_position,
        )
    )
    evidence.append(
        IntelligenceEvidence(
            "squad_rank",
            label_key="squad_intelligence.evidence.squad_rank",
            value=f"{position.rank_in_best_position}/{position.candidates_in_best_position}",
        )
    )
    if position.alternative_positions:
        evidence.append(
            IntelligenceEvidence(
                "alternative_positions",
                label_key="squad_intelligence.evidence.alternative_positions",
                value=", ".join(position.alternative_positions),
            )
        )

    tier = bucket_five_tier(score, thresholds)

    player = context.player
    form = getattr(player, "form", None)
    stamina = getattr(player, "stamina", None)
    if form is not None and form <= FORM_LOW and tier > 0:
        tier -= 1
        evidence.append(
            IntelligenceEvidence(
                "low_form", label_key="squad_intelligence.evidence.low_form", value=form
            )
        )
    elif form is not None and form >= FORM_HIGH and tier < 4:
        tier += 1
        evidence.append(
            IntelligenceEvidence(
                "high_form", label_key="squad_intelligence.evidence.high_form", value=form
            )
        )
    if stamina is not None and stamina <= STAMINA_LOW:
        evidence.append(
            IntelligenceEvidence(
                "low_stamina", label_key="squad_intelligence.evidence.low_stamina", value=stamina
            )
        )

    if not context.is_available:
        evidence.append(
            IntelligenceEvidence(
                "unavailable",
                label_key="squad_intelligence.evidence.unavailable",
                value=context.availability_label,
            )
        )
        tier = min(tier, 1)

    return _PERFORMANCE_TIERS[tier], tuple(evidence)


def classify_training_potential(context, thresholds=None):
    thresholds = thresholds or DEFAULT_THRESHOLDS
    training = context.training
    age = getattr(context.player, "age", None)
    evidence = []

    if not training.has_active_training:
        evidence.append(
            IntelligenceEvidence(
                "no_active_training",
                label_key="squad_intelligence.evidence.no_active_training",
            )
        )
        return TrainingPotential.INSUFFICIENT_DATA, tuple(evidence)

    fit = training_fit_value(training)
    if fit == 0.0:
        evidence.append(
            IntelligenceEvidence(
                "position_not_trained",
                label_key="squad_intelligence.evidence.position_not_trained",
                value=training.effect_for_best_position,
            )
        )
        return TrainingPotential.NOT_APPLICABLE, tuple(evidence)

    if age is None:
        evidence.append(
            IntelligenceEvidence(
                "missing_age", label_key="squad_intelligence.evidence.missing_age"
            )
        )
        return TrainingPotential.INSUFFICIENT_DATA, tuple(evidence)

    score = training_value(training, age)
    evidence.append(
        IntelligenceEvidence(
            "training_effect",
            label_key="squad_intelligence.evidence.training_effect",
            value=training.effect_for_best_position,
        )
    )
    evidence.append(
        IntelligenceEvidence("age", label_key="squad_intelligence.evidence.age", value=age)
    )
    if training.priority:
        evidence.append(
            IntelligenceEvidence(
                "priority",
                label_key="squad_intelligence.evidence.priority",
                value=training.priority,
            )
        )

    if age > 29 and fit is not None and fit < 1.0:
        # An old player in a non-full slot has effectively no
        # remaining development runway -- exhausted, not merely low.
        return TrainingPotential.EXHAUSTED, tuple(evidence)

    tier = bucket_five_tier(score, thresholds)
    if tier is None:
        return TrainingPotential.INSUFFICIENT_DATA, tuple(evidence)
    return _POTENTIAL_TIERS[tier], tuple(evidence)


def classify_training_fit(context):
    training = context.training
    evidence = []

    if not training.has_active_training:
        return TrainingFit.UNKNOWN, tuple(evidence)

    effect = training.effect_for_best_position
    evidence.append(
        IntelligenceEvidence(
            "training_effect",
            label_key="squad_intelligence.evidence.training_effect",
            value=effect,
        )
    )
    if not effect or effect == "NONE":
        return TrainingFit.NO_TRAINING, tuple(evidence)

    if training.priority and training.priority not in ("", "NO_PRIORITY"):
        evidence.append(
            IntelligenceEvidence(
                "priority",
                label_key="squad_intelligence.evidence.priority",
                value=training.priority,
            )
        )

    if effect == "FULL":
        return TrainingFit.EXCELLENT, tuple(evidence)
    if effect == "REDUCED":
        return TrainingFit.COMPATIBLE, tuple(evidence)
    if effect == "VERY_SMALL":
        if not training.priority or training.priority in ("", "NO_PRIORITY"):
            return TrainingFit.NOT_PRIORITIZED, tuple(evidence)
        return TrainingFit.PARTIAL, tuple(evidence)
    return TrainingFit.UNKNOWN, tuple(evidence)


def classify_salary_efficiency(context, thresholds=None):
    thresholds = thresholds or DEFAULT_THRESHOLDS
    evidence = []
    salary = getattr(context.player, "salary", None)

    if salary is None or context.salary_percentile_in_squad is None:
        evidence.append(
            IntelligenceEvidence(
                "missing_salary", label_key="squad_intelligence.evidence.missing_salary"
            )
        )
        return SalaryEfficiency.INSUFFICIENT_DATA, tuple(evidence)

    match_score = match_value(context.position)
    train_score = training_value(context.training, getattr(context.player, "age", None))
    score = salary_efficiency_value(
        context.salary_percentile_in_squad, match_score, train_score
    )
    evidence.append(
        IntelligenceEvidence(
            "salary", label_key="squad_intelligence.evidence.salary", value=salary
        )
    )
    evidence.append(
        IntelligenceEvidence(
            "salary_percentile",
            label_key="squad_intelligence.evidence.salary_percentile",
            value=round(context.salary_percentile_in_squad * 100),
        )
    )

    tier = bucket_five_tier(score, thresholds)
    if tier is None:
        return SalaryEfficiency.INSUFFICIENT_DATA, tuple(evidence)
    return _SALARY_TIERS[tier], tuple(evidence)


def classify_strategic_value(context, squad_context, thresholds=None):
    thresholds = thresholds or DEFAULT_THRESHOLDS
    evidence = []

    match_score = match_value(context.position)
    train_score = training_value(context.training, getattr(context.player, "age", None))
    replacement_score = replacement_difficulty(
        context.position, squad_context, context.position.best_position
    )
    salary_score = salary_efficiency_value(
        context.salary_percentile_in_squad, match_score, train_score
    )

    if all(value is None for value in (match_score, train_score, replacement_score, salary_score)):
        evidence.append(
            IntelligenceEvidence(
                "insufficient_evidence",
                label_key="squad_intelligence.evidence.insufficient_strategic_evidence",
            )
        )
        return StrategicValue.INSUFFICIENT_DATA, tuple(evidence)

    if replacement_score is not None:
        evidence.append(
            IntelligenceEvidence(
                "replacement_difficulty",
                label_key="squad_intelligence.evidence.replacement_difficulty",
                value=round(replacement_score, 2),
            )
        )
    if squad_context is not None and context.position.best_position:
        evidence.append(
            IntelligenceEvidence(
                "positional_depth",
                label_key="squad_intelligence.evidence.positional_depth",
                value=squad_context.depth_at(context.position.best_position),
            )
        )

    score = strategic_value_score(match_score, train_score, replacement_score, salary_score)
    tier = bucket_five_tier(score, thresholds)
    if tier is None:
        return StrategicValue.INSUFFICIENT_DATA, tuple(evidence)
    return _STRATEGIC_TIERS[tier], tuple(evidence)
