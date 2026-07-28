from engine.history.cohort_classifier import classify_match_cohort
from engine.history.enums import CompetitionType, SnapshotStage, TeamType
from engine.history.models import (
    HistoricalMatchSnapshot,
    MatchContext,
    OpponentReference,
    PredictionSnapshot,
    SectorRatings,
    TacticalSetup,
    stable_snapshot_id,
)
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.services.historical_insights_formatting import (
    format_evidence_summary,
    high_priority_insights,
    other_insights,
    visual_hierarchy,
)
from ht_coach_app.services.historical_insights_service import (
    HistoricalInsightsAppService,
)


def make_snapshot(match_date, midfield, competition_type=CompetitionType.LEAGUE):
    context = MatchContext(
        match_date=match_date,
        competition_type=competition_type,
        team_type=TeamType.FIRST_TEAM,
        snapshot_stage=SnapshotStage.PLAYED,
        opponent=OpponentReference(opponent_name="Rival FC"),
    )
    return HistoricalMatchSnapshot(
        snapshot_id=stable_snapshot_id(),
        match_context=context,
        cohort=classify_match_cohort(context),
        tactical_setup=TacticalSetup(formation="3-5-2", selected_tactic="Normal"),
        predictions=PredictionSnapshot(
            ratings=SectorRatings(
                midfield=midfield,
                right_defense=4.0,
                central_defense=4.0,
                left_defense=4.0,
                right_attack=3.0,
                central_attack=3.0,
                left_attack=3.0,
            ),
            win_probability=0.5,
        ),
    )


def test_app_service_compares_with_previous_league_and_generates_insights(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "historical_matches.json")
    older = make_snapshot("2026-07-01", midfield=4.0)
    current = make_snapshot("2026-07-15", midfield=8.0)
    repository.save(older)
    repository.save(current)

    service = HistoricalInsightsAppService(repository=repository)
    result = service.compare_with_previous_league(current.snapshot_id)

    assert result is not None
    assert result.previous_snapshot_id == older.snapshot_id
    assert any(i.rule_id == "sector.midfield_improvement" for i in result.insights)
    assert (
        result.summary.comparison_target_key
        == "insight.comparison_target.previous_league_match"
    )


def test_app_service_returns_none_for_unknown_snapshot(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "historical_matches.json")
    service = HistoricalInsightsAppService(repository=repository)

    assert service.compare_with_previous_league("missing") is None


def test_app_service_returns_none_without_eligible_previous_match(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "historical_matches.json")
    only_snapshot = make_snapshot("2026-07-15", midfield=6.0)
    repository.save(only_snapshot)

    service = HistoricalInsightsAppService(repository=repository)
    assert service.compare_with_previous_league(only_snapshot.snapshot_id) is None


def test_app_service_custom_comparison(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "historical_matches.json")
    older = make_snapshot("2026-07-01", midfield=4.0)
    current = make_snapshot("2026-07-15", midfield=8.0)
    repository.save(older)
    repository.save(current)

    service = HistoricalInsightsAppService(repository=repository)
    result = service.compare_with_custom_snapshot(current.snapshot_id, older.snapshot_id)

    assert result is not None
    assert result.summary.comparison_target_key == "insight.comparison_target.custom"


def test_app_service_custom_comparison_returns_none_for_unknown_snapshot(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "historical_matches.json")
    current = make_snapshot("2026-07-15", midfield=8.0)
    repository.save(current)

    service = HistoricalInsightsAppService(repository=repository)
    assert service.compare_with_custom_snapshot(current.snapshot_id, "missing") is None


def test_app_service_exposes_all_comparison_policies(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "historical_matches.json")
    older = make_snapshot("2026-07-01", midfield=4.0)
    current = make_snapshot("2026-07-15", midfield=8.0)
    repository.save(older)
    repository.save(current)

    service = HistoricalInsightsAppService(repository=repository)

    assert service.compare_with_previous(current.snapshot_id) is not None
    assert service.compare_with_previous_cup(current.snapshot_id) is None
    assert service.compare_with_previous_friendly(current.snapshot_id) is None
    assert service.compare_same_cohort(current.snapshot_id) is not None


def test_visual_hierarchy_buckets_by_severity(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "historical_matches.json")
    older = make_snapshot("2026-07-01", midfield=4.0)
    current = make_snapshot("2026-07-15", midfield=8.0)
    repository.save(older)
    repository.save(current)

    service = HistoricalInsightsAppService(repository=repository)
    result = service.compare_with_previous_league(current.snapshot_id)

    hierarchy = visual_hierarchy(result)
    assert hierarchy["summary"] is result.summary
    assert set(hierarchy) == {"summary", "high_priority", "other", "limitations"}
    assert len(hierarchy["high_priority"]) + len(hierarchy["other"]) == len(
        result.insights
    )


def test_high_priority_and_other_insights_are_disjoint(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "historical_matches.json")
    older = make_snapshot("2026-07-01", midfield=4.0)
    current = make_snapshot("2026-07-15", midfield=8.0)
    repository.save(older)
    repository.save(current)

    service = HistoricalInsightsAppService(repository=repository)
    result = service.compare_with_previous_league(current.snapshot_id)

    high = set(i.rule_id for i in high_priority_insights(result.insights))
    other = set(i.rule_id for i in other_insights(result.insights))
    assert high.isdisjoint(other)


def test_format_evidence_summary_shape(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "historical_matches.json")
    older = make_snapshot("2026-07-01", midfield=4.0)
    current = make_snapshot("2026-07-15", midfield=8.0)
    repository.save(older)
    repository.save(current)

    service = HistoricalInsightsAppService(repository=repository)
    result = service.compare_with_previous_league(current.snapshot_id)
    midfield_insight = next(
        i for i in result.insights if i.rule_id == "sector.midfield_improvement"
    )

    rows = format_evidence_summary(midfield_insight)
    assert rows[0][0] == "midfield"
    assert rows[0][1] == 4.0
    assert rows[0][2] == 8.0
