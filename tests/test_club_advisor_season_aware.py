import pytest

from engine.club_advisor.context import ClubAdvisorContext
from engine.club_advisor.enums import (
    ActionType,
    ClubConfidence,
    CurrentCompetitiveness,
    DepthStatus,
    OperationalUrgency,
    PromotionObjective,
    PromotionReadiness,
    RecommendationHorizon,
    SeasonPhase,
    SigningCostCategory,
    StrategicNeed,
)
from engine.club_advisor.models import (
    ClubAdvisorReport,
    DepthSummary,
    PositionDepth,
    SquadSummary,
    TrainingSummary,
)
from engine.club_advisor.recommendation_policy import (
    assess_promotion_readiness,
    build_season_aware_priorities,
)
from engine.club_advisor.season_context import SeasonContext
from engine.club_advisor.service import generate_report
from engine.club_advisor.timing import determine_action_type
from engine.club_advisor.urgency import UrgencyInputs, compute_urgency


class FakeBaseReport:
    def __init__(self, depth_summary=None, training_summary=None, squad_summary=None):
        self.depth_summary = depth_summary or DepthSummary(positions=())
        self.training_summary = training_summary or TrainingSummary()
        self.squad_summary = squad_summary or SquadSummary()


def make_depth(**statuses):
    positions = tuple(
        PositionDepth(position=position, status=status, player_count=1)
        for position, status in statuses.items()
    )
    return DepthSummary(positions=positions)


def test_high_need_can_produce_low_urgency():
    context = SeasonContext(
        season_phase=SeasonPhase.EARLY_SEASON,
        current_competitiveness=CurrentCompetitiveness.DOMINANT,
        bot_opponent_count=3,
        promotion_objective=PromotionObjective.WELCOME_IF_NATURAL,
        recent_major_signing=True,
        recent_signing_position="CENTRAL_DEFENDER",
    )
    inputs = UrgencyInputs(area_matches_recent_signing=True)
    urgency, evidence = compute_urgency(StrategicNeed.HIGH, context, inputs)
    assert urgency == OperationalUrgency.LOW
    assert evidence


def test_urgency_is_never_computed_from_need_alone():
    """A SeasonContext with genuinely no modifiers (promotion
    explicitly UNSPECIFIED, not the WELCOME_IF_NATURAL default which
    is itself a mild reducer) versus one with several active reducers
    must not land on the same urgency -- proving urgency reads the
    context, not just the need."""
    from engine.club_advisor.enums import PromotionObjective as PO

    plain_context = SeasonContext(promotion_objective=PO.UNSPECIFIED)
    reduced_context = SeasonContext(
        current_competitiveness=CurrentCompetitiveness.DOMINANT,
        bot_opponent_count=5,
        season_phase=SeasonPhase.EARLY_SEASON,
        promotion_objective=PromotionObjective.NOT_A_PRIORITY,
    )
    plain_urgency, _ = compute_urgency(StrategicNeed.HIGH, plain_context)
    reduced_urgency, _ = compute_urgency(StrategicNeed.HIGH, reduced_context)
    order = [
        OperationalUrgency.NONE, OperationalUrgency.DEFERRED, OperationalUrgency.LOW,
        OperationalUrgency.MEDIUM, OperationalUrgency.HIGH, OperationalUrgency.IMMEDIATE,
    ]
    assert order.index(reduced_urgency) < order.index(plain_urgency)


def test_scenario_1_high_need_low_urgency_monitors_or_defers():
    context = SeasonContext(
        season_phase=SeasonPhase.EARLY_SEASON,
        current_competitiveness=CurrentCompetitiveness.DOMINANT,
        bot_opponent_count=3,
        promotion_objective=PromotionObjective.WELCOME_IF_NATURAL,
        recent_major_signing=True,
        recent_signing_position="CENTRAL_DEFENDER",
    )
    inputs = UrgencyInputs(area_matches_recent_signing=True)
    urgency, _ = compute_urgency(StrategicNeed.HIGH, context, inputs)
    action = determine_action_type(StrategicNeed.HIGH, urgency)
    assert action in (ActionType.MONITOR, ActionType.DEFER)
    assert action != ActionType.ACT_NOW


