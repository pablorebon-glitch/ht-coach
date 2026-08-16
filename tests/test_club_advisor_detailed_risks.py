from engine.club_advisor.context import ClubAdvisorContext
from engine.club_advisor.enums import ClubWarningType
from engine.club_advisor.risks import detect_risks
from engine.club_advisor.warnings import generate_warnings
from engine.club_advisor.summary import build_depth_summary, build_squad_summary, build_training_summary
from engine.squad_intelligence.context import SquadIntelligenceContext
from engine.squad_intelligence.enums import (
    ClubStrategy,
    CurrentPerformance,
    ManagementStatus,
    RecommendedRole,
    SalaryEfficiency,
    StrategicValue,
    TrainingFit,
    TrainingPotential,
    IntelligenceConfidence,
    MilestoneType,
)
from engine.squad_intelligence.models import PlayerIntelligenceReport, PlayerMilestone


def make_report(name="P", role=RecommendedRole.STARTER, training_fit=TrainingFit.EXCELLENT):
    return PlayerIntelligenceReport(
        player_id=name,
        player_name=name,
        generated_at="2026-01-01T00:00:00Z",
        strategy=ClubStrategy.SUSTAINABLE_GROWTH,
        recommended_role=role,
        management_status=ManagementStatus.KEEP,
        primary_reason_key="x",
        primary_reason_params={},
        supporting_reason_keys=(),
        current_performance=CurrentPerformance.HIGH,
        training_potential=TrainingPotential.MEDIUM,
        training_fit=training_fit,
        salary_efficiency=SalaryEfficiency.GOOD,
        strategic_value=StrategicValue.MEDIUM,
        next_milestone=PlayerMilestone(MilestoneType.NO_MILESTONE),
        confidence=IntelligenceConfidence.HIGH,
    )


def make_context(squad_reports, positional_depth, players_by_position=None):
    squad_context = SquadIntelligenceContext(
        roster_size=len(squad_reports), positional_depth=positional_depth,
        active_training_type="PLAYMAKING",
    )
    return ClubAdvisorContext(
        squad_reports=tuple(squad_reports), squad_context=squad_context,
        active_training_type="PLAYMAKING",
        players_by_position=players_by_position or {},
    )


def test_goalkeeper_risk_has_full_detail():
    context = make_context([make_report("GK1")], {"GOALKEEPER": 1}, {"GOALKEEPER": ("GK1",)})
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    risks = detect_risks(context, training_summary, squad_summary, depth_summary)
    gk_risk = next(r for r in risks if r.position == "GOALKEEPER")
    assert gk_risk.reason_key
    assert gk_risk.impact
    assert gk_risk.urgency
    assert gk_risk.affected_players == ("GK1",)
    assert gk_risk.review_condition_key


def test_central_defense_risk_impact_reflects_formation_coverage():
    """A gap that the preferred formations still cover (combined CD+WB
    count clears formation demand) should show low impact, not a
    blanket high-severity statement."""
    context = make_context(
        [make_report(f"D{i}") for i in range(5)],
        {"CENTRAL_DEFENDER": 1, "WING_BACK": 4},
        {"CENTRAL_DEFENDER": ("D0",), "WING_BACK": ("D1", "D2", "D3", "D4")},
    )
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    risks = detect_risks(context, training_summary, squad_summary, depth_summary)
    cd_risk = next(r for r in risks if r.position == "CENTRAL_DEFENDER")
    assert cd_risk.impact == "low"


def test_no_risk_contains_only_abstract_labels():
    """Every risk must carry actionable detail, not just an abstract
    label -- the sprint's own example: 'Weak positional depth' alone is
    insufficient."""
    context = make_context([make_report("D1")], {"CENTRAL_DEFENDER": 1}, {"CENTRAL_DEFENDER": ("D1",)})
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    risks = detect_risks(context, training_summary, squad_summary, depth_summary)
    for risk in risks:
        assert risk.reason_key
        assert risk.impact
        assert risk.urgency
        assert risk.review_condition_key


def test_players_without_training_never_flagged_as_risk_when_expected():
    reports = [make_report(f"P{i}", training_fit=TrainingFit.NO_TRAINING) for i in range(8)]
    context = make_context(reports, {"WINGER": 8}, {"WINGER": tuple(f"P{i}" for i in range(8))})
    training_summary = build_training_summary(context)
    training_summary = type(training_summary)(
        **{**training_summary.__dict__, "players_without_training": 6, "total_players_evaluated": 8}
    )
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    risks = detect_risks(context, training_summary, squad_summary, depth_summary)
    assert all(r.risk_type.value != "players_without_training" for r in risks)


def test_priority_trainees_missing_training_warning():
    reports = [
        make_report("Trainee1", role=RecommendedRole.PRIMARY_TRAINEE, training_fit=TrainingFit.NO_TRAINING),
        make_report("Trainee2", role=RecommendedRole.SECONDARY_TRAINEE, training_fit=TrainingFit.UNKNOWN),
        make_report("Starter1", role=RecommendedRole.STARTER, training_fit=TrainingFit.EXCELLENT),
    ]
    context = make_context(reports, {"INNER_MIDFIELDER": 3})
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    warnings = generate_warnings(context, training_summary, squad_summary, depth_summary)
    warning = next(w for w in warnings if w.warning_type == ClubWarningType.PRIORITY_TRAINEES_MISSING_TRAINING)
    assert warning.reason_params["count"] == 2


def test_training_slot_competition_warning():
    reports = [make_report(f"W{i}") for i in range(8)]
    context = make_context(reports, {"WINGER": 8})
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    warnings = generate_warnings(context, training_summary, squad_summary, depth_summary)
    assert any(w.warning_type == ClubWarningType.TRAINING_SLOT_COMPETITION for w in warnings)


def test_training_plan_deviation_warning():
    reports = [
        make_report("Odd1", role=RecommendedRole.DEPTH_PLAYER, training_fit=TrainingFit.EXCELLENT),
    ]
    context = make_context(reports, {"INNER_MIDFIELDER": 1})
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    warnings = generate_warnings(context, training_summary, squad_summary, depth_summary)
    assert any(w.warning_type == ClubWarningType.TRAINING_PLAN_DEVIATION for w in warnings)
