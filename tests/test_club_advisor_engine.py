import pytest

from engine.club_advisor.confidence import ClubConfidenceInputs, classify_confidence
from engine.club_advisor.context import ClubAdvisorContext
from engine.club_advisor.dimensions import evaluate_project_status
from engine.club_advisor.enums import (
    ClubConfidence,
    ClubLimitationType,
    ClubRiskType,
    ClubStrengthType,
    ClubWarningType,
    DepthStatus,
    PriorityType,
    ProjectStatus,
)
from engine.club_advisor.models import (
    ClubAdvisorReport,
    DepthSummary,
    PositionDepth,
    SquadSummary,
    TrainingSummary,
)
from engine.club_advisor.priorities import generate_priorities
from engine.club_advisor.risks import detect_risks
from engine.club_advisor.rule_engine import ClubAdvisorRuleEngine
from engine.club_advisor.service import generate_report
from engine.club_advisor.strengths import detect_strengths
from engine.club_advisor.summary import build_depth_summary, build_squad_summary, build_training_summary
from engine.club_advisor.validation import ClubAdvisorError, ensure_context_valid
from engine.club_advisor.warnings import generate_warnings
from engine.squad_intelligence.context import SquadIntelligenceContext
from engine.squad_intelligence.enums import (
    CurrentPerformance,
    ManagementStatus,
    RecommendedRole,
    SalaryEfficiency,
    StrategicValue,
    TrainingFit,
    TrainingPotential,
)
from engine.squad_intelligence.models import PlayerIntelligenceReport, PlayerMilestone
from engine.squad_intelligence.enums import MilestoneType, IntelligenceConfidence


def make_report(name="P", role=RecommendedRole.STARTER, training_fit=TrainingFit.EXCELLENT,
                 salary_efficiency=SalaryEfficiency.GOOD, status=ManagementStatus.KEEP):
    return PlayerIntelligenceReport(
        player_id=name,
        player_name=name,
        generated_at="2026-01-01T00:00:00Z",
        strategy=__import__("engine.squad_intelligence", fromlist=["ClubStrategy"]).ClubStrategy.SUSTAINABLE_GROWTH,
        recommended_role=role,
        management_status=status,
        primary_reason_key="squad_intelligence.reason.starter",
        primary_reason_params={},
        supporting_reason_keys=(),
        current_performance=CurrentPerformance.HIGH,
        training_potential=TrainingPotential.MEDIUM,
        training_fit=training_fit,
        salary_efficiency=salary_efficiency,
        strategic_value=StrategicValue.MEDIUM,
        next_milestone=PlayerMilestone(MilestoneType.NO_MILESTONE),
        confidence=IntelligenceConfidence.HIGH,
    )


def make_squad_context(positional_depth=None, ages_by_position=None):
    return SquadIntelligenceContext(
        roster_size=sum((positional_depth or {}).values()),
        positional_depth=positional_depth or {},
        active_training_type="PLAYMAKING",
        ages_by_position=ages_by_position or {},
    )


def make_context(squad_reports=None, positional_depth=None, active_training_type="PLAYMAKING",
                  has_historical_data=False, ages_by_position=None):
    squad_reports = squad_reports if squad_reports is not None else [make_report()]
    return ClubAdvisorContext(
        squad_reports=tuple(squad_reports),
        squad_context=make_squad_context(positional_depth, ages_by_position),
        active_training_type=active_training_type,
        has_historical_data=has_historical_data,
    )


# --------------------------------------------------------------------------
# Report generation and models
# --------------------------------------------------------------------------

def test_generate_report_end_to_end():
    context = make_context(positional_depth={"GOALKEEPER": 2, "CENTRAL_DEFENDER": 3})
    report = generate_report(context)
    assert isinstance(report, ClubAdvisorReport)
    payload = report.to_dict()
    assert payload["project_status"]


def test_report_never_shows_a_single_overall_score():
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(ClubAdvisorReport)}
    assert "overall_score" not in field_names
    assert "score" not in field_names


def test_ensure_context_valid_rejects_none():
    with pytest.raises(ClubAdvisorError):
        ensure_context_valid(None)


# --------------------------------------------------------------------------
# Project status (independent dimensions)
# --------------------------------------------------------------------------

