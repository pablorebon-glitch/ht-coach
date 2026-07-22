import os
import pytest
import unittest
from datetime import date, datetime
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from engine.weekly_training.coverage import WeeklyTrainingCoverageService
from engine.weekly_training.models import (
    PLAYMAKING,
    MatchRole,
    MatchStatus,
    PlayerCoverage,
    PlannerExplanation,
    PlannerState,
    TrainingPriority,
    TrainingPriorityRecord,
    WeeklyMatchLineupEntry,
    WeeklyMatchRecord,
)
from engine.weekly_training.persistence import WeeklyTrainingRepository
from engine.weekly_training.player_identity import player_training_id
from engine.weekly_training.planner import WeeklyTrainingPlanner
from engine.weekly_training.training_rules import PlaymakingTrainingRules, assumed_confidence
from engine.weekly_training.training_week import active_training_week, rollover_week
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from ht_coach_app.workspace.workspace_service import WorkspaceService
from models.formations import FORMATION_BY_NAME
from models.player import Player
from models.position import Position

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import QApplication, QComboBox, QScrollArea, QTextBrowser
    from ht_coach_app.views.squad_page import SquadPage
except Exception:  # pragma: no cover - PySide6 may be unavailable in headless CI
    Qt = None
    QTimer = None
    QApplication = None
    QComboBox = None
    QScrollArea = None
    QTextBrowser = None
    SquadPage = None


def player(
    name,
    goalkeeper=1,
    defending=5,
    playmaking=5,
    winger=5,
    passing=5,
    scoring=5,
    injury=None,
    tsi=None,
    salary=None,
):
    return Player(
        name=name,
        age=23,
        days=12,
        speciality="",
        form=7,
        stamina=7,
        goalkeeper=goalkeeper,
        defending=defending,
        playmaking=playmaking,
        winger=winger,
        passing=passing,
        scoring=scoring,
        set_pieces=4,
        experience=5,
        leadership=4,
        tsi=tsi if tsi is not None else 1000 + playmaking + winger + scoring,
        salary=salary if salary is not None else 1000 + defending,
        injury=injury,
    )


def roster():
    return [
        player("Keeper", goalkeeper=12),
        player("Required IM", playmaking=14),
        player("Required Wing", playmaking=9, winger=13),
        player("High IM", playmaking=13),
        player("Secondary IM", playmaking=12),
        player("Rested Winger", winger=14),
        player("Defender 1", defending=12),
        player("Defender 2", defending=11),
        player("Defender 3", defending=10),
        player("Winger 1", winger=12),
        player("Winger 2", winger=11),
        player("Forward 1", scoring=12),
        player("Forward 2", scoring=11),
        player("Forward 3", scoring=10),
    ]


def entry_for(player_obj, position, minutes=90, match_id="m1"):
    return WeeklyMatchLineupEntry(
        player_id=player_training_id(player_obj),
        player_name=player_obj.name,
        slot_id=f"{position}:1",
        position=position,
        side="CENTER",
        played_minutes=Decimal(str(minutes)),
    )


def played_record(entries, match_id="m1", minutes_known=False):
    rules = PlaymakingTrainingRules()
    return WeeklyMatchRecord(
        match_id=match_id,
        match_date=date(2026, 7, 19),
        match_role=MatchRole.FIRST_WEEKLY_MATCH,
        formation="3-5-2",
        lineup=tuple(entries),
        planned_or_played=MatchStatus.PLAYED,
        minutes_known=minutes_known,
        training_exposure_entries=tuple(
            rules.exposure_for_entry(
                match_id,
                entry,
                "test",
                assumed_confidence(minutes_known),
            )
            for entry in entries
        ),
    )


def show_weekly_tab(page):
    for index in range(page.tabs.count()):
        if page.tabs.tabText(index) in {"Weekly Planner", "Planificador semanal"}:
            page.tabs.setCurrentIndex(index)
            return
    raise AssertionError("Weekly Planner tab not found")


def trainable_lineup_player_id(record):
    return next(
        entry.player_id for entry in record.lineup
        if entry.position in {
            Position.INNER_MIDFIELDER.value,
            Position.WINGER.value,
        }
    )