def test_scenario_2_no_replacement_and_unavailable_player_forces_action():
    context = SeasonContext(season_phase=SeasonPhase.PROMOTION_STAGE)
    inputs = UrgencyInputs(has_no_internal_replacement=True, player_unavailable=True)
    urgency, _ = compute_urgency(StrategicNeed.CRITICAL, context, inputs)
    action = determine_action_type(StrategicNeed.CRITICAL, urgency)
    assert urgency in (OperationalUrgency.HIGH, OperationalUrgency.IMMEDIATE)
    assert action in (ActionType.ACT_NOW, ActionType.PREPARE)


def test_scenario_3_low_need_produces_no_action():
    context = SeasonContext()
    urgency, _ = compute_urgency(StrategicNeed.LOW, context)
    action = determine_action_type(StrategicNeed.LOW, urgency)
    assert action in (ActionType.NO_ACTION, ActionType.MAINTAIN)


def test_none_need_is_always_no_urgency_and_no_action():
    urgency, _ = compute_urgency(StrategicNeed.NONE, SeasonContext())
    assert urgency == OperationalUrgency.NONE
    assert determine_action_type(StrategicNeed.NONE, urgency) == ActionType.NO_ACTION


def test_scenario_4_dominance_with_gaps_is_developing_not_ready():
    base_report = FakeBaseReport(
        depth_summary=make_depth(CENTRAL_DEFENDER=DepthStatus.NO_REPLACEMENT.value)
    )
    season = SeasonContext(current_competitiveness=CurrentCompetitiveness.DOMINANT)
    readiness = assess_promotion_readiness(base_report, season)
    assert readiness.readiness == PromotionReadiness.DEVELOPING
    assert readiness.confidence != ClubConfidence.INSUFFICIENT_DATA


def test_scenario_5_bots_are_one_reducer_not_a_guarantee():
    context_many_bots = SeasonContext(bot_opponent_count=6)
    context_no_bots = SeasonContext(bot_opponent_count=0)
    urgency_many, _ = compute_urgency(StrategicNeed.HIGH, context_many_bots)
    urgency_none, _ = compute_urgency(StrategicNeed.HIGH, context_no_bots)
    order = [
        OperationalUrgency.NONE, OperationalUrgency.DEFERRED, OperationalUrgency.LOW,
        OperationalUrgency.MEDIUM, OperationalUrgency.HIGH, OperationalUrgency.IMMEDIATE,
    ]
    assert order.index(urgency_many) <= order.index(urgency_none)


def test_scenario_6_recent_signing_reduces_urgency_for_same_area():
    context = SeasonContext(recent_major_signing=True, recent_signing_position="CENTRAL_DEFENDER")
    with_signing = UrgencyInputs(area_matches_recent_signing=True)
    without_signing = UrgencyInputs(area_matches_recent_signing=False)
    urgency_with, _ = compute_urgency(StrategicNeed.HIGH, context, with_signing)
    urgency_without, _ = compute_urgency(StrategicNeed.HIGH, context, without_signing)
    order = [
        OperationalUrgency.NONE, OperationalUrgency.DEFERRED, OperationalUrgency.LOW,
        OperationalUrgency.MEDIUM, OperationalUrgency.HIGH, OperationalUrgency.IMMEDIATE,
    ]
    assert order.index(urgency_with) <= order.index(urgency_without)


def test_season_context_signing_matches_area():
    context = SeasonContext(recent_major_signing=True, recent_signing_position="CENTRAL_DEFENDER")
    assert context.signing_matches_area("central_defense") or context.signing_matches_area(
        "CENTRAL_DEFENDER"
    )
    assert not context.signing_matches_area("FORWARD")


