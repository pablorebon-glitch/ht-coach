from dataclasses import replace
from datetime import date

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.weekly_training.models import MatchRole, MatchStatus, TrainingPriority
from engine.weekly_training.persistence import WeeklyTrainingRepository, WeeklyTrainingState
from engine.weekly_training.player_identity import player_training_id
from engine.weekly_training.training_rules import PlaymakingTrainingRules, assumed_confidence
from engine.weekly_training.training_week import active_training_week
from engine.history.models import HistoricalMatchSnapshot, MatchContext, OpponentReference
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from ht_coach_app.views.squad_page import SquadPage
from tests.test_weekly_training_planner import (
    coverage_row_for_player,
    entry_for,
    player,
    played_record,
    roster,
)


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def _service(tmp_path):
    return WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )


def _symbol_for(row):
    if row.confirmed_exposure + row.assumed_exposure > 0:
        return "✓"
    if row.planned_exposure > 0:
        return "○"
    return "—"


def _replace_player_in_trainable_slot(board, replacement):
    slot = next(
        item
        for item in board.slots
        if item.player is not None
        and item.player.position in {"INNER_MIDFIELDER", "WINGER"}
    )
    card = replace(
        slot.player,
        player_id=player_training_id(replacement),
        player_name=replacement.name,
        display_name=replacement.name,
    )
    slots = tuple(
        replace(item, player=card)
        if item.slot_id == slot.slot_id
        else item
        for item in board.slots
    )
    return replace(board, slots=slots), slot.player.player_id


def test_replacing_linked_match_lineup_removes_prior_player_participation(tmp_path):
    service = _service(tmp_path)
    week = service.load_state().active_week
    players = roster() + [player("Replacement IM", playmaking=10)]
    replacement = players[-1]
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    plan = service.generate_plan(players, "3-5-2")
    saved = service.record_first_match(
        service.board_for_plan(plan),
        roster_players=players,
        match_date=week.first_match_date,
        requested_status=MatchStatus.PLAYED,
        today=week.first_match_date,
        linked_match_record_id="saved-match-1",
    )
    original = saved.match_records[0]
    changed_board, removed_player_id = _replace_player_in_trainable_slot(
        service.board_for_record(original),
        replacement,
    )

    updated = service.replace_linked_match_lineup(
        "saved-match-1",
        changed_board,
        roster_players=players,
        match_date=original.match_date,
        requested_status=original.planned_or_played,
        played_confirmed=True,
        today=week.first_match_date,
    )

    assert len(updated.match_records) == 1
    record = updated.match_records[0]
    assert record.match_id == original.match_id
    assert removed_player_id not in {
        exposure.player_id for exposure in record.training_exposure_entries
    }
    replacement_id = player_training_id(replacement)
    assert replacement_id in {
        exposure.player_id for exposure in record.training_exposure_entries
    }
    removed = coverage_row_for_player(service.coverage(players, service.active_cycle_id()), removed_player_id)
    added = coverage_row_for_player(service.coverage(players, service.active_cycle_id()), replacement_id)
    assert removed.assumed_exposure == 0
    assert removed.planned_exposure == 0
    assert added.planned_exposure > 0


def test_replaced_participation_survives_repository_reload(tmp_path):
    path = tmp_path / "planner.json"
    service = WeeklyTrainingAppService(repository=WeeklyTrainingRepository(path))
    week = service.load_state().active_week
    players = roster() + [player("Replacement IM", playmaking=10)]
    replacement = players[-1]
    plan = service.generate_plan(players, "3-5-2")
    saved = service.record_first_match(
        service.board_for_plan(plan),
        roster_players=players,
        match_date=week.first_match_date,
        requested_status=MatchStatus.PLAYED,
        today=week.first_match_date,
        linked_match_record_id="saved-match-1",
    )
    original = saved.match_records[0]
    changed_board, removed_player_id = _replace_player_in_trainable_slot(
        service.board_for_record(original),
        replacement,
    )
    service.replace_linked_match_lineup(
        "saved-match-1",
        changed_board,
        roster_players=players,
        match_date=original.match_date,
        requested_status=original.planned_or_played,
        played_confirmed=True,
        today=week.first_match_date,
    )

    reloaded = WeeklyTrainingAppService(repository=WeeklyTrainingRepository(path))
    state = reloaded.load_state()
    current_first = [
        record for record in state.match_records
        if record.match_role == MatchRole.FIRST_WEEKLY_MATCH
    ]

    assert len(current_first) == 1
    assert removed_player_id not in {
        entry.player_id for entry in current_first[0].lineup
    }
    assert player_training_id(replacement) in {
        entry.player_id for entry in current_first[0].lineup
    }