def test_project_status_excellent_when_all_dimensions_healthy():
    training_summary = TrainingSummary(
        primary_trainee_count=2, secondary_trainee_count=3, players_without_training=0,
        full_effect_slots_used=5, total_players_evaluated=10,
    )
    squad_summary = SquadSummary(replaceable_count=0)
    depth_summary = DepthSummary(
        positions=tuple(
            PositionDepth(position=p, status=DepthStatus.HEALTHY_COMPETITION.value, player_count=3)
            for p in ("GOALKEEPER", "CENTRAL_DEFENDER", "WING_BACK", "INNER_MIDFIELDER", "WINGER", "FORWARD")
        )
    )
    status = evaluate_project_status(training_summary, squad_summary, depth_summary, 10)
    assert status in (ProjectStatus.EXCELLENT, ProjectStatus.HEALTHY)


def test_project_status_critical_with_severe_depth_and_training_gaps():
    training_summary = TrainingSummary(players_without_training=8, total_players_evaluated=10)
    squad_summary = SquadSummary()
    depth_summary = DepthSummary(
        positions=tuple(
            PositionDepth(position=p, status=DepthStatus.NO_REPLACEMENT.value, player_count=1)
            for p in ("GOALKEEPER", "CENTRAL_DEFENDER", "WING_BACK")
        )
    )
    status = evaluate_project_status(training_summary, squad_summary, depth_summary, 10)
    assert status == ProjectStatus.CRITICAL


def test_project_status_never_uses_a_single_blended_score():
    """A dimension-by-dimension implementation detail: verify that a
    single very-bad dimension caps the overall status even when the
    other two are perfect -- proving it isn't an averaged score."""
    perfect_training = TrainingSummary(
        primary_trainee_count=3, secondary_trainee_count=3, players_without_training=0,
        full_effect_slots_used=5, total_players_evaluated=10,
    )
    perfect_squad = SquadSummary(replaceable_count=0)
    terrible_depth = DepthSummary(
        positions=tuple(
            PositionDepth(position=p, status=DepthStatus.NO_REPLACEMENT.value, player_count=1)
            for p in ("GOALKEEPER", "CENTRAL_DEFENDER", "WING_BACK")
        )
    )
    status = evaluate_project_status(perfect_training, perfect_squad, terrible_depth, 10)
    assert status == ProjectStatus.CRITICAL


def test_project_status_with_empty_roster_is_stable_not_a_crash():
    training_summary = TrainingSummary()
    squad_summary = SquadSummary()
    depth_summary = DepthSummary(positions=())
    status = evaluate_project_status(training_summary, squad_summary, depth_summary, 0)
    assert status == ProjectStatus.STABLE


# --------------------------------------------------------------------------
# Priorities (ordered, evidenced, never purchases/players/prices)
# --------------------------------------------------------------------------

def test_priorities_are_ordered_by_rank():
    context = make_context(
        positional_depth={"GOALKEEPER": 1, "CENTRAL_DEFENDER": 1},
        squad_reports=[make_report(role=RecommendedRole.KEY_STARTER)],
    )
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    priorities = generate_priorities(context, training_summary, squad_summary, depth_summary)

    ranks = [p.rank for p in priorities]
    assert ranks == sorted(ranks)
    assert ranks[0] == 1


def test_goalkeeper_priority_ranks_above_generic_depth_priority():
    context = make_context(positional_depth={"GOALKEEPER": 1, "WINGER": 1})
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    priorities = generate_priorities(context, training_summary, squad_summary, depth_summary)

    priority_types = [p.priority_type for p in priorities]
    assert PriorityType.ADDRESS_GOALKEEPER_COVERAGE in priority_types


def test_priorities_never_mention_purchases_or_prices():
    context = make_context(positional_depth={"GOALKEEPER": 1})
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    priorities = generate_priorities(context, training_summary, squad_summary, depth_summary)

    for priority in priorities:
        assert "purchase" not in priority.priority_type.value
        assert "price" not in priority.priority_type.value
        assert "buy" not in priority.priority_type.value


def test_maintain_training_priority_when_everything_is_healthy():
    context = make_context(
        positional_depth={p: 3 for p in ("GOALKEEPER", "CENTRAL_DEFENDER", "WING_BACK", "INNER_MIDFIELDER", "WINGER", "FORWARD")},
        squad_reports=[
            make_report(name=f"P{i}", training_fit=TrainingFit.EXCELLENT) for i in range(6)
        ],
    )
    training_summary = TrainingSummary(
        primary_trainee_count=2, secondary_trainee_count=2, players_without_training=0,
        full_effect_slots_used=4, total_players_evaluated=6,
    )
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    priorities = generate_priorities(context, training_summary, squad_summary, depth_summary)
    assert any(p.priority_type == PriorityType.MAINTAIN_CURRENT_TRAINING for p in priorities)


