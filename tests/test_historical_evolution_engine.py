import pytest

from engine.history.cohort_classifier import classify_match_cohort
from engine.history.enums import CompetitionType, SnapshotStage, TeamType
from engine.history.evolution import (
    DEFAULT_TREND_THRESHOLDS,
    HistoricalEvolutionEngine,
    LineupChangeStatus,
    Trend,
    TrendThresholds,
    classify_trend,
    compare,
    ensure_comparable,
)
from engine.history.evolution.comparison_metrics import (
    absolute_delta,
    percentage_delta,
    safe_average,
)
from engine.history.evolution.comparison_validation import EvolutionComparisonError
from engine.history.models import (
    HistoricalLineupEntry,
    HistoricalMatchSnapshot,
    MatchContext,
    MatchCohort,
    OpponentReference,
    PredictionSnapshot,
    SectorRatings,
    TacticalSetup,
    stable_snapshot_id,
)


def make_ratings(**overrides):
    base = dict(
        midfield=5.0,
        right_defense=4.0,
        central_defense=4.0,
        left_defense=4.0,
        right_attack=3.0,
        central_attack=3.0,
        left_attack=3.0,
    )
    base.update(overrides)
    return SectorRatings(**base)


def make_entry(name, position="INNER_MIDFIELDER", side="CENTER", order="Normal",
                order_side="", number=1, player_id=None):
    return HistoricalLineupEntry(
        player_id=player_id if player_id is not None else f"id-{name}",
        player_name=name,
        number=number,
        position=position,
        side=side,
        individual_order=order,
        order_side=order_side,
    )


def make_snapshot(
    match_date="2026-07-01",
    competition_type=CompetitionType.LEAGUE,
    team_type=TeamType.FIRST_TEAM,
    formation="3-5-2",
    tactic="Normal",
    tactic_level=5.0,
    attitude="Normal",
    confidence="High",
    ratings=None,
    lineup=None,
    win_probability=0.6,
    draw_probability=0.25,
    loss_probability=0.15,
    expected_goals=1.5,
    opponent_expected_goals=1.0,
    possession=55.0,
    snapshot_stage=SnapshotStage.PLAYED,
    opponent_name="Rival FC",
):
    context = MatchContext(
        match_date=match_date,
        competition_type=competition_type,
        team_type=team_type,
        snapshot_stage=snapshot_stage,
        opponent=OpponentReference(opponent_name=opponent_name),
    )
    return HistoricalMatchSnapshot(
        snapshot_id=stable_snapshot_id(),
        match_context=context,
        cohort=classify_match_cohort(context),
        tactical_setup=TacticalSetup(
            formation=formation,
            selected_tactic=tactic,
            tactic_level=tactic_level,
            team_attitude=attitude,
            confidence=confidence,
        ),
        predictions=PredictionSnapshot(
            ratings=ratings if ratings is not None else make_ratings(),
            win_probability=win_probability,
            draw_probability=draw_probability,
            loss_probability=loss_probability,
            expected_goals=expected_goals,
            opponent_expected_goals=opponent_expected_goals,
            possession=possession,
        ),
        lineup=tuple(lineup) if lineup is not None else (
            make_entry("Alice", number=1),
            make_entry("Bob", number=2),
            make_entry("Carol", number=3),
        ),
    )


# --------------------------------------------------------------------------
# Metrics primitives
# --------------------------------------------------------------------------

def test_absolute_delta_basic():
    assert absolute_delta(4.0, 6.0) == 2.0
    assert absolute_delta(6.0, 4.0) == -2.0


def test_absolute_delta_missing_values():
    assert absolute_delta(None, 6.0) is None
    assert absolute_delta(4.0, None) is None
    assert absolute_delta(None, None) is None


def test_percentage_delta_basic():
    assert percentage_delta(4.0, 5.0) == 25.0
    assert percentage_delta(4.0, 3.0) == -25.0


def test_percentage_delta_zero_previous_is_undefined():
    assert percentage_delta(0.0, 5.0) is None


def test_safe_average_ignores_none():
    assert safe_average([1.0, None, 3.0]) == 2.0
    assert safe_average([None, None]) is None