def test_scenario_7_promotion_targeted_increases_urgency():
    deprioritized = SeasonContext(promotion_objective=PromotionObjective.NOT_A_PRIORITY)
    targeted = SeasonContext(promotion_objective=PromotionObjective.TARGET_THIS_SEASON)
    urgency_deprioritized, _ = compute_urgency(StrategicNeed.MEDIUM, deprioritized)
    urgency_targeted, _ = compute_urgency(StrategicNeed.MEDIUM, targeted)
    order = [
        OperationalUrgency.NONE, OperationalUrgency.DEFERRED, OperationalUrgency.LOW,
        OperationalUrgency.MEDIUM, OperationalUrgency.HIGH, OperationalUrgency.IMMEDIATE,
    ]
    assert order.index(urgency_targeted) >= order.index(urgency_deprioritized)


def test_scenario_8_promotion_not_priority_favors_development():
    context = SeasonContext(promotion_objective=PromotionObjective.NOT_A_PRIORITY)
    urgency, _ = compute_urgency(StrategicNeed.MEDIUM, context)
    action = determine_action_type(StrategicNeed.MEDIUM, urgency)
    assert action in (ActionType.MONITOR, ActionType.MAINTAIN, ActionType.DEFER, ActionType.NO_ACTION)
    assert action != ActionType.ACT_NOW


def test_scenario_9_unknown_season_context_still_generates_report():
    context = ClubAdvisorContext()
    report = generate_report(context, season_context=SeasonContext())
    assert isinstance(report, ClubAdvisorReport)
    assert report.promotion_readiness.readiness == PromotionReadiness.NOT_EVALUATED
    assert report.promotion_readiness.confidence == ClubConfidence.INSUFFICIENT_DATA


def test_scenario_9_missing_context_does_not_fabricate_conclusions():
    base_report = FakeBaseReport(
        depth_summary=make_depth(CENTRAL_DEFENDER=DepthStatus.NO_REPLACEMENT.value)
    )
    readiness = assess_promotion_readiness(base_report, SeasonContext())
    assert readiness.readiness == PromotionReadiness.NOT_EVALUATED
    assert readiness.limitations


def test_scenario_10_strategic_and_operational_texts_differ():
    base_report = FakeBaseReport(
        depth_summary=make_depth(
            CENTRAL_DEFENDER=DepthStatus.NO_REPLACEMENT.value,
            WING_BACK=DepthStatus.ONE_REPLACEMENT.value,
        )
    )
    strategic, operational = build_season_aware_priorities(base_report, SeasonContext())
    strategic_keys = {p.reason_key for p in strategic}
    operational_keys = {p.reason_key for p in operational}
    assert strategic_keys.isdisjoint(operational_keys)


def test_scenario_11_generate_report_without_season_context_arg_still_works():
    context = ClubAdvisorContext()
    report = generate_report(context)
    assert isinstance(report, ClubAdvisorReport)
    assert report.strategic_priorities is not None
    assert report.operational_priorities is not None


def test_scenario_11_existing_fields_unchanged():
    context = ClubAdvisorContext()
    report = generate_report(context)
    assert hasattr(report, "project_status")
    assert hasattr(report, "priorities")
    assert hasattr(report, "risks")
    assert hasattr(report, "strengths")


def test_every_priority_has_a_recommendation_horizon():
    base_report = FakeBaseReport(
        depth_summary=make_depth(
            GOALKEEPER=DepthStatus.FUTURE_SHORTAGE.value,
            CENTRAL_DEFENDER=DepthStatus.NO_REPLACEMENT.value,
        ),
        training_summary=TrainingSummary(players_without_training=10, total_players_evaluated=19),
    )
    strategic, operational = build_season_aware_priorities(base_report, SeasonContext())
    for priority in strategic + operational:
        assert priority.recommendation_horizon is not None