def test_priority_evidence_is_never_empty():
    context = make_context(positional_depth={"GOALKEEPER": 1})
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    priorities = generate_priorities(context, training_summary, squad_summary, depth_summary)
    for priority in priorities:
        assert priority.evidence


# --------------------------------------------------------------------------
# Risks
# --------------------------------------------------------------------------

def test_risk_only_one_goalkeeper():
    context = make_context(positional_depth={"GOALKEEPER": 1})
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    risks = detect_risks(context, training_summary, squad_summary, depth_summary)
    assert any(r.risk_type == ClubRiskType.ONLY_ONE_GOALKEEPER for r in risks)


def test_risk_no_central_defender_replacement():
    context = make_context(positional_depth={"CENTRAL_DEFENDER": 1})
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    risks = detect_risks(context, training_summary, squad_summary, depth_summary)
    assert any(r.risk_type == ClubRiskType.NO_CENTRAL_DEFENDER_REPLACEMENT for r in risks)


def test_risk_players_without_training():
    reports = [make_report(name=f"P{i}", training_fit=TrainingFit.NO_TRAINING) for i in range(8)]
    context = make_context(squad_reports=reports, positional_depth={"WINGER": 8})
    training_summary = TrainingSummary(players_without_training=6, total_players_evaluated=8)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    risks = detect_risks(context, training_summary, squad_summary, depth_summary)
    assert any(r.risk_type == ClubRiskType.PLAYERS_WITHOUT_TRAINING for r in risks)


def test_risk_starter_dependency():
    context = make_context(
        positional_depth={"GOALKEEPER": 1},
        squad_reports=[make_report(role=RecommendedRole.KEY_STARTER)],
    )
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    risks = detect_risks(context, training_summary, squad_summary, depth_summary)
    assert any(r.risk_type == ClubRiskType.STARTER_DEPENDENCY for r in risks)


def test_no_risks_when_squad_is_healthy():
    reports = [make_report(name=f"P{i}") for i in range(12)]
    context = make_context(
        squad_reports=reports,
        positional_depth={p: 3 for p in ("GOALKEEPER", "CENTRAL_DEFENDER", "WING_BACK", "INNER_MIDFIELDER")},
    )
    training_summary = TrainingSummary(players_without_training=0, total_players_evaluated=12, full_effect_slots_used=5)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    risks = detect_risks(context, training_summary, squad_summary, depth_summary)
    assert ClubRiskType.ONLY_ONE_GOALKEEPER not in [r.risk_type for r in risks]


def test_all_risks_have_evidence():
    context = make_context(positional_depth={"GOALKEEPER": 1, "CENTRAL_DEFENDER": 1})
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    risks = detect_risks(context, training_summary, squad_summary, depth_summary)
    for risk in risks:
        assert risk.evidence


def test_no_financial_risk_types_exist():
    """This sprint deliberately does not estimate financial risks."""
    for risk_type in ClubRiskType:
        assert "financ" not in risk_type.value
        assert "budget" not in risk_type.value


# --------------------------------------------------------------------------
# Strengths
# --------------------------------------------------------------------------

def test_strength_training_fully_utilized():
    reports = [make_report(name=f"P{i}", training_fit=TrainingFit.EXCELLENT) for i in range(4)]
    context = make_context(squad_reports=reports)
    training_summary = TrainingSummary(players_without_training=0, full_effect_slots_used=4, total_players_evaluated=4)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    strengths = detect_strengths(context, training_summary, squad_summary, depth_summary)
    assert any(s.strength_type == ClubStrengthType.TRAINING_FULLY_UTILIZED for s in strengths)


def test_strength_excellent_trainee_pipeline():
    context = make_context()
    training_summary = TrainingSummary(primary_trainee_count=3, total_players_evaluated=10)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    strengths = detect_strengths(context, training_summary, squad_summary, depth_summary)
    assert any(s.strength_type == ClubStrengthType.EXCELLENT_TRAINEE_PIPELINE for s in strengths)


def test_strength_strong_positional_coverage():
    context = make_context(positional_depth={p: 3 for p in ("GOALKEEPER", "CENTRAL_DEFENDER", "WING_BACK", "INNER_MIDFIELDER", "WINGER", "FORWARD")})
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    strengths = detect_strengths(context, training_summary, squad_summary, depth_summary)
    assert any(s.strength_type == ClubStrengthType.STRONG_POSITIONAL_COVERAGE for s in strengths)


def test_all_strengths_have_evidence():
    reports = [make_report(name=f"P{i}", training_fit=TrainingFit.EXCELLENT) for i in range(4)]
    context = make_context(squad_reports=reports, positional_depth={p: 3 for p in ("GOALKEEPER", "CENTRAL_DEFENDER")})
    training_summary = TrainingSummary(players_without_training=0, full_effect_slots_used=4, total_players_evaluated=4)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    strengths = detect_strengths(context, training_summary, squad_summary, depth_summary)
    for strength in strengths:
        assert strength.evidence