def test_trend_classification_bands():
    thresholds = TrendThresholds(unchanged_band=1.0, major_band=10.0)
    assert classify_trend(0.5, thresholds) == Trend.UNCHANGED
    assert classify_trend(5.0, thresholds) == Trend.IMPROVEMENT
    assert classify_trend(15.0, thresholds) == Trend.MAJOR_IMPROVEMENT
    assert classify_trend(-5.0, thresholds) == Trend.DECLINE
    assert classify_trend(-15.0, thresholds) == Trend.MAJOR_DECLINE
    assert classify_trend(None, thresholds) == Trend.UNCHANGED


def test_trend_thresholds_reject_invalid_bands():
    with pytest.raises(ValueError):
        TrendThresholds(unchanged_band=-1.0)
    with pytest.raises(ValueError):
        TrendThresholds(unchanged_band=5.0, major_band=1.0)


def test_trend_thresholds_round_trip():
    thresholds = TrendThresholds(unchanged_band=2.0, major_band=20.0)
    restored = TrendThresholds.from_dict(thresholds.to_dict())
    assert restored == thresholds
    assert TrendThresholds.from_dict(None) == DEFAULT_TREND_THRESHOLDS


def test_sector_evolution_round_trip():
    from engine.history.evolution.comparison_models import SectorEvolution

    original = SectorEvolution(
        sector="midfield",
        previous_value=4.0,
        current_value=5.0,
        absolute_delta=1.0,
        percentage_delta=25.0,
        trend=Trend.IMPROVEMENT,
    )
    restored = SectorEvolution.from_dict(original.to_dict())
    assert restored == original


# --------------------------------------------------------------------------
# Validation / guardrails
# --------------------------------------------------------------------------

def test_ensure_comparable_rejects_missing_snapshots():
    snapshot = make_snapshot()
    with pytest.raises(EvolutionComparisonError):
        ensure_comparable(None, snapshot)
    with pytest.raises(EvolutionComparisonError):
        ensure_comparable(snapshot, None)


def test_ensure_comparable_rejects_comparing_snapshot_to_itself():
    snapshot = make_snapshot()
    with pytest.raises(EvolutionComparisonError):
        ensure_comparable(snapshot, snapshot)


def test_compare_raises_through_validation():
    snapshot = make_snapshot()
    with pytest.raises(EvolutionComparisonError):
        compare(snapshot, None)


# --------------------------------------------------------------------------
# Identical snapshots
# --------------------------------------------------------------------------

def test_identical_snapshots_produce_no_evolution():
    ratings = make_ratings()
    lineup = (make_entry("Alice", number=1), make_entry("Bob", number=2))
    previous = make_snapshot(match_date="2026-07-01", ratings=ratings, lineup=lineup)
    current = make_snapshot(match_date="2026-07-08", ratings=ratings, lineup=lineup)

    result = compare(current, previous)

    assert all(sector.trend == Trend.UNCHANGED for sector in result.sectors)
    assert all(sector.absolute_delta == 0 for sector in result.sectors)
    assert result.overall.overall_trend == Trend.UNCHANGED
    assert result.overall.improved_sector_count == 0
    assert result.overall.declined_sector_count == 0
    assert result.overall.unchanged_sector_count == len(result.sectors)
    assert result.evolution_score == 0.0
    assert not result.formation.changed
    assert not result.tactical.tactic_changed
    assert result.lineup.players_added == ()
    assert result.lineup.players_removed == ()
    assert len(result.lineup.players_kept) == 2
    assert all(not c.position_changed for c in result.lineup.players_kept)


# --------------------------------------------------------------------------
# Sector improvements / declines
# --------------------------------------------------------------------------

def test_sector_improvement_is_classified_and_deltas_are_correct():
    previous = make_snapshot(ratings=make_ratings(midfield=4.0))
    current = make_snapshot(ratings=make_ratings(midfield=5.0))

    result = compare(current, previous)
    midfield = next(s for s in result.sectors if s.sector == "midfield")

    assert midfield.previous_value == 4.0
    assert midfield.current_value == 5.0
    assert midfield.absolute_delta == 1.0
    assert midfield.percentage_delta == 25.0
    assert midfield.trend == Trend.MAJOR_IMPROVEMENT
    assert result.overall.improved_sector_count == 1
    assert result.overall.best_improved_sector == "midfield"


def test_sector_decline_is_classified_and_deltas_are_correct():
    previous = make_snapshot(ratings=make_ratings(central_attack=6.0))
    current = make_snapshot(ratings=make_ratings(central_attack=4.5))

    result = compare(current, previous)
    sector = next(s for s in result.sectors if s.sector == "central_attack")

    assert sector.absolute_delta == -1.5
    assert sector.trend in (Trend.DECLINE, Trend.MAJOR_DECLINE)
    assert result.overall.declined_sector_count == 1
    assert result.overall.worst_sector == "central_attack"


