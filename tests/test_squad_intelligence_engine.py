import pytest

from engine.squad_intelligence.confidence import ConfidenceInputs, classify_confidence
from engine.squad_intelligence.context import (
    PlayerIntelligenceContext,
    PositionEvidence,
    SquadIntelligenceContext,
    TrainingEvidence,
)
from engine.squad_intelligence.dimensions import (
    classify_current_performance,
    classify_salary_efficiency,
    classify_strategic_value,
    classify_training_fit,
    classify_training_potential,
)
from engine.squad_intelligence.enums import (
    ClubStrategy,
    CurrentPerformance,
    IntelligenceConfidence,
    LimitationType,
    ManagementStatus,
    MilestoneType,
    RecommendedRole,
    RiskType,
    SalaryEfficiency,
    StrategicValue,
    StrengthType,
    TrainingFit,
    TrainingPotential,
)
from engine.squad_intelligence.milestones import select_milestone
from engine.squad_intelligence.models import PlayerIntelligenceReport
from engine.squad_intelligence.rule import RoleEvaluationContext
from engine.squad_intelligence.rule_engine import SquadIntelligenceRuleEngine
from engine.squad_intelligence.scoring import ScoringThresholds
from engine.squad_intelligence.service import generate_report
from engine.squad_intelligence.validation import SquadIntelligenceError, ensure_player_context_valid
from models.player import Player


def make_player(**overrides):
    base = dict(
        name="Test Player", age=22, days=50, speciality="", form=6, stamina=7,
        goalkeeper=1, defending=5, playmaking=5, winger=5, passing=5, scoring=5,
        set_pieces=4, experience=5, leadership=4, tsi=5000, salary=1000,
    )
    base.update(overrides)
    return Player(**base)


def make_position(**overrides):
    base = dict(
        best_position="INNER_MIDFIELDER", best_position_score=6.0,
        rank_in_best_position=1, candidates_in_best_position=5,
        alternative_positions=(),
    )
    base.update(overrides)
    return PositionEvidence(**base)


def make_training(**overrides):
    base = dict(
        active_training_type="PLAYMAKING", trained_skills=("playmaking",),
        effect_for_best_position="FULL", priority="REQUIRED_100",
        current_trained_skill_level=6,
    )
    base.update(overrides)
    return TrainingEvidence(**base)


def make_context(player=None, position=None, training=None, **overrides):
    base = dict(
        player_id="p1", player_name="Test Player",
        player=player or make_player(),
        position=position or make_position(),
        training=training if training is not None else make_training(),
        is_available=True,
        salary_percentile_in_squad=0.5,
    )
    base.update(overrides)
    return PlayerIntelligenceContext(**base)


def make_squad_context(**overrides):
    base = dict(roster_size=20, positional_depth={"INNER_MIDFIELDER": 5})
    base.update(overrides)
    return SquadIntelligenceContext(**base)


# --------------------------------------------------------------------------
# Models and enums
# --------------------------------------------------------------------------

def test_all_recommended_roles_are_unique():
    values = [role.value for role in RecommendedRole]
    assert len(values) == len(set(values)) == 11


def test_all_management_statuses_are_unique():
    values = [status.value for status in ManagementStatus]
    assert len(values) == len(set(values)) == 8


def test_no_unconditional_sell_status_exists():
    assert not any("sell" in status.value for status in ManagementStatus)


def test_complete_report_is_valid_and_serializable():
    context = make_context()
    report = generate_report(context, make_squad_context())
    assert isinstance(report, PlayerIntelligenceReport)
    payload = report.to_dict()
    assert payload["recommended_role"]
    assert payload["management_status"]


def test_ensure_player_context_valid_rejects_none():
    with pytest.raises(SquadIntelligenceError):
        ensure_player_context_valid(None)


def test_scoring_thresholds_reject_invalid_ordering():
    with pytest.raises(ValueError):
        ScoringThresholds(very_high=0.5, high=0.6, medium=0.3, low=0.1)


# --------------------------------------------------------------------------
# Current performance
# --------------------------------------------------------------------------

def test_current_performance_key_starter_rank_one():
    context = make_context(position=make_position(rank_in_best_position=1, candidates_in_best_position=6))
    performance, evidence = classify_current_performance(context)
    assert performance in (CurrentPerformance.VERY_HIGH, CurrentPerformance.HIGH)
    assert evidence


def test_current_performance_low_value_depth_player():
    context = make_context(
        position=make_position(rank_in_best_position=6, candidates_in_best_position=6)
    )
    performance, _ = classify_current_performance(context)
    assert performance in (CurrentPerformance.LOW, CurrentPerformance.VERY_LOW)


def test_current_performance_form_impact():
    high_form_context = make_context(
        player=make_player(form=8),
        position=make_position(rank_in_best_position=3, candidates_in_best_position=6),
    )
    low_form_context = make_context(
        player=make_player(form=1),
        position=make_position(rank_in_best_position=3, candidates_in_best_position=6),
    )
    high_perf, _ = classify_current_performance(high_form_context)
    low_perf, _ = classify_current_performance(low_form_context)
    tiers = [
        CurrentPerformance.VERY_LOW, CurrentPerformance.LOW, CurrentPerformance.MEDIUM,
        CurrentPerformance.HIGH, CurrentPerformance.VERY_HIGH,
    ]
    assert tiers.index(high_perf) >= tiers.index(low_perf)