def coverage_row_for_player(rows, player_id):
    return next(item for item in rows if item.player_id == player_id)


def widget_rect_in(widget, ancestor):
    top_left = widget.mapTo(ancestor, widget.rect().topLeft())
    return widget.rect().translated(top_left)


def test_training_week_uses_sunday_to_wednesday_window_and_thursday_rollover():
    week = active_training_week(date(2026, 7, 19))
    assert week.start_date == date(2026, 7, 19)
    assert week.second_match_date == date(2026, 7, 22)
    assert week.training_update_date == date(2026, 7, 23)

    rolled = active_training_week(date(2026, 7, 23))
    assert rolled.start_date == date(2026, 7, 26)


def test_weekly_training_engine_layer_does_not_import_desktop_app():
    weekly_training_path = Path("engine/weekly_training")
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in weekly_training_path.glob("*.py")
    )

    assert "ht_coach_app" not in source


def test_training_week_handles_year_boundary_and_timezone_aware_datetime():
    week = active_training_week(datetime(2026, 1, 1, 3, 0))
    assert week.start_date == date(2026, 1, 4)


def test_rollover_archives_week_and_preserves_training_type():
    week = active_training_week(date(2026, 7, 19))
    archived, active = rollover_week(week, date(2026, 7, 23))

    assert archived.status.value == "ARCHIVED"
    assert active.start_date == date(2026, 7, 26)
    assert active.active_training_type == PLAYMAKING


def test_playmaking_rules_calculate_factors_minutes_and_capacity():
    rules = PlaymakingTrainingRules()
    p = player("Trainee")

    im = rules.exposure_for_entry(
        "m1",
        entry_for(p, Position.INNER_MIDFIELDER.value, 90),
        "test",
        assumed_confidence(False),
    )
    winger = rules.exposure_for_entry(
        "m1",
        entry_for(p, Position.WINGER.value, 45),
        "test",
        assumed_confidence(True),
    )

    assert im.training_factor == Decimal("1")
    assert im.effective_training_minutes == Decimal("90")
    assert winger.training_factor == Decimal("0.5")
    assert winger.effective_training_minutes == Decimal("22.5")
    assert rules.factor_for_position(Position.FORWARD) == Decimal("0")
    capacity = rules.capacity_for_formation(FORMATION_BY_NAME["3-5-2"])
    assert capacity.full_slots == 3
    assert capacity.half_slots == 2
    assert capacity.effective_player_equivalents == Decimal("4.0")


def test_coverage_separates_confirmed_assumed_and_planned_exposure():
    players = roster()
    trainee = players[1]
    priorities = {
        player_training_id(trainee): TrainingPriority.REQUIRED_100,
    }
    confirmed = played_record(
        [entry_for(trainee, Position.WINGER.value, 90)],
        "confirmed",
        minutes_known=True,
    )
    planned = WeeklyMatchRecord(
        match_id="planned",
        match_date=date(2026, 7, 22),
        match_role=MatchRole.SECOND_WEEKLY_MATCH,
        planned_or_played=MatchStatus.PLANNED,
        training_exposure_entries=confirmed.training_exposure_entries,
    )

    rows = WeeklyTrainingCoverageService(PlaymakingTrainingRules()).aggregate(
        players,
        priorities,
        (confirmed, planned),
    )
    row = next(item for item in rows if item.player_id == player_training_id(trainee))
    assert row.confirmed_exposure == Decimal("50.0")
    assert row.planned_exposure == Decimal("50.0")
    assert row.remaining_exposure == Decimal("0")


def test_first_match_past_played_counts_as_already_trained(tmp_path):
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    plan = service.generate_plan(players, "3-5-2")
    board = service.board_for_plan(plan)

    service.record_first_match(
        board,
        roster_players=players,
        match_date=date(2026, 7, 21),
        requested_status=MatchStatus.PLAYED,
        today=date(2026, 7, 22),
    )
    row = coverage_row_for_player(
        service.coverage(players),
        trainable_lineup_player_id(service.first_match_record()),
    )

    assert row.assumed_exposure > 0
    assert row.planned_exposure == 0