def test_overall_rating_delta_sums_comparable_sector_deltas():
    previous = make_snapshot(ratings=make_ratings(midfield=4.0, right_attack=3.0))
    current = make_snapshot(ratings=make_ratings(midfield=5.0, right_attack=4.0))

    result = compare(current, previous)

    assert result.overall.overall_rating_delta == pytest.approx(2.0)


def test_custom_thresholds_change_classification():
    previous = make_snapshot(ratings=make_ratings(midfield=4.0))
    current = make_snapshot(ratings=make_ratings(midfield=4.2))  # +5%

    loose = TrendThresholds(unchanged_band=10.0, major_band=50.0)
    result = compare(current, previous, thresholds=loose)
    midfield = next(s for s in result.sectors if s.sector == "midfield")

    assert midfield.trend == Trend.UNCHANGED


# --------------------------------------------------------------------------
# Formation evolution
# --------------------------------------------------------------------------

def test_formation_change_detected():
    previous = make_snapshot(formation="3-5-2")
    current = make_snapshot(formation="4-4-2")

    result = compare(current, previous)

    assert result.formation.changed
    assert result.formation.previous_formation == "3-5-2"
    assert result.formation.current_formation == "4-4-2"


def test_formation_unchanged_detected():
    previous = make_snapshot(formation="4-5-1")
    current = make_snapshot(formation="4-5-1")

    result = compare(current, previous)

    assert not result.formation.changed


# --------------------------------------------------------------------------
# Tactical evolution
# --------------------------------------------------------------------------

def test_tactic_change_detected():
    previous = make_snapshot(tactic="Normal", tactic_level=3.0, attitude="Normal", confidence="Medium")
    current = make_snapshot(tactic="Pressing", tactic_level=6.0, attitude="Attacking", confidence="High")

    result = compare(current, previous)

    assert result.tactical.tactic_changed
    assert result.tactical.previous_tactic == "Normal"
    assert result.tactical.current_tactic == "Pressing"
    assert result.tactical.tactic_level_delta == pytest.approx(3.0)
    assert result.tactical.attitude_changed
    assert result.tactical.confidence_changed


def test_tactic_unchanged_detected():
    previous = make_snapshot(tactic="Normal", attitude="Normal", confidence="High")
    current = make_snapshot(tactic="Normal", attitude="Normal", confidence="High")

    result = compare(current, previous)

    assert not result.tactical.tactic_changed
    assert not result.tactical.attitude_changed
    assert not result.tactical.confidence_changed
    assert result.tactical.tactic_level_delta == 0


# --------------------------------------------------------------------------
# Lineup evolution: reorder, replacement, order change, order-side change
# --------------------------------------------------------------------------

def test_lineup_reorder_does_not_register_as_a_change():
    previous_lineup = (
        make_entry("Alice", number=1, player_id="p1"),
        make_entry("Bob", number=2, player_id="p2"),
        make_entry("Carol", number=3, player_id="p3"),
    )
    # Same players, different order in the list (row order must not matter).
    current_lineup = (
        make_entry("Carol", number=3, player_id="p3"),
        make_entry("Alice", number=1, player_id="p1"),
        make_entry("Bob", number=2, player_id="p2"),
    )
    previous = make_snapshot(lineup=previous_lineup)
    current = make_snapshot(lineup=current_lineup)

    result = compare(current, previous)

    assert result.lineup.players_added == ()
    assert result.lineup.players_removed == ()
    assert len(result.lineup.players_kept) == 3
    assert all(not c.position_changed for c in result.lineup.players_kept)
    assert all(not c.number_changed for c in result.lineup.players_kept)


def test_lineup_player_replacement_detected():
    previous_lineup = (
        make_entry("Alice", number=1, player_id="p1"),
        make_entry("Bob", number=2, player_id="p2"),
    )
    current_lineup = (
        make_entry("Alice", number=1, player_id="p1"),
        make_entry("Dave", number=2, player_id="p4"),
    )
    previous = make_snapshot(lineup=previous_lineup)
    current = make_snapshot(lineup=current_lineup)

    result = compare(current, previous)

    assert [c.player_name for c in result.lineup.players_added] == ["Dave"]
    assert [c.player_name for c in result.lineup.players_removed] == ["Bob"]
    assert [c.player_name for c in result.lineup.players_kept] == ["Alice"]