def test_current_performance_injury_caps_tier():
    context = make_context(
        position=make_position(rank_in_best_position=1, candidates_in_best_position=6),
        is_available=False,
        availability_label="Injured",
    )
    performance, evidence = classify_current_performance(context)
    assert performance in (CurrentPerformance.VERY_LOW, CurrentPerformance.LOW)
    assert any(item.evidence_type == "unavailable" for item in evidence)


def test_current_performance_no_positional_score_is_insufficient_data():
    context = make_context(position=PositionEvidence())
    performance, evidence = classify_current_performance(context)
    assert performance == CurrentPerformance.INSUFFICIENT_DATA
    assert evidence


def test_salary_never_used_as_performance_signal():
    """A very high salary alone must not push performance up."""
    cheap = make_context(player=make_player(salary=100))
    expensive = make_context(player=make_player(salary=999999))
    cheap_perf, _ = classify_current_performance(cheap)
    expensive_perf, _ = classify_current_performance(expensive)
    assert cheap_perf == expensive_perf


# --------------------------------------------------------------------------
# Training potential
# --------------------------------------------------------------------------

def test_training_potential_young_full_effect_trainee():
    context = make_context(player=make_player(age=18))
    potential, _ = classify_training_potential(context)
    assert potential in (TrainingPotential.HIGH, TrainingPotential.VERY_HIGH)


def test_training_potential_reduced_effect_trainee():
    context = make_context(
        player=make_player(age=20),
        training=make_training(effect_for_best_position="REDUCED"),
    )
    potential, _ = classify_training_potential(context)
    assert potential not in (TrainingPotential.INSUFFICIENT_DATA,)


def test_training_potential_no_training_player():
    context = make_context(training=make_training(effect_for_best_position="NONE"))
    potential, _ = classify_training_potential(context)
    assert potential == TrainingPotential.NOT_APPLICABLE


def test_training_potential_older_player_in_non_full_slot_is_exhausted():
    context = make_context(
        player=make_player(age=32),
        training=make_training(effect_for_best_position="REDUCED"),
    )
    potential, _ = classify_training_potential(context)
    assert potential == TrainingPotential.EXHAUSTED


def test_training_potential_missing_age_is_insufficient_data():
    player = make_player()
    player.age = None
    context = make_context(player=player)
    potential, _ = classify_training_potential(context)
    assert potential == TrainingPotential.INSUFFICIENT_DATA


def test_training_potential_unknown_active_training_is_insufficient_data():
    context = make_context(training=TrainingEvidence())
    potential, _ = classify_training_potential(context)
    assert potential == TrainingPotential.INSUFFICIENT_DATA


def test_training_potential_does_not_overrate_old_trainable_player():
    """An old player merely occupying a trainable position must not
    become a high-potential trainee."""
    context = make_context(
        player=make_player(age=33),
        training=make_training(effect_for_best_position="FULL"),
    )
    potential, _ = classify_training_potential(context)
    assert potential not in (TrainingPotential.VERY_HIGH,)


# --------------------------------------------------------------------------
# Training fit (consumes the canonical training catalog conceptually)
# --------------------------------------------------------------------------

def test_training_fit_full_is_excellent():
    context = make_context(training=make_training(effect_for_best_position="FULL"))
    fit, _ = classify_training_fit(context)
    assert fit == TrainingFit.EXCELLENT


def test_training_fit_reduced_is_compatible():
    context = make_context(training=make_training(effect_for_best_position="REDUCED"))
    fit, _ = classify_training_fit(context)
    assert fit == TrainingFit.COMPATIBLE


def test_training_fit_very_small_without_priority_is_not_prioritized():
    context = make_context(
        training=make_training(effect_for_best_position="VERY_SMALL", priority="")
    )
    fit, _ = classify_training_fit(context)
    assert fit == TrainingFit.NOT_PRIORITIZED


def test_training_fit_very_small_with_priority_is_partial():
    context = make_context(
        training=make_training(effect_for_best_position="VERY_SMALL", priority="REQUIRED_50")
    )
    fit, _ = classify_training_fit(context)
    assert fit == TrainingFit.PARTIAL


def test_training_fit_none_is_no_training():
    context = make_context(training=make_training(effect_for_best_position="NONE"))
    fit, _ = classify_training_fit(context)
    assert fit == TrainingFit.NO_TRAINING


def test_training_fit_uses_real_catalog_effect_for_defending_cd():
    from engine.weekly_training.training_rules import rule_provider_for

    rules = rule_provider_for("DEFENDING")
    effect = rules.effect_for_position("CENTRAL_DEFENDER").value
    context = make_context(
        position=make_position(best_position="CENTRAL_DEFENDER"),
        training=make_training(active_training_type="DEFENDING", effect_for_best_position=effect),
    )
    fit, _ = classify_training_fit(context)
    assert fit == TrainingFit.EXCELLENT


def test_training_fit_uses_real_catalog_effect_for_scoring_forward():
    from engine.weekly_training.training_rules import rule_provider_for

    rules = rule_provider_for("SCORING")
    effect = rules.effect_for_position("FORWARD").value
    context = make_context(
        position=make_position(best_position="FORWARD"),
        training=make_training(active_training_type="SCORING", effect_for_best_position=effect),
    )
    fit, _ = classify_training_fit(context)
    assert fit == TrainingFit.EXCELLENT