def test_first_match_past_planned_counts_only_as_planned(tmp_path):
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    plan = service.generate_plan(players, "3-5-2")

    service.record_first_match(
        service.board_for_plan(plan),
        roster_players=players,
        match_date=date(2026, 7, 21),
        requested_status=MatchStatus.PLANNED,
        today=date(2026, 7, 22),
    )
    row = coverage_row_for_player(
        service.coverage(players),
        trainable_lineup_player_id(service.first_match_record()),
    )

    assert row.assumed_exposure == 0
    assert row.planned_exposure > 0


def test_first_match_today_played_requires_confirmation(tmp_path):
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    plan = service.generate_plan(players, "3-5-2")

    saved = service.record_first_match(
        service.board_for_plan(plan),
        roster_players=players,
        match_date=date(2026, 7, 22),
        requested_status=MatchStatus.PLAYED,
        played_confirmed=False,
        today=date(2026, 7, 22),
    )
    record = saved.match_records[0]

    assert record.planned_or_played == MatchStatus.PLANNED
    assert "not been confirmed" in record.notes


def test_first_match_today_played_with_confirmation_counts_as_played(tmp_path):
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    plan = service.generate_plan(players, "3-5-2")

    saved = service.record_first_match(
        service.board_for_plan(plan),
        roster_players=players,
        match_date=date(2026, 7, 22),
        requested_status=MatchStatus.PLAYED,
        played_confirmed=True,
        today=date(2026, 7, 22),
    )

    assert saved.match_records[0].planned_or_played == MatchStatus.PLAYED
    row = coverage_row_for_player(
        service.coverage(players),
        trainable_lineup_player_id(service.first_match_record()),
    )
    assert row.assumed_exposure > 0


def test_first_match_future_played_becomes_planned_and_never_already_trained(tmp_path):
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    plan = service.generate_plan(players, "3-5-2")

    saved = service.record_first_match(
        service.board_for_plan(plan),
        roster_players=players,
        match_date=date(2026, 7, 23),
        requested_status=MatchStatus.PLAYED,
        today=date(2026, 7, 22),
    )
    record = saved.match_records[0]
    row = coverage_row_for_player(
        service.coverage(players),
        trainable_lineup_player_id(record),
    )

    assert record.planned_or_played == MatchStatus.PLANNED
    assert "future" in record.notes
    assert row.assumed_exposure == 0
    assert row.planned_exposure > 0


def test_future_played_strict_validation_returns_clear_error(tmp_path):
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )

    with pytest.raises(ValueError, match="future_match_cannot_be_played"):
        service.validate_match_status(
            date(2026, 7, 23),
            MatchStatus.PLAYED,
            today=date(2026, 7, 22),
            strict=True,
        )


def test_edit_past_played_record_to_future_invalidates_played_status(tmp_path):
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    plan = service.generate_plan(players, "3-5-2")
    service.record_first_match(
        service.board_for_plan(plan),
        roster_players=players,
        match_date=date(2026, 7, 21),
        requested_status=MatchStatus.PLAYED,
        today=date(2026, 7, 22),
    )

    saved = service.update_first_match_metadata(
        match_date=date(2026, 7, 23),
        requested_status=MatchStatus.PLAYED,
        today=date(2026, 7, 22),
    )

    assert saved.match_records[0].planned_or_played == MatchStatus.PLANNED
    row = coverage_row_for_player(
        service.coverage(players),
        trainable_lineup_player_id(saved.match_records[0]),
    )
    assert row.assumed_exposure == 0
    assert row.planned_exposure > 0


def test_delete_first_match_removes_confirmed_exposure(tmp_path):
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    plan = service.generate_plan(players, "3-5-2")
    service.record_first_match(
        service.board_for_plan(plan),
        roster_players=players,
        match_date=date(2026, 7, 21),
        requested_status=MatchStatus.PLAYED,
        today=date(2026, 7, 22),
    )

    service.delete_first_match()
    row = next(
        item for item in service.coverage(players)
        if item.player_id == player_training_id(players[1])
    )

    assert row.confirmed_exposure == 0
    assert row.assumed_exposure == 0
    assert row.planned_exposure == 0