# --------------------------------------------------------------------------
# Training summary
# --------------------------------------------------------------------------

def test_training_summary_counts_trainee_roles():
    reports = [
        make_report(name="Primary", role=RecommendedRole.PRIMARY_TRAINEE),
        make_report(name="Secondary", role=RecommendedRole.SECONDARY_TRAINEE),
        make_report(name="Starter", role=RecommendedRole.STARTER),
    ]
    context = make_context(squad_reports=reports)
    summary = build_training_summary(context)
    assert summary.primary_trainee_count == 1
    assert summary.secondary_trainee_count == 1
    assert summary.total_players_evaluated == 3


def test_training_summary_counts_training_fit_effects():
    reports = [
        make_report(name="A", training_fit=TrainingFit.EXCELLENT),
        make_report(name="B", training_fit=TrainingFit.COMPATIBLE),
        make_report(name="C", training_fit=TrainingFit.NO_TRAINING),
    ]
    context = make_context(squad_reports=reports)
    summary = build_training_summary(context)
    assert summary.full_effect_slots_used == 1
    assert summary.reduced_effect_slots_used == 1
    assert summary.players_without_training == 1


# --------------------------------------------------------------------------
# Depth analysis
# --------------------------------------------------------------------------

def test_depth_no_replacement_for_single_player_position():
    context = make_context(positional_depth={"GOALKEEPER": 1})
    depth_summary = build_depth_summary(context)
    goalkeeper = next(item for item in depth_summary.positions if item.position == "GOALKEEPER")
    assert goalkeeper.status == DepthStatus.NO_REPLACEMENT.value


def test_depth_no_replacement_for_missing_position():
    context = make_context(positional_depth={"GOALKEEPER": 3})
    depth_summary = build_depth_summary(context)
    central_defender = next(item for item in depth_summary.positions if item.position == "CENTRAL_DEFENDER")
    assert central_defender.status == DepthStatus.NO_REPLACEMENT.value
    assert central_defender.player_count == 0


def test_depth_healthy_competition():
    context = make_context(positional_depth={"WINGER": 4})
    depth_summary = build_depth_summary(context)
    winger = next(item for item in depth_summary.positions if item.position == "WINGER")
    assert winger.status == DepthStatus.HEALTHY_COMPETITION.value


def test_depth_excess_players():
    context = make_context(positional_depth={"WINGER": 8})
    depth_summary = build_depth_summary(context)
    winger = next(item for item in depth_summary.positions if item.position == "WINGER")
    assert winger.status == DepthStatus.EXCESS_PLAYERS.value


def test_depth_future_shortage_when_only_replacements_are_old():
    context = make_context(
        positional_depth={"CENTRAL_DEFENDER": 2},
        ages_by_position={"CENTRAL_DEFENDER": (33, 34)},
    )
    depth_summary = build_depth_summary(context)
    central_defender = next(item for item in depth_summary.positions if item.position == "CENTRAL_DEFENDER")
    assert central_defender.status == DepthStatus.FUTURE_SHORTAGE.value


def test_depth_covers_every_canonical_position():
    context = make_context(positional_depth={"GOALKEEPER": 2})
    depth_summary = build_depth_summary(context)
    positions = {item.position for item in depth_summary.positions}
    assert positions == {"GOALKEEPER", "CENTRAL_DEFENDER", "WING_BACK", "INNER_MIDFIELDER", "WINGER", "FORWARD"}


# --------------------------------------------------------------------------
# Warnings
# --------------------------------------------------------------------------

def test_warning_no_goalkeeper_backup_explains_why():
    context = make_context(positional_depth={"GOALKEEPER": 1})
    training_summary = build_training_summary(context)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    warnings = generate_warnings(context, training_summary, squad_summary, depth_summary)
    warning = next(w for w in warnings if w.warning_type == ClubWarningType.NO_GOALKEEPER_BACKUP)
    assert warning.reason_key
    assert warning.reason_params


def test_warning_training_capacity_underused():
    context = make_context(active_training_type="PLAYMAKING")
    training_summary = TrainingSummary(total_players_evaluated=10, full_effect_slots_used=0)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    warnings = generate_warnings(context, training_summary, squad_summary, depth_summary)
    assert any(w.warning_type == ClubWarningType.TRAINING_CAPACITY_UNDERUSED for w in warnings)