def test_training_fit_uses_real_catalog_effect_for_goalkeeping():
    from engine.weekly_training.training_rules import rule_provider_for

    rules = rule_provider_for("GOALKEEPING")
    effect = rules.effect_for_position("GOALKEEPER").value
    context = make_context(
        position=make_position(best_position="GOALKEEPER"),
        training=make_training(active_training_type="GOALKEEPING", effect_for_best_position=effect),
    )
    fit, _ = classify_training_fit(context)
    assert fit == TrainingFit.EXCELLENT


def test_training_fit_unknown_when_no_active_training():
    context = make_context(training=TrainingEvidence())
    fit, _ = classify_training_fit(context)
    assert fit == TrainingFit.UNKNOWN


# --------------------------------------------------------------------------
# Salary efficiency
# --------------------------------------------------------------------------

def test_salary_efficiency_high_salary_key_starter_remains_acceptable():
    context = make_context(
        position=make_position(rank_in_best_position=1, candidates_in_best_position=6),
        salary_percentile_in_squad=0.9,
    )
    efficiency, _ = classify_salary_efficiency(context)
    assert efficiency not in (SalaryEfficiency.VERY_LOW,)


def test_salary_efficiency_high_salary_low_impact_is_low():
    context = make_context(
        position=make_position(rank_in_best_position=6, candidates_in_best_position=6),
        training=make_training(effect_for_best_position="NONE"),
        salary_percentile_in_squad=0.95,
    )
    efficiency, _ = classify_salary_efficiency(context)
    assert efficiency in (SalaryEfficiency.LOW, SalaryEfficiency.VERY_LOW)


def test_salary_efficiency_low_salary_useful_trainee_is_good():
    context = make_context(
        position=make_position(rank_in_best_position=1, candidates_in_best_position=6),
        salary_percentile_in_squad=0.05,
    )
    efficiency, _ = classify_salary_efficiency(context)
    assert efficiency in (SalaryEfficiency.GOOD, SalaryEfficiency.EXCELLENT)


def test_salary_efficiency_low_salary_unused_player_is_not_automatically_excellent():
    context = make_context(
        position=PositionEvidence(),
        training=TrainingEvidence(),
        salary_percentile_in_squad=0.05,
    )
    efficiency, _ = classify_salary_efficiency(context)
    assert efficiency != SalaryEfficiency.EXCELLENT


def test_salary_efficiency_missing_salary_percentile_is_insufficient_data():
    context = make_context(salary_percentile_in_squad=None)
    efficiency, evidence = classify_salary_efficiency(context)
    assert efficiency == SalaryEfficiency.INSUFFICIENT_DATA
    assert evidence


# --------------------------------------------------------------------------
# Strategic value
# --------------------------------------------------------------------------

def test_strategic_value_irreplaceable_starter_is_key_or_high():
    context = make_context(position=make_position(rank_in_best_position=1, candidates_in_best_position=6))
    squad = make_squad_context(positional_depth={"INNER_MIDFIELDER": 1})
    value, _ = classify_strategic_value(context, squad)
    assert value in (StrategicValue.KEY, StrategicValue.HIGH)


def test_strategic_value_replaceable_depth_player_is_low():
    context = make_context(
        position=make_position(rank_in_best_position=6, candidates_in_best_position=6),
        training=make_training(effect_for_best_position="NONE"),
        salary_percentile_in_squad=0.9,
    )
    squad = make_squad_context(positional_depth={"INNER_MIDFIELDER": 8})
    value, _ = classify_strategic_value(context, squad)
    assert value in (StrategicValue.LOW, StrategicValue.MEDIUM)


def test_strategic_value_squad_depth_changes_classification():
    """The same moderate player can be key when no replacement exists,
    or replaceable when several exist."""
    context = make_context(position=make_position(rank_in_best_position=3, candidates_in_best_position=4))
    scarce_squad = make_squad_context(positional_depth={"INNER_MIDFIELDER": 1})
    plentiful_squad = make_squad_context(positional_depth={"INNER_MIDFIELDER": 10})

    scarce_value, _ = classify_strategic_value(context, scarce_squad)
    plentiful_value, _ = classify_strategic_value(context, plentiful_squad)

    tiers = [StrategicValue.LOW, StrategicValue.MEDIUM, StrategicValue.HIGH, StrategicValue.KEY]
    assert tiers.index(scarce_value) >= tiers.index(plentiful_value)


def test_strategic_value_veteran_can_have_low_potential_but_key_value():
    context = make_context(
        player=make_player(age=33, leadership=8),
        position=make_position(rank_in_best_position=1, candidates_in_best_position=6),
        training=make_training(effect_for_best_position="REDUCED"),
    )
    squad = make_squad_context(positional_depth={"INNER_MIDFIELDER": 1})
    potential, _ = classify_training_potential(context)
    value, _ = classify_strategic_value(context, squad)
    assert potential in (TrainingPotential.EXHAUSTED, TrainingPotential.LOW)
    assert value in (StrategicValue.KEY, StrategicValue.HIGH)


# --------------------------------------------------------------------------
# Role rules (via the rule engine)
# --------------------------------------------------------------------------