def test_replace_first_match_recalculates_temporal_status(tmp_path):
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    plan = service.generate_plan(players, "3-5-2")
    board = service.board_for_plan(plan)
    service.record_first_match(
        board,
        roster_players=players,
        match_date=date(2026, 7, 21),
        requested_status=MatchStatus.PLAYED,
        today=date(2026, 7, 22),
    )
    changed = service.generate_plan(players, "4-5-1")

    saved = service.replace_first_match(
        service.board_for_plan(changed),
        roster_players=players,
        match_date=date(2026, 7, 23),
        requested_status=MatchStatus.PLAYED,
        today=date(2026, 7, 22),
    )

    assert saved.match_records[0].formation == "4-5-1"
    assert saved.match_records[0].planned_or_played == MatchStatus.PLANNED


def test_priorities_persist_duplicate_names_and_rollover_resets_records(tmp_path):
    repository = WeeklyTrainingRepository(tmp_path / "planner.json")
    state = repository.load()
    first = player("Same Name", tsi=0)
    second = player("Same Name", tsi=0, salary=2000)
    state = repository.save_priority(
        state,
        TrainingPriorityRecord(
            player_id=player_training_id(first),
            player_name=first.name,
            priority=TrainingPriority.REQUIRED_100,
        ),
    )
    state = repository.save_priority(
        state,
        TrainingPriorityRecord(
            player_id=player_training_id(second),
            player_name=second.name,
            priority=TrainingPriority.REST,
        ),
    )
    state = repository.add_match_record(
        state,
        played_record([entry_for(first, Position.INNER_MIDFIELDER.value)]),
    )
    loaded = repository.load()

    assert loaded.priorities[player_training_id(first)].priority == TrainingPriority.REQUIRED_100
    assert loaded.priorities[player_training_id(second)].priority == TrainingPriority.REST
    rolled = repository.rollover(loaded, date(2026, 7, 23))
    assert rolled.priorities == loaded.priorities
    assert rolled.match_records == loaded.match_records
    assert len(rolled.archived_weeks) == 1


def test_planner_selects_required_players_excludes_rest_and_applies_orders():
    players = roster()
    required = players[1]
    required_half = players[2]
    rested = players[5]
    priorities = {
        player_training_id(required): TrainingPriority.REQUIRED_100,
        player_training_id(required_half): TrainingPriority.REQUIRED_50,
        player_training_id(rested): TrainingPriority.REST,
    }
    plan = WeeklyTrainingPlanner().plan(
        players,
        active_training_week(date(2026, 7, 19)),
        priorities,
        formation_name="3-5-2",
    )

    names = {entry.player_name for entry in plan.lineup}
    required_entry = next(entry for entry in plan.lineup if entry.player_name == required.name)
    half_entry = next(entry for entry in plan.lineup if entry.player_name == required_half.name)
    assert plan.state == PlannerState.PLAN_READY
    assert required.name in names
    assert required_entry.position == Position.INNER_MIDFIELDER.value
    assert half_entry.position in {Position.INNER_MIDFIELDER.value, Position.WINGER.value}
    assert rested.name not in names
    assert len(plan.lineup) == 11
    assert len({entry.player_id for entry in plan.lineup}) == 11
    assert all(entry.order for entry in plan.lineup)


def test_planner_returns_structured_conflict_for_too_many_required_full_targets():
    players = roster()
    priorities = {
        player_training_id(item): TrainingPriority.REQUIRED_100
        for item in players[1:6]
    }

    plan = WeeklyTrainingPlanner().plan(
        players,
        active_training_week(date(2026, 7, 19)),
        priorities,
        formation_name="3-5-2",
    )

    assert plan.state == PlannerState.PLAN_READY
    assert len(plan.lineup) == 11
    assert plan.conflicts[0].code == "INSUFFICIENT_TRAINING_SLOTS"
    assert plan.warnings


def test_planner_excludes_unavailable_required_player_with_conflict():
    players = roster()
    priorities = {
        player_training_id(players[1]): TrainingPriority.REQUIRED_100,
    }

    plan = WeeklyTrainingPlanner().plan(
        players,
        active_training_week(date(2026, 7, 19)),
        priorities,
        formation_name="3-5-2",
        unavailable_player_ids=(player_training_id(players[1]),),
    )

    assert plan.state == PlannerState.PLAN_READY
    assert len(plan.lineup) == 11
    assert plan.conflicts[0].code == "UNAVAILABLE_REQUIRED_PLAYER"
    assert players[1].name not in {entry.player_name for entry in plan.lineup}