def test_deleting_one_weekly_match_preserves_other_match_participation(tmp_path):
    service = _service(tmp_path)
    week = service.load_state().active_week
    players = roster()
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    first_plan = service.generate_plan(players, "3-5-2")
    service.record_first_match(
        service.board_for_plan(first_plan),
        roster_players=players,
        match_date=week.first_match_date,
        requested_status=MatchStatus.PLAYED,
        today=week.first_match_date,
    )
    service.record_second_match(
        service.board_for_plan(first_plan),
        roster_players=players,
        match_date=week.second_match_date,
        requested_status=MatchStatus.PLAYED,
        today=week.second_match_date,
    )
    second_ids = {
        exposure.player_id
        for exposure in service.second_match_record().training_exposure_entries
    }

    service.delete_first_match()

    state = service.load_state()
    assert len(state.match_records) == 1
    assert {
        exposure.player_id
        for exposure in state.match_records[0].training_exposure_entries
    } == second_ids


def test_duplicate_active_match_one_records_are_repaired_and_not_aggregated(tmp_path):
    service = _service(tmp_path)
    week = service.load_state().active_week
    players = roster() + [player("Replacement IM", playmaking=10)]
    replacement = players[-1]
    plan = service.generate_plan(players, "3-5-2")
    saved = service.record_first_match(
        service.board_for_plan(plan),
        roster_players=players,
        match_date=week.first_match_date,
        requested_status=MatchStatus.PLAYED,
        today=week.first_match_date,
    )
    original = saved.match_records[0]
    changed_board, removed_player_id = _replace_player_in_trainable_slot(
        service.board_for_record(original),
        replacement,
    )
    service.replace_first_match(
        changed_board,
        roster_players=players,
        match_date=week.first_match_date,
        requested_status=MatchStatus.PLAYED,
        played_confirmed=True,
        today=week.first_match_date,
    )
    state = service.load_state()
    current = state.match_records[0]
    stale_duplicate = replace(
        original,
        match_id=f"{week.week_id}:first-stale",
    )
    service._repository.save(
        replace(
            state,
            match_records=(stale_duplicate, current),
        )
    )

    repaired = service.load_state()
    records = [
        record for record in repaired.match_records
        if record.match_role == MatchRole.FIRST_WEEKLY_MATCH
        and record.match_id.startswith(f"{week.week_id}:")
    ]
    removed = coverage_row_for_player(service.coverage(players, service.active_cycle_id()), removed_player_id)
    added = coverage_row_for_player(
        service.coverage(players, service.active_cycle_id()),
        player_training_id(replacement),
    )

    assert len(records) == 1
    assert records[0].match_id == current.match_id
    assert removed.assumed_exposure == 0
    assert added.assumed_exposure > 0


def test_participation_provenance_reports_final_linked_slot(tmp_path):
    service = _service(tmp_path)
    week = service.load_state().active_week
    players = roster()
    plan = service.generate_plan(players, "3-5-2")
    service.record_first_match(
        service.board_for_plan(plan),
        roster_players=players,
        match_date=week.first_match_date,
        linked_match_record_id="saved-match-1",
    )
    player_id = service.first_match_record().lineup[0].player_id

    provenance = service.participation_provenance(player_id, week.week_id)

    assert provenance
    assert provenance[0]["match_role"] == "FIRST_WEEKLY_MATCH"
    assert provenance[0]["label"].startswith("Partido 1 - ")