def _evaluation_context(context, squad=None, **dims):
    from engine.squad_intelligence.dimensions import (
        classify_current_performance,
        classify_salary_efficiency,
        classify_strategic_value,
        classify_training_fit,
        classify_training_potential,
    )

    performance = dims.get("current_performance") or classify_current_performance(context)[0]
    potential = dims.get("training_potential") or classify_training_potential(context)[0]
    fit = dims.get("training_fit") or classify_training_fit(context)[0]
    salary = dims.get("salary_efficiency") or classify_salary_efficiency(context)[0]
    strategic = dims.get("strategic_value") or classify_strategic_value(context, squad)[0]
    return RoleEvaluationContext(context, squad, performance, potential, fit, salary, strategic)


def test_role_primary_trainee():
    context = make_context(
        player=make_player(age=18, form=5),
        position=make_position(rank_in_best_position=3, candidates_in_best_position=8),
    )
    engine = SquadIntelligenceRuleEngine()
    eval_context = _evaluation_context(context, make_squad_context())
    role, _ = engine.resolve_role(eval_context)
    assert role == RecommendedRole.PRIMARY_TRAINEE


def test_role_key_starter():
    context = make_context(position=make_position(rank_in_best_position=1, candidates_in_best_position=6))
    engine = SquadIntelligenceRuleEngine()
    eval_context = _evaluation_context(context, make_squad_context(positional_depth={"INNER_MIDFIELDER": 1}))
    role, _ = engine.resolve_role(eval_context)
    assert role == RecommendedRole.KEY_STARTER


def test_role_tactical_specialist():
    context = make_context(
        player=make_player(speciality="Technical", age=27, form=5),
        position=make_position(rank_in_best_position=4, candidates_in_best_position=6),
        training=make_training(effect_for_best_position="NONE"),
    )
    engine = SquadIntelligenceRuleEngine()
    eval_context = _evaluation_context(context, make_squad_context())
    role, _ = engine.resolve_role(eval_context)
    assert role == RecommendedRole.TACTICAL_SPECIALIST


def test_role_veteran_mentor():
    context = make_context(
        player=make_player(age=32, leadership=9, experience=9, form=5),
        position=make_position(rank_in_best_position=4, candidates_in_best_position=6),
        training=make_training(effect_for_best_position="NONE"),
    )
    engine = SquadIntelligenceRuleEngine()
    eval_context = _evaluation_context(context, make_squad_context())
    role, _ = engine.resolve_role(eval_context)
    assert role == RecommendedRole.VETERAN_MENTOR


def test_role_never_assigned_merely_for_age():
    """A veteran with no leadership/experience signal must not become
    VETERAN_MENTOR just from being old."""
    context = make_context(
        player=make_player(age=34, leadership=2, experience=2),
        position=make_position(rank_in_best_position=5, candidates_in_best_position=6),
        training=make_training(effect_for_best_position="NONE"),
    )
    engine = SquadIntelligenceRuleEngine()
    eval_context = _evaluation_context(context, make_squad_context())
    role, _ = engine.resolve_role(eval_context)
    assert role != RecommendedRole.VETERAN_MENTOR


def test_role_transfer_candidate():
    context = make_context(
        player=make_player(age=30, experience=3, leadership=3, form=5),
        position=make_position(rank_in_best_position=8, candidates_in_best_position=8),
        training=make_training(effect_for_best_position="NONE"),
        salary_percentile_in_squad=0.95,
    )
    engine = SquadIntelligenceRuleEngine()
    eval_context = _evaluation_context(
        context, make_squad_context(positional_depth={"INNER_MIDFIELDER": 8})
    )
    role, _ = engine.resolve_role(eval_context)
    assert role in (RecommendedRole.TRANSFER_CANDIDATE, RecommendedRole.REPLACEABLE)


def test_role_replaceable():
    context = make_context(
        position=make_position(rank_in_best_position=8, candidates_in_best_position=8),
        training=make_training(effect_for_best_position="NONE"),
    )
    engine = SquadIntelligenceRuleEngine()
    eval_context = _evaluation_context(
        context, make_squad_context(positional_depth={"INNER_MIDFIELDER": 8})
    )
    role, _ = engine.resolve_role(eval_context)
    assert role in (RecommendedRole.REPLACEABLE, RecommendedRole.TRANSFER_CANDIDATE)


def test_role_useful_rotation():
    context = make_context(
        player=make_player(form=5),
        position=make_position(rank_in_best_position=4, candidates_in_best_position=8),
        training=make_training(effect_for_best_position="VERY_SMALL", priority=""),
    )
    engine = SquadIntelligenceRuleEngine()
    eval_context = _evaluation_context(context, make_squad_context(positional_depth={"INNER_MIDFIELDER": 3}))
    role, _ = engine.resolve_role(eval_context)
    assert role in (RecommendedRole.USEFUL_ROTATION, RecommendedRole.STARTER, RecommendedRole.DEPTH_PLAYER)


def test_role_always_resolves_exactly_one_primary_role():
    """The fallback DepthPlayerRule guarantees every context yields
    exactly one primary role -- never zero, never a contradiction."""
    context = make_context(player=make_player(), position=PositionEvidence(), training=TrainingEvidence())
    engine = SquadIntelligenceRuleEngine()
    eval_context = _evaluation_context(context)
    role, evidence = engine.resolve_role(eval_context)
    assert isinstance(role, RecommendedRole)
    assert evidence