def test_generate_plan_returns_complete_lineup_with_conflict_and_coverage():
    players = roster()
    priorities = {
        player_training_id(item): TrainingPriority.REQUIRED_100
        for item in players[1:7]
    }

    plan = WeeklyTrainingPlanner().plan(
        players,
        active_training_week(date(2026, 7, 19)),
        priorities,
        formation_name="3-5-2",
    )

    assert plan.state == PlannerState.PLAN_READY
    assert len(plan.lineup) == 11
    assert len({entry.player_id for entry in plan.lineup}) == 11
    assert any(entry.position == Position.GOALKEEPER.value for entry in plan.lineup)
    assert all(entry.order for entry in plan.lineup)
    assert plan.coverage
    assert plan.conflicts
    assert plan.warnings
    assert plan.competitive_cost.sector_deltas
    assert any(
        item.code in {"REQUIRED_TARGET_PARTIAL", "REQUIRED_TARGET_OMITTED"}
        for item in plan.explanations
    )


def test_planner_returns_no_lineup_only_without_valid_goalkeeper():
    players = [
        player(f"Player {index}", goalkeeper=0, playmaking=10, defending=10)
        for index in range(12)
    ]

    plan = WeeklyTrainingPlanner().plan(
        players,
        active_training_week(date(2026, 7, 19)),
        {},
        formation_name="3-5-2",
    )

    assert plan.state == PlannerState.PLAN_CONFLICTED
    assert plan.lineup == ()
    assert plan.conflicts[0].code == "NO_VALID_GOALKEEPER"


def test_app_service_persists_priority_and_records_first_match(tmp_path):
    repository = WeeklyTrainingRepository(tmp_path / "planner.json")
    service = WeeklyTrainingAppService(repository=repository)
    players = roster()

    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    rows = service.priority_rows(players)
    required = next(row for row in rows if row.player_name == players[1].name)
    assert required.priority == TrainingPriority.REQUIRED_100

    plan = service.generate_plan(players, "3-5-2")
    board = service.board_for_plan(plan)
    service.record_first_match(board, roster_players=players)
    loaded = repository.load()

    assert loaded.priorities[player_training_id(players[1])].priority == TrainingPriority.REQUIRED_100
    assert len(loaded.match_records) == 1
    assert loaded.match_records[0].planned_or_played == MatchStatus.PLAYED