def test_lineup_position_change_detected():
    previous_lineup = (make_entry("Alice", position="WINGER", side="LEFT", player_id="p1"),)
    current_lineup = (make_entry("Alice", position="INNER_MIDFIELDER", side="CENTER", player_id="p1"),)
    previous = make_snapshot(lineup=previous_lineup)
    current = make_snapshot(lineup=current_lineup)

    result = compare(current, previous)

    assert len(result.lineup.position_changes) == 1
    change = result.lineup.position_changes[0]
    assert change.previous_position == "WINGER"
    assert change.current_position == "INNER_MIDFIELDER"


def test_lineup_order_change_detected():
    previous_lineup = (make_entry("Alice", order="Normal", player_id="p1"),)
    current_lineup = (make_entry("Alice", order="Offensive", player_id="p1"),)
    previous = make_snapshot(lineup=previous_lineup)
    current = make_snapshot(lineup=current_lineup)

    result = compare(current, previous)

    assert len(result.lineup.order_changes) == 1
    assert result.lineup.order_changes[0].previous_order == "Normal"
    assert result.lineup.order_changes[0].current_order == "Offensive"


def test_lineup_order_side_change_detected():
    previous_lineup = (
        make_entry("Michael", order="Towards Wing", order_side="LEFT", player_id="p9"),
    )
    current_lineup = (
        make_entry("Michael", order="Towards Wing", order_side="RIGHT", player_id="p9"),
    )
    previous = make_snapshot(lineup=previous_lineup)
    current = make_snapshot(lineup=current_lineup)

    result = compare(current, previous)

    assert len(result.lineup.order_side_changes) == 1
    assert result.lineup.order_side_changes[0].previous_order_side == "LEFT"
    assert result.lineup.order_side_changes[0].current_order_side == "RIGHT"


def test_lineup_shirt_number_change_detected():
    previous_lineup = (make_entry("Alice", number=7, player_id="p1"),)
    current_lineup = (make_entry("Alice", number=10, player_id="p1"),)
    previous = make_snapshot(lineup=previous_lineup)
    current = make_snapshot(lineup=current_lineup)

    result = compare(current, previous)

    assert len(result.lineup.number_changes) == 1
    assert result.lineup.number_changes[0].previous_number == 7
    assert result.lineup.number_changes[0].current_number == 10


def test_lineup_matches_by_name_when_player_id_missing():
    previous_lineup = (make_entry("Alice", player_id="", number=1),)
    current_lineup = (make_entry("Alice", player_id="", number=1),)
    previous = make_snapshot(lineup=previous_lineup)
    current = make_snapshot(lineup=current_lineup)

    result = compare(current, previous)

    assert len(result.lineup.players_kept) == 1
    assert result.lineup.players_added == ()
    assert result.lineup.players_removed == ()


def test_empty_lineups_produce_no_changes():
    previous = make_snapshot(lineup=())
    current = make_snapshot(lineup=())

    result = compare(current, previous)

    assert result.lineup.changes == ()


# --------------------------------------------------------------------------
# Prediction evolution
# --------------------------------------------------------------------------

def test_prediction_evolution_deltas():
    previous = make_snapshot(
        win_probability=0.4, draw_probability=0.3, loss_probability=0.3,
        expected_goals=1.0, opponent_expected_goals=1.2, possession=48.0,
    )
    current = make_snapshot(
        win_probability=0.6, draw_probability=0.25, loss_probability=0.15,
        expected_goals=1.8, opponent_expected_goals=0.9, possession=55.0,
    )

    result = compare(current, previous)

    assert result.prediction.win_probability.previous == 0.4
    assert result.prediction.win_probability.current == 0.6
    assert result.prediction.win_probability.delta == pytest.approx(0.2)
    assert result.prediction.expected_goals.delta == pytest.approx(0.8)
    assert result.prediction.opponent_expected_goals.delta == pytest.approx(-0.3)
    assert result.prediction.possession.delta == pytest.approx(7.0)


# --------------------------------------------------------------------------
# Missing optional data / unknown fields
# --------------------------------------------------------------------------