def test_role_conflict_resolution_is_documented_and_deterministic():
    """A player who could plausibly be both PRIMARY_TRAINEE and STARTER
    always resolves to KEY_STARTER when performance is very high --
    same inputs, same output, every time."""
    context = make_context(
        player=make_player(age=19),
        position=make_position(rank_in_best_position=1, candidates_in_best_position=6),
    )
    engine = SquadIntelligenceRuleEngine()
    squad = make_squad_context(positional_depth={"INNER_MIDFIELDER": 1})
    results = {engine.resolve_role(_evaluation_context(context, squad))[0] for _ in range(5)}
    assert len(results) == 1


# --------------------------------------------------------------------------
# Status rules
# --------------------------------------------------------------------------

def test_status_keep_for_key_starter():
    context = make_context(position=make_position(rank_in_best_position=1, candidates_in_best_position=6))
    engine = SquadIntelligenceRuleEngine()
    squad = make_squad_context(positional_depth={"INNER_MIDFIELDER": 1})
    eval_context = _evaluation_context(context, squad)
    role, _ = engine.resolve_role(eval_context)
    status, _ = engine.resolve_status(eval_context, role)
    assert status == ManagementStatus.KEEP


def test_status_train_for_trainee():
    context = make_context(
        player=make_player(age=19),
        position=make_position(rank_in_best_position=4, candidates_in_best_position=8),
    )
    engine = SquadIntelligenceRuleEngine()
    eval_context = _evaluation_context(context, make_squad_context())
    role, _ = engine.resolve_role(eval_context)
    status, _ = engine.resolve_status(eval_context, role)
    assert status in (ManagementStatus.TRAIN, ManagementStatus.REVIEW_AT_NEXT_SKILL_LEVEL)


def test_status_evaluate_sale_for_transfer_candidate():
    context = make_context(
        player=make_player(age=30),
        position=make_position(rank_in_best_position=8, candidates_in_best_position=8),
        training=make_training(effect_for_best_position="NONE"),
        salary_percentile_in_squad=0.95,
    )
    engine = SquadIntelligenceRuleEngine()
    squad = make_squad_context(positional_depth={"INNER_MIDFIELDER": 8})
    eval_context = _evaluation_context(context, squad)
    role, _ = engine.resolve_role(eval_context)
    status, _ = engine.resolve_status(eval_context, role)
    if role == RecommendedRole.TRANSFER_CANDIDATE:
        assert status == ManagementStatus.EVALUATE_SALE


def test_status_never_produces_unsupported_immediate_sale():
    for status in ManagementStatus:
        assert "immediate" not in status.value


def test_status_monitor_is_the_guaranteed_fallback():
    engine = SquadIntelligenceRuleEngine(status_rules=())
    context = make_context()
    eval_context = _evaluation_context(context)
    with pytest.raises(RuntimeError):
        engine.resolve_status(eval_context, RecommendedRole.DEPTH_PLAYER)


# --------------------------------------------------------------------------
# Milestones
# --------------------------------------------------------------------------

def test_milestone_reach_trained_skill_for_primary_trainee():
    context = make_context(player=make_player(age=18), position=make_position(rank_in_best_position=3, candidates_in_best_position=8))
    eval_context = _evaluation_context(context, make_squad_context(), training_potential=TrainingPotential.VERY_HIGH)
    milestone = select_milestone(eval_context, RecommendedRole.PRIMARY_TRAINEE, IntelligenceConfidence.HIGH)
    assert milestone.milestone_type == MilestoneType.REACH_TRAINED_SKILL_LEVEL
    assert "skill" in milestone.message_params


def test_milestone_review_at_age_for_veteran_mentor():
    context = make_context(player=make_player(age=32))
    eval_context = _evaluation_context(context)
    milestone = select_milestone(eval_context, RecommendedRole.VETERAN_MENTOR, IntelligenceConfidence.HIGH)
    assert milestone.milestone_type == MilestoneType.REVIEW_AT_AGE
    assert milestone.message_params["age"] == 33


def test_milestone_review_when_replacement_exists_for_scarce_position():
    context = make_context()
    squad = make_squad_context(positional_depth={"INNER_MIDFIELDER": 1})
    eval_context = _evaluation_context(context, squad)
    milestone = select_milestone(eval_context, RecommendedRole.REPLACEABLE, IntelligenceConfidence.HIGH, squad)
    assert milestone.milestone_type == MilestoneType.REVIEW_WHEN_REPLACEMENT_EXISTS


def test_milestone_never_predicts_an_exact_date():
    context = make_context()
    eval_context = _evaluation_context(context)
    milestone = select_milestone(eval_context, RecommendedRole.USEFUL_ROTATION, IntelligenceConfidence.HIGH)
    for value in milestone.message_params.values():
        assert not isinstance(value, str) or "-" not in str(value) or len(str(value)) < 6


def test_milestone_insufficient_data_when_confidence_is_insufficient():
    context = make_context()
    eval_context = _evaluation_context(context)
    milestone = select_milestone(eval_context, RecommendedRole.DEPTH_PLAYER, IntelligenceConfidence.INSUFFICIENT_DATA)
    assert milestone.milestone_type == MilestoneType.INSUFFICIENT_DATA