def test_priority_alone_does_not_create_participation_symbol(tmp_path):
    page = SquadPage()
    players = roster()
    service = _service(tmp_path)
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    rows = service.priority_rows(players)

    page.show_weekly_training(
        service.load_state(),
        rows,
        service.coverage(players, service.active_cycle_id()),
        ["3-5-2"],
    )
    status_by_name = {
        page.weekly_player_table.item(row, 0).text():
        page.weekly_player_table.item(row, 2).text()
        for row in range(page.weekly_player_table.rowCount())
    }

    assert status_by_name[players[1].name] == "\u2014"


def test_explain_weekly_player_state_reports_no_sources_after_removal(tmp_path):
    service = _service(tmp_path)
    week = service.load_state().active_week
    players = roster() + [player("Replacement IM", playmaking=10)]
    replacement = players[-1]
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    plan = service.generate_plan(players, "3-5-2")
    saved = service.record_first_match(
        service.board_for_plan(plan),
        roster_players=players,
        match_date=week.first_match_date,
        requested_status=MatchStatus.PLAYED,
        today=week.first_match_date,
        linked_match_record_id="saved-match-1",
    )
    original = saved.match_records[0]
    changed_board, removed_player_id = _replace_player_in_trainable_slot(
        service.board_for_record(original),
        replacement,
    )
    service.replace_linked_match_lineup(
        "saved-match-1",
        changed_board,
        roster_players=players,
        match_date=original.match_date,
        requested_status=original.planned_or_played,
        played_confirmed=True,
        today=week.first_match_date,
    )

    explanation = service.explain_weekly_player_state(
        removed_player_id,
        week.week_id,
        players,
        displayed_symbol="\u2014",
    )

    assert explanation["displayed_symbol"] == "\u2014"
    assert explanation["planned_exposure"] == "0"
    assert explanation["assumed_exposure"] == "0"
    assert explanation["source_matches"] == ()
    assert explanation["match_1"] == ()
    assert explanation["match_2"] == ()