def test_missing_ratings_on_previous_snapshot_does_not_crash():
    previous = make_snapshot(ratings=SectorRatings())
    current = make_snapshot(ratings=make_ratings(midfield=6.0))

    result = compare(current, previous)
    midfield = next(s for s in result.sectors if s.sector == "midfield")

    assert midfield.previous_value is None
    assert midfield.current_value == 6.0
    assert midfield.absolute_delta is None
    assert midfield.trend == Trend.UNCHANGED


def test_missing_predictions_entirely_does_not_crash():
    previous = make_snapshot()
    current = make_snapshot()
    current = current.with_updates(predictions=PredictionSnapshot())

    result = compare(current, previous)

    assert result.prediction.win_probability.current is None
    assert all(s.current_value is None for s in result.sectors)


def test_missing_tactical_level_does_not_crash():
    previous = make_snapshot(tactic_level=None)
    current = make_snapshot(tactic_level=5.0)

    result = compare(current, previous)

    assert result.tactical.previous_tactic_level is None
    assert result.tactical.tactic_level_delta is None


def test_unknown_optional_fields_are_ignored_gracefully():
    # Extra/unknown fields arriving via a loosely-typed dict round trip
    # (e.g. an older or newer schema) should not break comparison, since
    # the engine only ever reads the fields it knows about.
    previous = make_snapshot()
    current = make_snapshot()
    data = current.to_dict()
    data["some_future_field"] = {"nested": True}
    data["match_context"]["some_future_field"] = "ignored"
    rehydrated = HistoricalMatchSnapshot.from_dict(
        {k: v for k, v in data.items() if k != "some_future_field"}
    )

    result = compare(rehydrated, previous)
    assert result is not None


# --------------------------------------------------------------------------
# Comparison policies: previous match / league / cup / friendly / cohort
# --------------------------------------------------------------------------

def test_compare_with_previous_picks_most_recent_earlier_match():
    engine = HistoricalEvolutionEngine()
    current = make_snapshot(match_date="2026-07-20")
    older = make_snapshot(match_date="2026-07-01")
    newer_but_still_earlier = make_snapshot(match_date="2026-07-15")

    result = engine.compare_with_previous(current, [older, newer_but_still_earlier])

    assert result.previous_snapshot_id == newer_but_still_earlier.snapshot_id


def test_compare_with_previous_ignores_future_snapshots():
    engine = HistoricalEvolutionEngine()
    current = make_snapshot(match_date="2026-07-10")
    future = make_snapshot(match_date="2026-07-20")

    result = engine.compare_with_previous(current, [future])

    assert result is None


def test_compare_with_previous_league_filters_by_competition():
    engine = HistoricalEvolutionEngine()
    current = make_snapshot(match_date="2026-07-20", competition_type=CompetitionType.LEAGUE)
    cup_match = make_snapshot(match_date="2026-07-15", competition_type=CompetitionType.CUP)
    league_match = make_snapshot(match_date="2026-07-10", competition_type=CompetitionType.LEAGUE)

    result = engine.compare_with_previous_league(current, [cup_match, league_match])

    assert result.previous_snapshot_id == league_match.snapshot_id


def test_compare_with_previous_cup_filters_by_competition():
    engine = HistoricalEvolutionEngine()
    current = make_snapshot(match_date="2026-07-20", competition_type=CompetitionType.CUP)
    league_match = make_snapshot(match_date="2026-07-15", competition_type=CompetitionType.LEAGUE)
    cup_match = make_snapshot(match_date="2026-07-10", competition_type=CompetitionType.CUP)

    result = engine.compare_with_previous_cup(current, [league_match, cup_match])

    assert result.previous_snapshot_id == cup_match.snapshot_id


def test_compare_with_previous_friendly_filters_by_competition():
    engine = HistoricalEvolutionEngine()
    current = make_snapshot(match_date="2026-07-20", competition_type=CompetitionType.FRIENDLY)
    league_match = make_snapshot(match_date="2026-07-15", competition_type=CompetitionType.LEAGUE)
    friendly = make_snapshot(match_date="2026-07-10", competition_type=CompetitionType.FRIENDLY)

    result = engine.compare_with_previous_friendly(current, [league_match, friendly])

    assert result.previous_snapshot_id == friendly.snapshot_id


