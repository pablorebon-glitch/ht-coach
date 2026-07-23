import json
import subprocess
import sys

import pytest

from engine.history import (
    CompetitionType,
    HistoricalMatchQueryService,
    HistoricalMatchRepository,
    HistoricalSnapshotFactory,
    HomeAway,
    MatchContext,
    OpponentReference,
    PreviousMatchSelection,
    PreviousMatchSelector,
    SnapshotStage,
    TeamType,
    classify_match_cohort,
)
from engine.history.enums import (
    ComparisonSelectorType,
    HistoricalRatingSource,
    ScheduleGroup,
    SnapshotSource,
)
from engine.history.models import (
    HistoricalLineupEntry,
    HistoricalMatchSnapshot,
    OfficialResultSnapshot,
    PredictionSnapshot,
    SectorRatings,
    SnapshotProvenance,
    TacticalSetup,
)
from engine.history.query_service import HistoricalMatchQuery
from engine.history.repository import HistoricalMatchRepositoryError
from engine.history.serialization import (
    HistoricalSerializationError,
    repository_payload_to_json,
    snapshot_from_json,
    snapshot_to_json,
    snapshots_from_repository_payload,
)
from engine.history.validation import (
    enrich_with_official_result,
    ensure_valid_snapshot,
    validate_snapshot,
)
from ht_coach_app.services.historical_match_service import HistoricalMatchAppService
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    MatchAnalysisResult,
    TeamRatingsResult,
)


def sample_lineup():
    return (
        HistoricalLineupEntry(
            player_id="p1",
            player_name="Keeper One",
            number=1,
            position="GOALKEEPER",
            side="CENTER",
            individual_order="Normal",
        ),
        HistoricalLineupEntry(
            player_id="p2",
            player_name="Michael Rushton",
            number=10,
            position="FORWARD",
            side="CENTER",
            individual_order="Towards Wing",
            order_side="LEFT",
            form=7,
            stamina=8,
            experience=6,
        ),
    )


def sample_ratings(source=HistoricalRatingSource.HT_COACH_PREDICTED):
    return SectorRatings(
        source=source,
        scale="ht-coach-internal",
        right_defense=7.5,
        central_defense=8.0,
        left_defense=7.0,
        midfield=9.25,
        right_attack=6.5,
        central_attack=7.0,
        left_attack=8.5,
        indirect_defense=5.0,
        indirect_attack=5.5,
    )


def snapshot(
    snapshot_id="snap-1",
    match_date="2026-07-19",
    competition=CompetitionType.LEAGUE,
    stage=SnapshotStage.PLAYED,
    official=True,
    kickoff_time="21:00",
    opponent_name="Rival FC",
):
    context = MatchContext(
        official_match_id=f"match-{snapshot_id}",
        match_date=match_date,
        kickoff_time=kickoff_time,
        season="92",
        round="4",
        competition_type=competition,
        home_away=HomeAway.HOME,
        team_type=TeamType.FIRST_TEAM,
        opponent=OpponentReference(
            opponent_id=f"opp-{opponent_name}",
            opponent_name=opponent_name,
            country_or_region="AR",
            division_or_league="VI",
            notes="Pressed last time.",
        ),
        venue="HT Arena",
        snapshot_stage=stage,
    )
    official_result = None
    if official:
        official_result = OfficialResultSnapshot(
            goals_for=2,
            goals_against=1,
            ratings=sample_ratings(HistoricalRatingSource.HATTRICK_OFFICIAL),
            official_tactic="Pressing",
            official_tactic_level=8.0,
            possession=0.54,
            outcome="win",
            match_report_reference="https://hattrick.org/match/1",
            played_lineup=sample_lineup(),
        )
    return HistoricalMatchSnapshot(
        snapshot_id=snapshot_id,
        created_at="2026-07-18T20:00:00+00:00",
        updated_at="2026-07-18T20:00:00+00:00",
        source=SnapshotSource.MATCH_ANALYSIS,
        match_context=context,
        tactical_setup=TacticalSetup(
            formation="2-5-3",
            selected_tactic="Pressing",
            tactic_level=7.25,
            home_away=HomeAway.HOME,
            team_attitude="normal",
        ),
        lineup=sample_lineup(),
        predictions=PredictionSnapshot(
            ratings=sample_ratings(),
            possession=0.58,
            expected_goals=2.4,
            opponent_expected_goals=1.1,
            win_probability=0.61,
            draw_probability=0.23,
            loss_probability=0.16,
            recommended_tactic="Pressing",
            tactic_level=7.25,
            model_version="test-model",
            prediction_timestamp="2026-07-18T20:05:00+00:00",
        ),
        official_result=official_result,
        cohort=classify_match_cohort(context),
        provenance=SnapshotProvenance(
            source_application_version="0.5.8.2",
            source_engine_version="stable",
            imported_filename="players.csv",
            imported_match_id=f"match-{snapshot_id}",
            creation_workflow="test",
            roster_source="players.csv",
            opponent_source="opponents.json",
            notes="Fixture note.",
        ),
    )