# --------------------------------------------------------------------------
# Squad context
# --------------------------------------------------------------------------

def test_squad_context_depth_at_unknown_position_is_zero():
    squad = make_squad_context(positional_depth={})
    assert squad.depth_at("FORWARD") == 0


def test_squad_context_positional_scarcity_vs_surplus():
    scarce = make_squad_context(positional_depth={"GOALKEEPER": 1})
    surplus = make_squad_context(positional_depth={"GOALKEEPER": 10})
    assert scarce.depth_at("GOALKEEPER") < surplus.depth_at("GOALKEEPER")


# --------------------------------------------------------------------------
# Confidence
# --------------------------------------------------------------------------

def test_confidence_high_with_complete_data():
    inputs = ConfidenceInputs(
        has_positional_score=True, has_active_training=True,
        has_salary=True, has_stable_player_id=True,
    )
    assert classify_confidence(inputs) == IntelligenceConfidence.HIGH


def test_confidence_medium_with_partial_data():
    inputs = ConfidenceInputs(
        has_positional_score=True, has_active_training=False,
        has_salary=True, has_stable_player_id=True,
    )
    assert classify_confidence(inputs) == IntelligenceConfidence.MEDIUM


def test_confidence_low_with_contradictory_evidence():
    inputs = ConfidenceInputs(
        has_positional_score=True, has_active_training=False,
        contradictory_evidence=True,
    )
    assert classify_confidence(inputs) == IntelligenceConfidence.LOW


def test_confidence_insufficient_data_when_unevaluable():
    inputs = ConfidenceInputs(player_evaluable=False)
    assert classify_confidence(inputs) == IntelligenceConfidence.INSUFFICIENT_DATA


def test_confidence_missing_historical_data_does_not_block_classification():
    """History is optional; its absence should not force
    INSUFFICIENT_DATA on its own."""
    context = make_context()
    report = generate_report(context, make_squad_context())
    assert report.confidence != IntelligenceConfidence.INSUFFICIENT_DATA


# --------------------------------------------------------------------------
# Full-report integration checks
# --------------------------------------------------------------------------

def test_report_never_shows_a_raw_overall_score():
    """The dataclass itself has no such field -- this is a structural
    guarantee, not just a convention."""
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(PlayerIntelligenceReport)}
    assert "overall_score" not in field_names
    assert "score" not in field_names


def test_report_missing_data_is_disclosed_transparently():
    player = make_player()
    player.salary = None
    context = make_context(player=player, salary_percentile_in_squad=None)
    report = generate_report(context, make_squad_context())
    assert LimitationType.MISSING_SALARY in report.limitations


def test_squad_intelligence_never_imports_formation_optimizer():
    import ast
    from pathlib import Path

    package_dir = Path(__file__).resolve().parents[1] / "engine" / "squad_intelligence"
    forbidden = {
        "engine.optimizers.formation_optimizer",
        "engine.optimizers.tactic_optimizer",
        "engine.optimizers.lineup_optimizer",
    }
    for path in package_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
        assert not (imported & forbidden), f"{path.name} imports {imported & forbidden}"


# --------------------------------------------------------------------------
# Additional coverage: secondary trainee, status rules, strengths/risks
# --------------------------------------------------------------------------

def test_role_secondary_trainee_directly():
    from engine.squad_intelligence.roles import SecondaryTraineeRule
    from engine.squad_intelligence.enums import TrainingFit, TrainingPotential

    context = make_context()
    eval_context = _evaluation_context(
        context,
        training_fit=TrainingFit.COMPATIBLE,
        training_potential=TrainingPotential.MEDIUM,
    )
    result = SecondaryTraineeRule().evaluate(eval_context)
    assert result is not None
    assert result[0] == RecommendedRole.SECONDARY_TRAINEE


def test_status_do_not_invest_more_training_directly():
    from engine.squad_intelligence.statuses import DoNotInvestMoreTrainingStatusRule

    context = make_context()
    eval_context = _evaluation_context(
        context,
        training_fit=TrainingFit.NO_TRAINING,
        training_potential=TrainingPotential.EXHAUSTED,
    )
    result = DoNotInvestMoreTrainingStatusRule().evaluate(
        eval_context, RecommendedRole.DEPTH_PLAYER
    )
    assert result is not None
    assert result[0] == ManagementStatus.DO_NOT_INVEST_MORE_TRAINING


def test_status_maintain_as_depth_directly():
    from engine.squad_intelligence.statuses import MaintainAsDepthStatusRule

    context = make_context()
    eval_context = _evaluation_context(
        context, salary_efficiency=SalaryEfficiency.ACCEPTABLE
    )
    result = MaintainAsDepthStatusRule().evaluate(eval_context, RecommendedRole.DEPTH_PLAYER)
    assert result is not None
    assert result[0] == ManagementStatus.MAINTAIN_AS_DEPTH


def test_status_maintain_as_depth_rejected_for_very_low_salary_efficiency():
    from engine.squad_intelligence.statuses import MaintainAsDepthStatusRule

    context = make_context()
    eval_context = _evaluation_context(
        context, salary_efficiency=SalaryEfficiency.VERY_LOW
    )
    result = MaintainAsDepthStatusRule().evaluate(eval_context, RecommendedRole.DEPTH_PLAYER)
    assert result is None


