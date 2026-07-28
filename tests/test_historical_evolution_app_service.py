from engine.history.enums import CompetitionType, SnapshotStage, TeamType
from engine.history.cohort_classifier import classify_match_cohort
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
from ht_coach_app.services.historical_evolution_formatting import (
    format_evolution_summary,
    format_overall_row,
    format_sector_rows,
    format_signed,
)
from ht_coach_app.services.historical_evolution_service import (
    HistoricalEvolutionAppService,
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


def test_format_signed_handles_missing_and_signed_values():
    assert format_signed(None) == "\u2014"
    assert format_signed(0.5) == "+0.50"
    assert format_signed(-0.25) == "-0.25"


def test_app_service_compares_with_previous_league(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "historical_matches.json")
    older = make_snapshot("2026-07-01", midfield=4.0)
    current = make_snapshot("2026-07-15", midfield=5.0)
    repository.save(older)
    repository.save(current)

    service = HistoricalEvolutionAppService(repository=repository)
    result = service.compare_with_previous_league(current.snapshot_id)

    assert result is not None
    assert result.previous_snapshot_id == older.snapshot_id
    rows = format_evolution_summary(result)
    labels = [label for label, _ in rows]
    assert "Midfield" in labels
    assert rows[-1][0] == "Overall"


def test_app_service_returns_none_when_snapshot_unknown(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "historical_matches.json")
    service = HistoricalEvolutionAppService(repository=repository)

    assert service.compare_with_previous_league("does-not-exist") is None


def test_app_service_returns_none_without_eligible_previous_match(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "historical_matches.json")
    only_snapshot = make_snapshot("2026-07-15", midfield=5.0)
    repository.save(only_snapshot)

    service = HistoricalEvolutionAppService(repository=repository)
    result = service.compare_with_previous_league(only_snapshot.snapshot_id)

    assert result is None


def test_app_service_exposes_all_comparison_policies(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "historical_matches.json")
    older = make_snapshot("2026-07-01", midfield=4.0)
    current = make_snapshot("2026-07-15", midfield=5.0)
    repository.save(older)
    repository.save(current)

    service = HistoricalEvolutionAppService(repository=repository)

    assert service.compare_with_previous(current.snapshot_id) is not None
    assert service.compare_with_previous_cup(current.snapshot_id) is None
    assert service.compare_with_previous_friendly(current.snapshot_id) is None
    assert service.compare_same_cohort(current.snapshot_id) is not None


def test_format_sector_rows_and_overall_row_shape():
    repository_result_previous = make_snapshot("2026-07-01", midfield=4.0)
    repository_result_current = make_snapshot("2026-07-15", midfield=5.0)
    from engine.history.evolution.comparison_engine import compare

    result = compare(repository_result_current, repository_result_previous)

    sector_rows = format_sector_rows(result)
    assert ("Midfield", "+1.00") in sector_rows

    overall_label, overall_value = format_overall_row(result)
    assert overall_label == "Overall"
    assert overall_value.startswith(("+", "-", "\u2014"))