def match_analysis_result():
    lineup = [
        LineupPlayerResult(1, "Goalkeeper (GK)", "CENTER", "Normal", "", "Keeper One"),
        LineupPlayerResult(10, "Forward (F)", "CENTER", "Towards Wing", "LEFT", "Michael Rushton"),
    ]
    formation = FormationAnalysisResult(
        formation_name="2-5-3",
        recommended_tactic="Pressing",
        tactic_level=7.25,
        win_probability=0.61,
        draw_probability=0.23,
        loss_probability=0.16,
        possession=0.58,
        expected_goals=2.4,
        opponent_expected_goals=1.1,
        lineup=lineup,
        is_recommended=True,
        team_ratings=TeamRatingsResult(
            left_defense=7.0,
            central_defense=8.0,
            right_defense=7.5,
            midfield=9.25,
            left_attack=8.5,
            central_attack=7.0,
            right_attack=6.5,
        ),
    )
    return MatchAnalysisResult(
        player_count=2,
        opponent_name="Rival FC",
        formations=[formation],
        players_csv_filename="players.csv",
        analyzed_formations=["2-5-3"],
        completed_at="2026-07-18T20:05:00+00:00",
    )


def test_complete_snapshot_round_trip_is_lossless_and_deterministic():
    original = snapshot()
    text = snapshot_to_json(original)
    restored = snapshot_from_json(text)

    assert restored == original
    assert json.loads(snapshot_to_json(restored)) == json.loads(text)
    assert snapshot_to_json(restored) == text
    assert restored.lineup[1].order_side == "LEFT"


def test_minimal_snapshot_round_trip_loads_optional_fields_safely():
    original = HistoricalMatchSnapshot(snapshot_id="minimal")
    restored = snapshot_from_json(snapshot_to_json(original))

    assert restored.snapshot_id == "minimal"
    assert restored.match_context.competition_type == CompetitionType.UNKNOWN
    assert restored.official_result is None
    assert restored.predictions.ratings is None


def test_serialization_rejects_corrupt_json_and_future_schema():
    with pytest.raises(HistoricalSerializationError):
        snapshot_from_json("{not-json")

    payload = snapshot().to_dict()
    payload["schema_version"] = 999

    with pytest.raises(ValueError, match="unsupported historical snapshot schema"):
        snapshot_from_json(json.dumps(payload))


def test_repository_save_update_delete_import_query_and_sorting(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "history.json")
    older = snapshot("old", "2026-07-05", CompetitionType.LEAGUE)
    newer = snapshot("new", "2026-07-12", CompetitionType.CUP)

    repository.save(newer)
    repository.save(older)

    assert [item.snapshot_id for item in repository.list_all()] == ["old", "new"]
    assert repository.get("old") == older
    assert repository.find_by_match_id("match-new") == newer

    updated = older.with_updates(
        tactical_setup=TacticalSetup(formation="3-5-2", selected_tactic="Normal")
    )
    repository.replace(updated)
    assert repository.get("old").tactical_setup.formation == "3-5-2"

    result = repository.import_snapshots([updated, newer], replace_existing=False)
    assert result == {"imported": 0, "skipped": ("old", "new")}

    league = repository.query(
        HistoricalMatchQuery(competition_type=CompetitionType.LEAGUE)
    )
    assert [item.snapshot_id for item in league] == ["old"]

    with_official = repository.query(HistoricalMatchQuery(has_official_ratings=True))
    assert [item.snapshot_id for item in with_official] == ["old", "new"]

    repository.delete("old")
    assert repository.get("old") is None
    assert [item.snapshot_id for item in repository.list_all()] == ["new"]