def test_compare_same_cohort_requires_matching_cohort():
    engine = HistoricalEvolutionEngine()
    current = make_snapshot(match_date="2026-07-20", competition_type=CompetitionType.LEAGUE)
    same_cohort_candidate = make_snapshot(
        match_date="2026-07-13", competition_type=CompetitionType.LEAGUE
    )
    different_cohort_candidate = make_snapshot(
        match_date="2026-07-14", competition_type=CompetitionType.CUP
    )

    result = engine.compare_same_cohort(
        current, [same_cohort_candidate, different_cohort_candidate]
    )

    assert result is not None
    assert result.previous_snapshot_id == same_cohort_candidate.snapshot_id


def test_different_competitions_are_not_selected_as_previous_league():
    engine = HistoricalEvolutionEngine()
    current = make_snapshot(match_date="2026-07-20", competition_type=CompetitionType.LEAGUE)
    only_cup = make_snapshot(match_date="2026-07-10", competition_type=CompetitionType.CUP)

    result = engine.compare_with_previous_league(current, [only_cup])

    assert result is None


def test_compare_excludes_itself_from_candidates():
    engine = HistoricalEvolutionEngine()
    current = make_snapshot(match_date="2026-07-20")

    result = engine.compare_with_previous(current, [current])

    assert result is None


def test_planned_snapshots_excluded_unless_requested():
    engine = HistoricalEvolutionEngine()
    current = make_snapshot(match_date="2026-07-20")
    planned = make_snapshot(match_date="2026-07-10", snapshot_stage=SnapshotStage.PLANNED)

    assert engine.compare_with_previous(current, [planned]) is None
    assert engine.compare_with_previous(
        current, [planned], include_planned=True
    ) is not None


def test_compare_with_previous_cup_returns_none_when_no_cup_match_exists():
    engine = HistoricalEvolutionEngine()
    current = make_snapshot(match_date="2026-07-20", competition_type=CompetitionType.CUP)
    only_league = make_snapshot(match_date="2026-07-10", competition_type=CompetitionType.LEAGUE)

    assert engine.compare_with_previous_cup(current, [only_league]) is None


def test_compare_with_previous_friendly_returns_none_when_no_friendly_exists():
    engine = HistoricalEvolutionEngine()
    current = make_snapshot(match_date="2026-07-20", competition_type=CompetitionType.FRIENDLY)
    only_league = make_snapshot(match_date="2026-07-10", competition_type=CompetitionType.LEAGUE)

    assert engine.compare_with_previous_friendly(current, [only_league]) is None


def test_compare_same_cohort_returns_none_when_no_matching_cohort_exists():
    engine = HistoricalEvolutionEngine()
    current = make_snapshot(match_date="2026-07-20", competition_type=CompetitionType.LEAGUE)
    only_cup = make_snapshot(match_date="2026-07-10", competition_type=CompetitionType.CUP)

    assert engine.compare_same_cohort(current, [only_cup]) is None


def test_compare_custom_with_explicit_competition_and_team_type():
    engine = HistoricalEvolutionEngine()
    current = make_snapshot(
        match_date="2026-07-20",
        competition_type=CompetitionType.LEAGUE,
        team_type=TeamType.FIRST_TEAM,
    )
    matching = make_snapshot(
        match_date="2026-07-10",
        competition_type=CompetitionType.LEAGUE,
        team_type=TeamType.FIRST_TEAM,
    )
    non_matching = make_snapshot(
        match_date="2026-07-15",
        competition_type=CompetitionType.CUP,
        team_type=TeamType.FIRST_TEAM,
    )

    result = engine.compare_custom(
        current,
        [matching, non_matching],
        competition_type=CompetitionType.LEAGUE,
        team_type=TeamType.FIRST_TEAM,
    )

    assert result.previous_snapshot_id == matching.snapshot_id


def test_compare_custom_returns_none_without_eligible_candidates():
    engine = HistoricalEvolutionEngine()
    current = make_snapshot(match_date="2026-07-20", competition_type=CompetitionType.LEAGUE)
    only_cup = make_snapshot(match_date="2026-07-10", competition_type=CompetitionType.CUP)

    result = engine.compare_custom(
        current, [only_cup], competition_type=CompetitionType.LEAGUE
    )

    assert result is None


# --------------------------------------------------------------------------
# Result serialization
# --------------------------------------------------------------------------

def test_result_to_dict_is_json_serializable():
    import json

    previous = make_snapshot()
    current = make_snapshot(ratings=make_ratings(midfield=6.0), formation="4-4-2")

    result = compare(current, previous)
    payload = json.dumps(result.to_dict())

    assert "evolution_score" in payload
    assert "sectors" in payload