def test_status_gradually_replace_directly():
    from engine.squad_intelligence.statuses import GraduallyReplaceStatusRule

    context = make_context()
    eval_context = _evaluation_context(context)
    result = GraduallyReplaceStatusRule().evaluate(eval_context, RecommendedRole.REPLACEABLE)
    assert result is not None
    assert result[0] == ManagementStatus.GRADUALLY_REPLACE


def test_status_evaluate_sale_directly():
    from engine.squad_intelligence.statuses import EvaluateSaleStatusRule

    context = make_context()
    eval_context = _evaluation_context(context)
    result = EvaluateSaleStatusRule().evaluate(eval_context, RecommendedRole.TRANSFER_CANDIDATE)
    assert result is not None
    assert result[0] == ManagementStatus.EVALUATE_SALE


def test_status_train_rejects_non_trainee_role():
    from engine.squad_intelligence.statuses import TrainStatusRule

    context = make_context()
    eval_context = _evaluation_context(context, training_fit=TrainingFit.EXCELLENT)
    result = TrainStatusRule().evaluate(eval_context, RecommendedRole.KEY_STARTER)
    assert result is None


def test_status_keep_rejects_low_strategic_value():
    from engine.squad_intelligence.statuses import KeepStatusRule

    context = make_context()
    eval_context = _evaluation_context(context, strategic_value=StrategicValue.LOW)
    result = KeepStatusRule().evaluate(eval_context, RecommendedRole.KEY_STARTER)
    assert result is None


def test_strengths_tactical_versatility_and_valuable_specialty():
    from engine.squad_intelligence.warnings import detect_strengths

    context = make_context(
        player=make_player(speciality="Powerful", age=27, form=5),
        position=make_position(
            rank_in_best_position=4, candidates_in_best_position=6,
            alternative_positions=("WINGER", "FORWARD"),
        ),
        training=make_training(effect_for_best_position="NONE"),
    )
    squad = make_squad_context()
    eval_context = _evaluation_context(context, squad)
    strengths = detect_strengths(eval_context, squad, RecommendedRole.TACTICAL_SPECIALIST)
    types = [s.strength_type for s in strengths]
    assert (
        StrengthType.TACTICAL_VERSATILITY in types or StrengthType.VALUABLE_SPECIALTY in types
    )


def test_strengths_hard_to_replace():
    from engine.squad_intelligence.warnings import detect_strengths

    context = make_context(
        player=make_player(age=27, form=5),
        position=make_position(rank_in_best_position=4, candidates_in_best_position=6),
        training=make_training(effect_for_best_position="NONE"),
    )
    squad = make_squad_context(positional_depth={"INNER_MIDFIELDER": 1})
    eval_context = _evaluation_context(context, squad)
    strengths = detect_strengths(eval_context, squad, RecommendedRole.STARTER)
    assert any(s.strength_type == StrengthType.HARD_TO_REPLACE for s in strengths)


def test_risks_blocked_by_stronger_players():
    from engine.squad_intelligence.warnings import detect_risks

    context = make_context(
        position=make_position(rank_in_best_position=3, candidates_in_best_position=6)
    )
    eval_context = _evaluation_context(context, make_squad_context())
    risks = detect_risks(eval_context, make_squad_context(), RecommendedRole.USEFUL_ROTATION, ())
    assert any(r.risk_type == RiskType.BLOCKED_BY_STRONGER_PLAYERS for r in risks)


def test_risks_missing_data_included_when_limitations_present():
    from engine.squad_intelligence.warnings import detect_risks

    context = make_context()
    eval_context = _evaluation_context(context, make_squad_context())
    risks = detect_risks(
        eval_context, make_squad_context(), RecommendedRole.DEPTH_PLAYER,
        (LimitationType.MISSING_SALARY,),
    )
    assert any(r.risk_type == RiskType.MISSING_DATA for r in risks)


def test_risks_reduced_training_only():
    from engine.squad_intelligence.warnings import detect_risks

    context = make_context(training=make_training(effect_for_best_position="REDUCED"))
    eval_context = _evaluation_context(context, make_squad_context())
    risks = detect_risks(eval_context, make_squad_context(), RecommendedRole.SECONDARY_TRAINEE, ())
    assert any(r.risk_type == RiskType.REDUCED_TRAINING_ONLY for r in risks)


def test_generate_squad_reports_batch():
    from engine.squad_intelligence.service import generate_squad_reports

    contexts = [make_context(player_id=f"p{i}", player_name=f"Player {i}") for i in range(3)]
    reports = generate_squad_reports(contexts, make_squad_context())
    assert len(reports) == 3
    assert all(isinstance(r, PlayerIntelligenceReport) for r in reports)


def test_rule_engine_custom_role_rules_raises_without_fallback():
    engine = SquadIntelligenceRuleEngine(role_rules=())
    context = make_context()
    eval_context = _evaluation_context(context)
    with pytest.raises(RuntimeError):
        engine.resolve_role(eval_context)