def test_repository_reports_corrupt_and_future_schema(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("{bad", encoding="utf-8")
    repository = HistoricalMatchRepository(path)

    with pytest.raises(HistoricalMatchRepositoryError, match="corrupt"):
        repository.list_all()

    path.write_text('{"schema_version": 99, "snapshots": []}', encoding="utf-8")
    with pytest.raises(HistoricalMatchRepositoryError, match="unsupported"):
        repository.list_all()


def test_repository_payload_round_trip_is_deterministic():
    snapshots = (snapshot("b", "2026-07-12"), snapshot("a", "2026-07-05"))
    text = repository_payload_to_json(snapshots)

    assert snapshots_from_repository_payload(text) == snapshots
    assert repository_payload_to_json(snapshots_from_repository_payload(text)) == text


def test_query_filters_every_supported_dimension():
    first = snapshot("first", "2026-07-05", CompetitionType.LEAGUE)
    second = snapshot(
        "second",
        "2026-07-09",
        CompetitionType.FRIENDLY,
        stage=SnapshotStage.PLANNED,
        official=False,
        opponent_name="Friendly FC",
    )
    service = HistoricalMatchQueryService()

    assert service.filter((first, second), HistoricalMatchQuery(date_to="2026-07-06")) == (first,)
    assert service.filter((first, second), HistoricalMatchQuery(opponent_name="friendly")) == (second,)
    assert service.filter((first, second), HistoricalMatchQuery(snapshot_stage=SnapshotStage.PLANNED)) == (second,)
    assert service.filter((first, second), HistoricalMatchQuery(has_predictions=True)) == (first, second)
    assert service.filter((first, second), HistoricalMatchQuery(has_official_ratings=False)) == (second,)
    assert service.filter((first, second), HistoricalMatchQuery(descending=True))[0] == second


@pytest.mark.parametrize(
    ("match_date", "competition", "expected"),
    [
        ("2026-07-19", CompetitionType.LEAGUE, ScheduleGroup.WEEKEND_COMPETITIVE),
        ("2026-07-22", CompetitionType.CUP, ScheduleGroup.MIDWEEK_COMPETITIVE),
        ("2026-07-23T23:30:00-03:00", CompetitionType.CUP, ScheduleGroup.MIDWEEK_COMPETITIVE),
        ("2026-07-20", CompetitionType.FRIENDLY, ScheduleGroup.FRIENDLY_OR_TRAINING),
        ("", CompetitionType.UNKNOWN, ScheduleGroup.UNKNOWN),
        ("2026-07-20", CompetitionType.UNKNOWN, ScheduleGroup.OTHER),
    ],
)
def test_cohort_classifier_is_deterministic(match_date, competition, expected):
    context = MatchContext(
        match_date=match_date,
        competition_type=competition,
        team_type=TeamType.FIRST_TEAM,
    )

    cohort = classify_match_cohort(context)

    assert cohort.competition_type == competition
    assert cohort.team_type == TeamType.FIRST_TEAM
    assert cohort.schedule_group == expected


def test_previous_match_selector_supports_selector_types_and_tie_breaking():
    current = snapshot("current", "2026-07-26", CompetitionType.LEAGUE)
    old_league = snapshot("old-league", "2026-07-12", CompetitionType.LEAGUE)
    old_cup = snapshot("old-cup", "2026-07-22", CompetitionType.CUP)
    old_friendly = snapshot("old-friendly", "2026-07-20", CompetitionType.FRIENDLY)
    planned = snapshot(
        "planned",
        "2026-07-25",
        CompetitionType.LEAGUE,
        stage=SnapshotStage.PLANNED,
        official=False,
    )
    tie_a = snapshot("tie-a", "2026-07-24", CompetitionType.LEAGUE, kickoff_time="21:00")
    tie_b = snapshot("tie-b", "2026-07-24", CompetitionType.LEAGUE, kickoff_time="21:00")
    candidates = (current, old_league, old_cup, old_friendly, planned, tie_a, tie_b)
    selector = PreviousMatchSelector()

    assert selector.select(current, candidates).snapshot_id == "tie-b"
    assert selector.select(
        current,
        candidates,
        PreviousMatchSelection(include_planned=True),
    ).snapshot_id == "planned"
    assert selector.select(
        current,
        candidates,
        PreviousMatchSelection(ComparisonSelectorType.PREVIOUS_CUP_MATCH),
    ) == old_cup
    assert selector.select(
        current,
        candidates,
        PreviousMatchSelection(ComparisonSelectorType.PREVIOUS_FRIENDLY),
    ) == old_friendly
    assert selector.select(
        current,
        candidates,
        PreviousMatchSelection(ComparisonSelectorType.PREVIOUS_FIRST_TEAM_MATCH),
    ).match_context.team_type == TeamType.FIRST_TEAM
    assert selector.select(
        current,
        candidates,
        PreviousMatchSelection(ComparisonSelectorType.PREVIOUS_SAME_COHORT),
    ).cohort == current.cohort
    assert selector.select(snapshot("alone", "2026-01-01"), candidates) is None


def test_snapshot_factory_preserves_authoritative_lineup_without_reoptimization(monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("workspace or optimizer should not be invoked")

    monkeypatch.setattr(
        "ht_coach_app.workspace.workspace_service.WorkspaceService.create",
        explode,
    )
    result = match_analysis_result()
    context = MatchContext(
        match_date="2026-07-19",
        competition_type=CompetitionType.LEAGUE,
        home_away=HomeAway.AWAY,
        team_type=TeamType.FIRST_TEAM,
        opponent=OpponentReference(opponent_name="Rival FC"),
        snapshot_stage=SnapshotStage.PLANNED,
    )

    historical = HistoricalSnapshotFactory().from_match_analysis(
        result,
        context=context,
        snapshot_id="from-analysis",
    )

    assert historical.snapshot_id == "from-analysis"
    assert historical.match_context.snapshot_stage == SnapshotStage.PLANNED
    assert historical.official_result is None
    assert historical.tactical_setup.formation == "2-5-3"
    assert historical.predictions.win_probability == 0.61
    assert historical.predictions.ratings.left_attack == 8.5
    assert historical.lineup[1].player_name == "Michael Rushton"
    assert historical.lineup[1].side == "CENTER"
    assert historical.lineup[1].individual_order == "Towards Wing"
    assert historical.lineup[1].order_side == "LEFT"


def test_app_service_persists_match_analysis_snapshot(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "history.json")
    service = HistoricalMatchAppService(repository=repository)

    saved = service.create_snapshot_from_match_analysis(
        match_analysis_result(),
        context=MatchContext(
            match_date="2026-07-19",
            competition_type=CompetitionType.LEAGUE,
            opponent=OpponentReference(opponent_name="Rival FC"),
        ),
        snapshot_id="app-service",
    )

    assert repository.get("app-service") == saved
    assert repository.get("app-service").lineup[1].order_side == "LEFT"


def test_planned_to_played_enrichment_preserves_prediction_identity_and_created_at():
    planned = snapshot(
        "planned-match",
        "2026-07-19",
        CompetitionType.LEAGUE,
        stage=SnapshotStage.PLANNED,
        official=False,
    )
    official = OfficialResultSnapshot(
        goals_for=3,
        goals_against=2,
        ratings=sample_ratings(HistoricalRatingSource.HATTRICK_OFFICIAL),
        outcome="win",
    )

    played = enrich_with_official_result(planned, official)

    assert played.snapshot_id == planned.snapshot_id
    assert played.created_at == planned.created_at
    assert played.updated_at != planned.updated_at
    assert played.predictions == planned.predictions
    assert played.official_result == official
    assert played.match_context.snapshot_stage == SnapshotStage.PLAYED


def test_validation_reports_bad_probabilities_duplicates_and_invalid_values():
    bad = HistoricalMatchSnapshot(
        snapshot_id="bad",
        match_context=MatchContext(snapshot_stage=SnapshotStage.PLAYED),
        lineup=(
            HistoricalLineupEntry(
                player_id="dup",
                player_name="A",
                number=1,
                position="NOPE",
                side="CENTER",
                individual_order="Normal",
            ),
            HistoricalLineupEntry(
                player_id="dup",
                player_name="B",
                number=1,
                position="FORWARD",
                side="BAD",
                individual_order="Teleport",
                order_side="WRONG",
            ),
        ),
        predictions=PredictionSnapshot(
            ratings=SectorRatings(left_attack=-1),
            win_probability=1.2,
        ),
    )

    errors = validate_snapshot(bad)
    fields = {error.field for error in errors}

    assert "predictions.win_probability" in fields
    assert "lineup.player_id" in fields
    assert "lineup[0].position" in fields
    assert "lineup[1].side" in fields
    assert "lineup[1].individual_order" in fields
    assert "lineup[1].order_side" in fields
    assert "predictions.ratings.left_attack" in fields
    assert "official_result" in fields

    with pytest.raises(ValueError):
        ensure_valid_snapshot(bad)


def test_history_cli_lists_validates_and_selects_previous(tmp_path):
    store = tmp_path / "history.json"
    repository = HistoricalMatchRepository(store)
    repository.save(snapshot("old", "2026-07-12"))
    repository.save(snapshot("current", "2026-07-19"))

    list_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "engine.history",
            "--store",
            str(store),
            "list",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    previous_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "engine.history",
            "--store",
            str(store),
            "previous",
            "current",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "old" in list_result.stdout
    assert previous_result.stdout.strip() == "old"