def test_every_priority_has_evidence():
    base_report = FakeBaseReport(
        depth_summary=make_depth(CENTRAL_DEFENDER=DepthStatus.NO_REPLACEMENT.value)
    )
    strategic, operational = build_season_aware_priorities(base_report, SeasonContext())
    for priority in strategic + operational:
        assert priority.evidence


def test_deliberate_inaction_is_a_legitimate_recommendation():
    base_report = FakeBaseReport(
        training_summary=TrainingSummary(
            players_without_training=0, total_players_evaluated=10, full_effect_slots_used=5
        )
    )
    _strategic, operational = build_season_aware_priorities(base_report, SeasonContext())
    maintain = next(p for p in operational if p.area == "training_utilization")
    assert maintain.action_type == ActionType.MAINTAIN
    assert maintain.evidence


def test_dominance_does_not_imply_promotion_readiness():
    base_report = FakeBaseReport(
        depth_summary=make_depth(CENTRAL_DEFENDER=DepthStatus.NO_REPLACEMENT.value)
    )
    season = SeasonContext(current_competitiveness=CurrentCompetitiveness.DOMINANT)
    readiness = assess_promotion_readiness(base_report, season)
    assert readiness.readiness != PromotionReadiness.READY


def test_no_major_gaps_and_dominant_is_nearly_ready():
    base_report = FakeBaseReport(
        depth_summary=make_depth(
            CENTRAL_DEFENDER=DepthStatus.HEALTHY_COMPETITION.value,
            GOALKEEPER=DepthStatus.ONE_REPLACEMENT.value,
        )
    )
    season = SeasonContext(current_competitiveness=CurrentCompetitiveness.DOMINANT)
    readiness = assess_promotion_readiness(base_report, season)
    assert readiness.readiness in (PromotionReadiness.NEARLY_READY, PromotionReadiness.READY)


def test_real_data_regression_fixture():
    base_report = FakeBaseReport(
        depth_summary=make_depth(
            GOALKEEPER=DepthStatus.FUTURE_SHORTAGE.value,
            CENTRAL_DEFENDER=DepthStatus.NO_REPLACEMENT.value,
            WING_BACK=DepthStatus.ONE_REPLACEMENT.value,
            INNER_MIDFIELDER=DepthStatus.HEALTHY_COMPETITION.value,
            WINGER=DepthStatus.HEALTHY_COMPETITION.value,
            FORWARD=DepthStatus.HEALTHY_COMPETITION.value,
        ),
        training_summary=TrainingSummary(
            players_without_training=8, total_players_evaluated=19, full_effect_slots_used=5,
        ),
        squad_summary=SquadSummary(
            key_starter_count=3, rotation_count=9, veteran_count=2, replaceable_count=1,
            depth_player_count=1,
        ),
    )
    season = SeasonContext(
        season_phase=SeasonPhase.EARLY_SEASON,
        current_competitiveness=CurrentCompetitiveness.DOMINANT,
        bot_opponent_count=3,
        promotion_objective=PromotionObjective.WELCOME_IF_NATURAL,
        recent_major_signing=True,
        recent_signing_position="CENTRAL_DEFENDER",
        recent_signing_cost_category=SigningCostCategory.HIGH,
    )

    strategic, operational = build_season_aware_priorities(base_report, season)
    readiness = assess_promotion_readiness(base_report, season)

    central_defense_strategic = next(p for p in strategic if p.area == "central_defense")
    goalkeeper_strategic = next(p for p in strategic if p.area == "goalkeeper")

    assert central_defense_strategic.strategic_need in (StrategicNeed.HIGH, StrategicNeed.CRITICAL)
    assert central_defense_strategic.operational_urgency in (
        OperationalUrgency.LOW, OperationalUrgency.DEFERRED,
    )
    assert central_defense_strategic.action_type != ActionType.ACT_NOW
    assert goalkeeper_strategic.recommendation_horizon == RecommendationHorizon.NEXT_SEASON
    assert readiness.readiness in (PromotionReadiness.DEVELOPING, PromotionReadiness.NOT_EVALUATED)