def test_app_service_populates_pitch_bench_orders_and_acceptance_board(tmp_path):
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()

    plan = service.generate_plan(players, "3-5-2")
    board = service.board_for_plan(plan)
    workspace = WorkspaceService().create([board], board.formation_name, players)
    bench = WorkspaceService().derive_bench(workspace, players)

    assert board is not None
    assert len([slot for slot in board.slots if slot.player is not None]) == 11
    assert bench
    assert all(entry.order for entry in plan.lineup)


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
def test_use_this_lineup_transfers_weekly_plan_to_squad_board(tmp_path):
    app = QApplication.instance() or QApplication([])
    page = SquadPage()
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    plan = service.generate_plan(players, "3-5-2")
    board = service.board_for_plan(plan)

    page.show_weekly_training_plan(plan, board, players)
    page.accept_weekly_training_plan()
    accepted = page.ideal_board.current_board()

    assert accepted is not None
    assert accepted.formation_name == "3-5-2"
    assert len([slot for slot in accepted.slots if slot.player is not None]) == 11
    app.processEvents()


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
def test_weekly_planner_information_cards_are_outside_pitch(tmp_path):
    app = QApplication.instance() or QApplication([])
    page = SquadPage()
    show_weekly_tab(page)
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    plan = service.generate_plan(players, "3-5-2")

    page.show_weekly_training_plan(plan, service.board_for_plan(plan), players)
    app.processEvents()

    pitch = page.weekly_plan_board.pitch
    for widget in (
        page.weekly_cost_card,
        page.weekly_warnings_card,
        page.weekly_explanations_card,
    ):
        current = widget.parentWidget()
        while current is not None:
            assert current is not pitch
            current = current.parentWidget()

    assert page.weekly_cost_card.parentWidget() is not page.weekly_plan_board
    assert page.weekly_explanations_card.parentWidget() is not page.weekly_plan_board
    assert page.weekly_lineup_workspace.findChild(QTextBrowser) is None


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
def test_weekly_planner_long_explanations_scroll_in_card(tmp_path):
    app = QApplication.instance() or QApplication([])
    page = SquadPage()
    show_weekly_tab(page)
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    plan = service.generate_plan(players, "3-5-2")
    long_plan = replace(
        plan,
        explanations=tuple(
            PlannerExplanation(
                code="REQUIRED_TARGET_OMITTED",
                player_id=f"p{index}",
                player_name=(
                    "Very Long Player Name With A Verbose Planner Explanation "
                    f"{index}"
                ),
            )
            for index in range(40)
        ),
    )

    page.resize(1366, 768)
    page.show_weekly_training_plan(long_plan, service.board_for_plan(plan), players)
    page.show()
    app.processEvents()

    browser = page.weekly_explanations_browser
    assert browser.lineWrapMode() == QTextBrowser.WidgetWidth
    assert browser.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert browser.maximumHeight() <= 180
    assert browser.verticalScrollBar().maximum() > 0
    assert page.weekly_plan_board.isVisible()


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
def test_weekly_planner_side_panel_collapse_keeps_info_cards_below_pitch(tmp_path):
    app = QApplication.instance() or QApplication([])
    page = SquadPage()
    show_weekly_tab(page)
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    plan = service.generate_plan(players, "3-5-2")
    page.show_weekly_training_plan(plan, service.board_for_plan(plan), players)
    page.resize(1366, 768)
    page.show()
    app.processEvents()

    before_y = page.weekly_cost_card.mapTo(page, page.weekly_cost_card.rect().topLeft()).y()
    page.weekly_plan_board.bench_side_panel.set_expanded(False)
    page.weekly_plan_board.inspector_side_panel.set_expanded(False)
    app.processEvents()
    after_y = page.weekly_cost_card.mapTo(page, page.weekly_cost_card.rect().topLeft()).y()

    assert abs(after_y - before_y) < 30
    assert page.weekly_cost_card.parentWidget() is not page.weekly_plan_board


def test_weekly_priority_rows_use_human_position_score_labels(tmp_path):
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    rows = service.priority_rows(roster())

    labels = [row.best_position for row in rows]
    assert any(label.startswith(("GK ", "IM ", "W ", "CD ", "WB ", "F ")) for label in labels)
    assert not any(label.startswith("(") for label in labels)
    assert not any("INNER_MIDFIELDER" in label for label in labels)


def test_planner_regenerates_after_priority_formation_and_first_match_update(tmp_path):
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    initial = service.generate_plan(players, "3-5-2")

    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    prioritized = service.generate_plan(players, "3-5-2")
    changed_formation = service.generate_plan(players, "4-5-1")
    service.record_first_match(
        service.board_for_plan(prioritized),
        roster_players=players,
    )
    after_first_match = service.generate_plan(players, "3-5-2")

    assert initial.formation == "3-5-2"
    assert prioritized.lineup
    assert any(
        item.player_name == players[1].name
        for item in prioritized.explanations
    )
    assert changed_formation.formation == "4-5-1"
    assert after_first_match.lineup
    assert any(row.source_matches for row in after_first_match.coverage)