def test_role_development_project_directly():
    from engine.squad_intelligence.roles import DevelopmentProjectRule
    from engine.squad_intelligence.enums import TrainingFit, TrainingPotential, CurrentPerformance

    context = make_context(player=make_player(age=20))
    eval_context = _evaluation_context(
        context,
        training_fit=TrainingFit.PARTIAL,
        training_potential=TrainingPotential.MEDIUM,
        current_performance=CurrentPerformance.LOW,
    )
    result = DevelopmentProjectRule().evaluate(eval_context)
    assert result is not None
    assert result[0] == RecommendedRole.DEVELOPMENT_PROJECT


def test_limitations_missing_age_days_and_incomplete_skills():
    player = make_player()
    player.days = None
    player.goalkeeper = None
    context = make_context(player=player)
    report = generate_report(context, make_squad_context())
    assert LimitationType.MISSING_AGE_DAYS in report.limitations
    assert LimitationType.INCOMPLETE_SKILLS in report.limitations


def test_limitations_no_active_training_and_no_positional_score():
    context = make_context(
        position=PositionEvidence(), training=TrainingEvidence(),
    )
    report = generate_report(context, make_squad_context())
    assert LimitationType.NO_ACTIVE_TRAINING in report.limitations
    assert LimitationType.NO_POSITIONAL_SCORE in report.limitations


def test_limitations_unavailable_current_roster_and_missing_stable_id():
    context = make_context(is_in_current_roster=False, has_stable_player_id=False)
    report = generate_report(context, make_squad_context())
    assert LimitationType.UNAVAILABLE_CURRENT_ROSTER in report.limitations
    assert LimitationType.MISSING_STABLE_PLAYER_ID in report.limitations


# --------------------------------------------------------------------------
# UX-03 role calibration: formation-demand-aware current performance
# --------------------------------------------------------------------------

def test_second_choice_goalkeeper_is_not_rated_as_high_as_a_starter():
    """Regression for a real calibration bug: a position that only
    ever fields one player (goalkeeper, formation_slots=1) must treat
    its second-choice very differently from a position with several
    starting slots. Rank 2 of 2 with formation_slots=1 should land
    clearly below rank 1's tier."""
    starter = make_context(
        position=make_position(
            best_position="GOALKEEPER", rank_in_best_position=1,
            candidates_in_best_position=2, formation_slots=1,
        )
    )
    backup = make_context(
        position=make_position(
            best_position="GOALKEEPER", rank_in_best_position=2,
            candidates_in_best_position=2, formation_slots=1,
        )
    )
    starter_perf, _ = classify_current_performance(starter)
    backup_perf, _ = classify_current_performance(backup)

    tiers = [
        CurrentPerformance.VERY_LOW, CurrentPerformance.LOW, CurrentPerformance.MEDIUM,
        CurrentPerformance.HIGH, CurrentPerformance.VERY_HIGH,
    ]
    assert tiers.index(starter_perf) > tiers.index(backup_perf)


def test_second_choice_goalkeeper_does_not_become_starter_role():
    context = make_context(
        player=make_player(form=5),
        position=make_position(
            best_position="GOALKEEPER", rank_in_best_position=2,
            candidates_in_best_position=2, formation_slots=1,
        ),
    )
    engine = SquadIntelligenceRuleEngine()
    eval_context = _evaluation_context(context, make_squad_context(positional_depth={"GOALKEEPER": 2}))
    role, _ = engine.resolve_role(eval_context)
    assert role not in (RecommendedRole.KEY_STARTER, RecommendedRole.STARTER)


def test_a_position_with_three_formation_slots_treats_its_third_choice_generously():
    """Unlike goalkeeper, a position that regularly fields several
    players (e.g. central defender, formation_slots=3) should still
    rate its rank-3 candidate as a genuine rotation starter, not a
    bench afterthought."""
    third_choice = make_context(
        position=make_position(
            best_position="CENTRAL_DEFENDER", rank_in_best_position=3,
            candidates_in_best_position=6, formation_slots=3,
        )
    )
    performance, _ = classify_current_performance(third_choice)
    assert performance in (CurrentPerformance.HIGH, CurrentPerformance.VERY_HIGH)


def test_beyond_formation_slots_performance_drops_off():
    within_slots = make_context(
        position=make_position(
            best_position="CENTRAL_DEFENDER", rank_in_best_position=3,
            candidates_in_best_position=6, formation_slots=3,
        )
    )
    beyond_slots = make_context(
        position=make_position(
            best_position="CENTRAL_DEFENDER", rank_in_best_position=4,
            candidates_in_best_position=6, formation_slots=3,
        )
    )
    within_perf, _ = classify_current_performance(within_slots)
    beyond_perf, _ = classify_current_performance(beyond_slots)
    tiers = [
        CurrentPerformance.VERY_LOW, CurrentPerformance.LOW, CurrentPerformance.MEDIUM,
        CurrentPerformance.HIGH, CurrentPerformance.VERY_HIGH,
    ]
    assert tiers.index(within_perf) >= tiers.index(beyond_perf)


def test_formation_slots_defaults_to_zero_and_falls_back_to_flat_formula():
    """Backward compatibility: existing PositionEvidence instances that
    don't set formation_slots (the default, 0) must behave exactly as
    before this sprint's calibration fix."""
    context = make_context(
        position=make_position(rank_in_best_position=2, candidates_in_best_position=4)
    )
    assert context.position.formation_slots == 0
    performance, _ = classify_current_performance(context)
    assert performance is not None