def test_visible_cycle_coverage_excludes_other_cycle_records_and_repairs_bad_link(tmp_path):
    historical_repo = HistoricalMatchRepository(tmp_path / "history.json")
    weekly_repo = WeeklyTrainingRepository(tmp_path / "planner.json")
    visible_week = active_training_week(
        today=date(2026, 8, 2),
        training_type="PLAYMAKING",
    )
    previous_cycle = active_training_week(
        today=date(2026, 7, 26),
        training_type="PLAYMAKING",
    ).week_id
    future_cycle = active_training_week(
        today=date(2027, 7, 25),
        training_type="PLAYMAKING",
    ).week_id
    bassedas = replace(
        player(
            "Mauricio Gustavo Bassedas",
            playmaking=12,
            salary=3930,
        ),
        age=25,
    )
    visible_player = player("Visible IM", playmaking=14)
    linked_snapshot = HistoricalMatchSnapshot(
        snapshot_id="1808df1d-e25c-490b-a98e-49d8ff746dee",
        match_context=MatchContext(
            match_date="2026-07-26",
            opponent=OpponentReference(opponent_name="Torres Futbol Club"),
        ),
    )
    historical_repo.save(linked_snapshot)
    rules = PlaymakingTrainingRules()

    previous_record = played_record(
        [entry_for(bassedas, "CENTRAL_DEFENDER", match_id=f"{previous_cycle}:first")],
        match_id=f"{previous_cycle}:first",
    )
    visible_record = played_record(
        [entry_for(visible_player, "INNER_MIDFIELDER", match_id=f"{visible_week.week_id}:first")],
        match_id=f"{visible_week.week_id}:first",
    )
    invalid_future_entry = entry_for(
        bassedas,
        "INNER_MIDFIELDER",
        match_id=f"{future_cycle}:second",
    )
    invalid_future_record = replace(
        played_record(
            [invalid_future_entry],
            match_id=f"{future_cycle}:second",
        ),
        match_date=date(2027, 7, 25),
        match_role=MatchRole.SECOND_WEEKLY_MATCH,
        planned_or_played=MatchStatus.PLANNED,
        source="match_page",
        linked_match_record_id=linked_snapshot.snapshot_id,
        training_exposure_entries=(
            rules.exposure_for_entry(
                f"{future_cycle}:second",
                invalid_future_entry,
                "match_page",
                assumed_confidence(False),
            ),
        ),
    )
    weekly_repo.save(
        WeeklyTrainingState(
            active_training_type="PLAYMAKING",
            active_week=visible_week,
            match_records=(
                previous_record,
                visible_record,
                invalid_future_record,
            ),
        )
    )
    service = WeeklyTrainingAppService(
        repository=weekly_repo,
        history_repository=historical_repo,
    )

    repaired_state = service.load_state()
    reloaded = WeeklyTrainingAppService(
        repository=weekly_repo,
        history_repository=historical_repo,
    )
    visible_row = coverage_row_for_player(
        reloaded.coverage([bassedas, visible_player], visible_week.week_id),
        player_training_id(bassedas),
    )
    previous_row = coverage_row_for_player(
        reloaded.coverage([bassedas, visible_player], previous_cycle),
        player_training_id(bassedas),
    )
    explanation = reloaded.explain_weekly_player_state(
        player_training_id(bassedas),
        visible_week.week_id,
        [bassedas, visible_player],
        displayed_symbol="—",
    )

    assert visible_row.planned_exposure == 0
    assert visible_row.assumed_exposure == 0
    assert visible_row.confirmed_exposure == 0
    assert _symbol_for(visible_row) == "—"
    assert previous_row.planned_exposure > 0
    assert explanation["source_matches"] == ()
    assert explanation["match_1"] == ()
    assert explanation["match_2"] == ()
    assert {
        item["match_id"] for item in explanation["other_cycles"]
    } == {
        f"{previous_cycle}:first",
        f"{previous_cycle}:second",
    }
    assert all(
        item["contributes_minutes"] == "0"
        for item in explanation["other_cycles"]
    )
    assert any(
        record.match_id == f"{previous_cycle}:second"
        and record.match_date == date(2026, 7, 26)
        for record in repaired_state.match_records
    )


def test_linked_weekly_record_without_safe_scheduled_date_is_quarantined(tmp_path):
    historical_repo = HistoricalMatchRepository(tmp_path / "history.json")
    weekly_repo = WeeklyTrainingRepository(tmp_path / "planner.json")
    visible_week = active_training_week(
        today=date(2026, 8, 2),
        training_type="PLAYMAKING",
    )
    bassedas = replace(
        player(
            "Mauricio Gustavo Bassedas",
            playmaking=12,
            salary=3930,
        ),
        age=25,
    )
    linked_snapshot = HistoricalMatchSnapshot(
        snapshot_id="bad-date-record",
        match_context=MatchContext(
            match_date="",
            opponent=OpponentReference(opponent_name="Torres Futbol Club"),
        ),
    )
    historical_repo.save(linked_snapshot)
    match_id = "2027-07-25:PLAYMAKING:second"
    weekly_record = replace(
        played_record(
            [entry_for(bassedas, "INNER_MIDFIELDER", match_id=match_id)],
            match_id=match_id,
        ),
        match_role=MatchRole.SECOND_WEEKLY_MATCH,
        linked_match_record_id=linked_snapshot.snapshot_id,
    )
    weekly_repo.save(
        WeeklyTrainingState(
            active_training_type="PLAYMAKING",
            active_week=visible_week,
            match_records=(weekly_record,),
        )
    )
    service = WeeklyTrainingAppService(
        repository=weekly_repo,
        history_repository=historical_repo,
    )

    state = service.load_state()
    row = coverage_row_for_player(
        service.coverage([bassedas], visible_week.week_id),
        player_training_id(bassedas),
    )

    assert state.match_records[0].match_role == MatchRole.OTHER
    assert state.match_records[0].training_exposure_entries == ()
    assert "quarantined" in state.match_records[0].notes
    assert row.planned_exposure == 0
    assert row.assumed_exposure == 0
    assert row.confirmed_exposure == 0
