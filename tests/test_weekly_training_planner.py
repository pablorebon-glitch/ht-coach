import os
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from engine.weekly_training.coverage import WeeklyTrainingCoverageService
from engine.weekly_training.models import (
    PLAYMAKING,
    MatchRole,
    MatchStatus,
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
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from models.formations import FORMATION_BY_NAME
from models.player import Player
from models.position import Position

try:
    from PySide6.QtWidgets import QApplication, QComboBox
    from ht_coach_app.views.squad_page import SquadPage
except Exception:  # pragma: no cover - PySide6 may be unavailable in headless CI
    QApplication = None
    QComboBox = None
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

    assert plan.state == PlannerState.PLAN_CONFLICTED
    assert plan.conflicts[0].code == "INSUFFICIENT_TRAINING_SLOTS"


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

    assert plan.state == PlannerState.PLAN_CONFLICTED
    assert plan.conflicts[0].code == "UNAVAILABLE_REQUIRED_PLAYER"


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
    service.record_first_match(board)
    loaded = repository.load()

    assert loaded.priorities[player_training_id(players[1])].priority == TrainingPriority.REQUIRED_100
    assert len(loaded.match_records) == 1
    assert loaded.match_records[0].planned_or_played == MatchStatus.PLAYED


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
    assert page.weekly_priority_table.columnCount() == 6
    assert page.weekly_coverage_table.columnCount() == 8
    assert page.findChildren(QComboBox)
    app.processEvents()