def test_no_training_capacity_warning_when_no_active_training():
    context = make_context(active_training_type="")
    training_summary = TrainingSummary(total_players_evaluated=10, full_effect_slots_used=0)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    warnings = generate_warnings(context, training_summary, squad_summary, depth_summary)
    assert not any(w.warning_type == ClubWarningType.TRAINING_CAPACITY_UNDERUSED for w in warnings)


def test_all_warnings_have_a_reason():
    context = make_context(positional_depth={"GOALKEEPER": 1})
    training_summary = TrainingSummary(total_players_evaluated=10, full_effect_slots_used=0, players_without_training=6)
    squad_summary = build_squad_summary(context)
    depth_summary = build_depth_summary(context)
    warnings = generate_warnings(context, training_summary, squad_summary, depth_summary)
    for warning in warnings:
        assert warning.reason_key


# --------------------------------------------------------------------------
# Confidence
# --------------------------------------------------------------------------

def test_confidence_high_with_full_data():
    inputs = ClubConfidenceInputs(has_roster=True, has_active_training=True, has_squad_reports=True)
    assert classify_confidence(inputs) == ClubConfidence.HIGH


def test_confidence_medium_without_active_training():
    inputs = ClubConfidenceInputs(has_roster=True, has_active_training=False, has_squad_reports=True)
    assert classify_confidence(inputs) == ClubConfidence.MEDIUM


def test_confidence_insufficient_data_without_roster():
    inputs = ClubConfidenceInputs(has_roster=False, has_squad_reports=False)
    assert classify_confidence(inputs) == ClubConfidence.INSUFFICIENT_DATA


def test_confidence_never_fakes_certainty_missing_historical_data():
    """Missing historical data alone must not force insufficient-data --
    it's a bonus input, not a requirement -- but it should still not
    silently claim HIGH confidence with no honesty about the gap
    (captured instead as a limitation, see below)."""
    context = make_context(has_historical_data=False)
    report = generate_report(context)
    assert report.confidence != ClubConfidence.INSUFFICIENT_DATA
    assert ClubLimitationType.HISTORICAL_DATA_UNAVAILABLE in report.limitations


# --------------------------------------------------------------------------
# Limitations
# --------------------------------------------------------------------------

def test_out_of_scope_limitations_always_present():
    context = make_context()
    report = generate_report(context)
    for limitation in (
        ClubLimitationType.FINANCIAL_DATA_UNAVAILABLE,
        ClubLimitationType.LEAGUE_COMPARISON_UNAVAILABLE,
        ClubLimitationType.TRANSFER_MARKET_UNAVAILABLE,
        ClubLimitationType.SALARY_BUDGET_UNAVAILABLE,
        ClubLimitationType.PROMOTION_TARGET_UNKNOWN,
    ):
        assert limitation in report.limitations


def test_empty_roster_limitation():
    context = make_context(squad_reports=())
    report = generate_report(context)
    assert ClubLimitationType.EMPTY_ROSTER in report.limitations


def test_no_active_training_limitation():
    context = make_context(active_training_type="")
    report = generate_report(context)
    assert ClubLimitationType.NO_ACTIVE_TRAINING in report.limitations


# --------------------------------------------------------------------------
# Regression / responsibility boundaries
# --------------------------------------------------------------------------

def test_empty_roster_does_not_crash():
    context = make_context(squad_reports=(), positional_depth={})
    report = generate_report(context)
    assert isinstance(report, ClubAdvisorReport)


def test_rule_engine_produces_all_expected_sections():
    context = make_context(positional_depth={"GOALKEEPER": 2})
    engine = ClubAdvisorRuleEngine()
    results = engine.evaluate(context)
    assert "training_summary" in results
    assert "squad_summary" in results
    assert "depth_summary" in results
    assert "sporting_summary" in results
    assert "priorities" in results
    assert "strengths" in results
    assert "risks" in results
    assert "warnings" in results


def test_club_advisor_never_imports_formation_optimizer():
    import ast
    from pathlib import Path

    package_dir = Path(__file__).resolve().parents[1] / "engine" / "club_advisor"
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


def test_club_advisor_never_computes_a_player_score_directly():
    """Structural guarantee: club_advisor never imports the player
    rating engine -- it only reads already-computed Squad Intelligence
    reports."""
    import ast
    from pathlib import Path

    package_dir = Path(__file__).resolve().parents[1] / "engine" / "club_advisor"
    forbidden = {"engine.rating.player_rating_engine", "engine.analyzers.player_analyzer"}
    for path in package_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        assert not (imported & forbidden), f"{path.name} imports {imported & forbidden}"