def test_app_service_uses_weekly_training_identity_for_duplicate_names(tmp_path):
    repository = WeeklyTrainingRepository(tmp_path / "planner.json")
    service = WeeklyTrainingAppService(repository=repository)
    first = player("Same Name", tsi=1000, salary=1000)
    second = player("Same Name", tsi=1000, salary=2000)

    service.save_priority(first, TrainingPriority.REQUIRED_100.value)
    service.save_priority(second, TrainingPriority.REST.value)
    priorities = repository.load().priorities

    assert priorities[player_training_id(first)].priority == TrainingPriority.REQUIRED_100
    assert priorities[player_training_id(second)].priority == TrainingPriority.REST


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
def test_squad_page_weekly_planner_tab_smoke():
    app = QApplication.instance() or QApplication([])
    page = SquadPage()

    tab_labels = [
        page.tabs.tabText(index)
        for index in range(page.tabs.count())
    ]

    assert "Weekly Planner" in tab_labels
    assert page.weekly_training_type_combo.currentData() == PLAYMAKING
    assert page.weekly_generate_button.text() == "Generate Plan"
    assert page.weekly_player_table.columnCount() == 9
    assert page.weekly_priority_table is page.weekly_player_table
    assert page.weekly_coverage_table is page.weekly_player_table
    assert page.findChildren(QComboBox)
    app.processEvents()


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
def test_weekly_planner_uses_unified_table_and_simplified_priorities(tmp_path):
    app = QApplication.instance() or QApplication([])
    page = SquadPage()
    players = [player("Trainer One")]
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    priority_rows = service.priority_rows(players)
    coverage_rows = [
        PlayerCoverage(
            player_id=player_training_id(players[0]),
            player_name="Trainer One",
            weekly_target=TrainingPriority.REQUIRED_100,
            confirmed_exposure=Decimal("0"),
            planned_exposure=Decimal("45"),
            remaining_exposure=Decimal("45"),
        )
    ]

    page.show_weekly_training(
        service.load_state(),
        priority_rows,
        coverage_rows,
        ["3-5-2"],
    )

    assert page.weekly_priority_table is page.weekly_player_table
    assert page.weekly_coverage_table is page.weekly_player_table
    combo = page.weekly_player_table.cellWidget(0, 3)
    assert [combo.itemText(index) for index in range(combo.count())] == [
        "100%",
        "50%",
        "No priority",
    ]
    assert page.weekly_player_table.item(0, 4).text() == "\u25cb"
    app.processEvents()


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
def test_future_first_match_record_renders_as_planned_not_trained(tmp_path):
    app = QApplication.instance() or QApplication([])
    page = SquadPage()
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    plan = service.generate_plan(players, "3-5-2")
    saved = service.record_first_match(
        service.board_for_plan(plan),
        roster_players=players,
        match_date=date(2026, 7, 23),
        requested_status=MatchStatus.PLAYED,
        today=date(2026, 7, 22),
    )
    trained_id = trainable_lineup_player_id(saved.match_records[0])
    trained_name = next(
        player_obj.name for player_obj in players
        if player_training_id(player_obj) == trained_id
    )

    page.show_weekly_training(
        service.load_state(),
        service.priority_rows(players),
        service.coverage(players),
        ["3-5-2"],
    )

    status_by_name = {
        page.weekly_player_table.item(row, 0).text():
        page.weekly_player_table.item(row, 4).text()
        for row in range(page.weekly_player_table.rowCount())
    }
    assert saved.match_records[0].planned_or_played == MatchStatus.PLANNED
    assert status_by_name[trained_name] == "\u25cb"
    assert "\u2713" not in status_by_name.values()
    app.processEvents()


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
def test_weekly_planner_result_cards_stack_below_pitch(tmp_path):
    app = QApplication.instance() or QApplication([])
    page = SquadPage()
    show_weekly_tab(page)
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    service.save_priority(players[2], TrainingPriority.REQUIRED_50.value)
    plan = service.generate_plan(players, "3-5-2")

    page.resize(1366, 768)
    page.show_weekly_training(
        service.load_state(),
        service.priority_rows(players),
        service.coverage(players),
        ["3-5-2", "4-5-1"],
    )
    page.show_weekly_training_plan(plan, service.board_for_plan(plan), players)
    page.show()
    app.processEvents()

    pitch_rect = widget_rect_in(page.weekly_plan_board.pitch, page)
    board_rect = widget_rect_in(page.weekly_lineup_workspace, page)
    summary_rect = widget_rect_in(page.weekly_cost_card, page)
    warnings_rect = widget_rect_in(page.weekly_warnings_card, page)
    explanations_rect = widget_rect_in(page.weekly_explanations_card, page)

    assert page.weekly_cost_card.isVisible()
    assert summary_rect.top() >= board_rect.bottom()
    assert warnings_rect.top() >= summary_rect.bottom()
    assert explanations_rect.top() >= warnings_rect.bottom()
    assert not summary_rect.intersects(pitch_rect)
    assert not warnings_rect.intersects(pitch_rect)
    assert not explanations_rect.intersects(pitch_rect)
    assert page.weekly_plan_board.current_board() is not None
    assert len(page.weekly_plan_board.pitch.card_geometries()) == 11
    assert page.findChild(QScrollArea, "weeklyPlannerScroll") is not None
    app.processEvents()


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
def test_weekly_planner_pitch_remains_interactive_after_plan_generation(tmp_path):
    app = QApplication.instance() or QApplication([])
    page = SquadPage()
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    plan = service.generate_plan(players, "3-5-2")

    page.show_weekly_training(
        service.load_state(),
        service.priority_rows(players),
        service.coverage(players),
        ["3-5-2"],
    )
    page.show_weekly_training_plan(plan, service.board_for_plan(plan), players)
    app.processEvents()
    first_player = page.weekly_plan_board.current_board().slots[0].player.player_id

    page.weekly_plan_board.select_player(first_player)

    assert page.weekly_plan_board.current_board().selected_player_id == first_player
    assert page.weekly_training_current_board() is not None
    app.processEvents()


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
def test_weekly_priority_filter_uses_visible_priority_and_updates_on_edit(tmp_path):
    app = QApplication.instance() or QApplication([])
    page = SquadPage()
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    service.save_priority(players[2], TrainingPriority.REQUIRED_50.value)

    page.show_weekly_training(
        service.load_state(),
        service.priority_rows(players),
        service.coverage(players),
        ["3-5-2"],
    )

    page.weekly_filter_combo.setCurrentIndex(
        page.weekly_filter_combo.findData("100")
    )
    assert page.weekly_player_table.rowCount() == 1
    assert page.weekly_player_table.item(0, 0).text() == players[1].name

    combo = page.weekly_player_table.cellWidget(0, 3)
    combo.setCurrentIndex(combo.findData("NO_PRIORITY"))
    app.processEvents()
    QTimer.singleShot(0, lambda: None)
    app.processEvents()

    assert page.weekly_player_table.rowCount() == 0

    page.weekly_filter_combo.setCurrentIndex(
        page.weekly_filter_combo.findData("no_priority")
    )
    names = {
        page.weekly_player_table.item(row, 0).text()
        for row in range(page.weekly_player_table.rowCount())
    }
    assert players[1].name in names
    assert players[2].name not in names
    app.processEvents()


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
def test_weekly_priority_filter_survives_sorting_plan_and_localization(tmp_path):
    app = QApplication.instance() or QApplication([])
    configure_localization("es")
    page = SquadPage()
    service = WeeklyTrainingAppService(
        repository=WeeklyTrainingRepository(tmp_path / "planner.json")
    )
    players = roster()
    service.save_priority(players[1], TrainingPriority.REQUIRED_100.value)
    service.save_priority(players[2], TrainingPriority.REQUIRED_50.value)
    plan = service.generate_plan(players, "3-5-2")

    page.show_weekly_training(
        service.load_state(),
        service.priority_rows(players),
        service.coverage(players),
        ["3-5-2"],
    )
    page.weekly_filter_combo.setCurrentIndex(
        page.weekly_filter_combo.findData("50")
    )
    page.weekly_player_table.sortItems(0, Qt.DescendingOrder)
    page.show_weekly_training_plan(plan, service.board_for_plan(plan), players)

    assert page.weekly_filter_combo.currentData() == "50"
    assert page.weekly_player_table.rowCount() == 1
    assert page.weekly_player_table.item(0, 0).text() == players[2].name
    assert (
        page.weekly_player_table.item(0, 0).data(SquadPage.PRIORITY_ROLE)
        == "REQUIRED_50"
    )
    page.show_weekly_training_plan(plan, service.board_for_plan(plan), players)
    assert "Se asumen 90 minutos" in page.weekly_warnings_label.text()
    configure_localization("en")
    app.processEvents()