def test_real_data_fixture_never_recommends_immediate_purchase():
    base_report = FakeBaseReport(
        depth_summary=make_depth(CENTRAL_DEFENDER=DepthStatus.NO_REPLACEMENT.value),
    )
    season = SeasonContext(
        current_competitiveness=CurrentCompetitiveness.DOMINANT,
        recent_major_signing=True,
        recent_signing_position="CENTRAL_DEFENDER",
    )
    strategic, operational = build_season_aware_priorities(base_report, season)
    for priority in strategic + operational:
        assert priority.action_type != ActionType.ACT_NOW


def test_no_financial_or_purchase_language_in_any_enum():
    from engine.club_advisor import enums

    for enum_cls in (
        enums.ActionType, enums.RecommendationHorizon, enums.StrategicNeed,
        enums.OperationalUrgency, enums.PromotionReadiness,
    ):
        for member in enum_cls:
            assert "purchase" not in member.value
            assert "price" not in member.value
            assert "budget" not in member.value


def test_season_modules_never_import_optimizers_or_squad_intelligence_rules():
    import ast
    from pathlib import Path

    package_dir = Path(__file__).resolve().parents[1] / "engine" / "club_advisor"
    forbidden = {
        "engine.optimizers.formation_optimizer",
        "engine.optimizers.tactic_optimizer",
        "engine.squad_intelligence.roles",
        "engine.squad_intelligence.statuses",
    }
    season_modules = (
        "season_context.py", "horizons.py", "urgency.py", "timing.py",
        "season_plan.py", "recommendation_policy.py",
    )
    for filename in season_modules:
        path = package_dir / filename
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        assert not (imported & forbidden), f"{filename} imports {imported & forbidden}"


# --------------------------------------------------------------------------
# Additional coverage: horizons.py and timing.py branches
# --------------------------------------------------------------------------

def test_horizon_promotion_stage_overrides_monitor_to_before_promotion():
    from engine.club_advisor.horizons import default_horizon_for_action

    season = SeasonContext(season_phase=SeasonPhase.PROMOTION_STAGE)
    horizon = default_horizon_for_action(ActionType.MONITOR, season)
    assert horizon == RecommendationHorizon.BEFORE_PROMOTION


def test_horizon_reevaluate_default():
    from engine.club_advisor.horizons import default_horizon_for_action

    horizon = default_horizon_for_action(ActionType.REEVALUATE, None)
    assert horizon == RecommendationHorizon.NEXT_SEASON


def test_horizon_act_now_default():
    from engine.club_advisor.horizons import default_horizon_for_action

    horizon = default_horizon_for_action(ActionType.ACT_NOW, None)
    assert horizon == RecommendationHorizon.THIS_WEEK


def test_horizon_no_action_default():
    from engine.club_advisor.horizons import default_horizon_for_action

    horizon = default_horizon_for_action(ActionType.NO_ACTION, None)
    assert horizon == RecommendationHorizon.NO_ACTION_REQUIRED


def test_timing_immediate_urgency_always_acts_now():
    action = determine_action_type(StrategicNeed.LOW, OperationalUrgency.IMMEDIATE)
    assert action == ActionType.ACT_NOW


def test_timing_high_urgency_high_need_prepares_not_acts():
    action = determine_action_type(StrategicNeed.HIGH, OperationalUrgency.HIGH)
    assert action == ActionType.PREPARE


def test_timing_medium_urgency_low_need_maintains():
    action = determine_action_type(StrategicNeed.LOW, OperationalUrgency.MEDIUM)
    assert action == ActionType.MAINTAIN


def test_timing_none_urgency_always_no_action():
    action = determine_action_type(StrategicNeed.CRITICAL, OperationalUrgency.NONE)
    assert action == ActionType.NO_ACTION


def test_timing_insufficient_data_urgency_monitors():
    action = determine_action_type(StrategicNeed.HIGH, OperationalUrgency.INSUFFICIENT_DATA)
    assert action == ActionType.MONITOR
