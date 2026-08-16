import os
import logging
from datetime import date
from decimal import Decimal

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from engine.weekly_training.models import (
    PLAYMAKING,
    MatchRole,
    MatchStatus,
    TrainingPriority,
    TrainingPriorityRecord,
    WeeklyMatchLineupEntry,
    WeeklyMatchRecord,
)
from engine.weekly_training.persistence import (
    WeeklyTrainingRepository,
    WeeklyTrainingState,
)
from engine.weekly_training.player_identity import player_training_id
from engine.weekly_training.training_rules import (
    PlaymakingTrainingRules,
    assumed_confidence,
)
from engine.weekly_training.training_week import active_training_week
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.services.match_workspace_service import (
    MatchAnalysisResult,
    match_analysis_result_from_dict,
    match_analysis_result_to_dict,
)
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from models.player import Player


def player(name, playmaking=10):
    return Player(
        name=name,
        age=23,
        days=12,
        speciality="",
        form=7,
        stamina=7,
        goalkeeper=1,
        defending=5,
        playmaking=playmaking,
        winger=5,
        passing=5,
        scoring=5,
        set_pieces=4,
        experience=5,
        leadership=4,
        tsi=1000,
        salary=1000,
        injury=None,
    )


def entry_for(player_obj, position="INNER_MIDFIELDER", minutes=90):
    return WeeklyMatchLineupEntry(
        player_id=player_training_id(player_obj),
        player_name=player_obj.name,
        slot_id=f"{position}:1",
        position=position,
        side="CENTER",
        played_minutes=Decimal(str(minutes)),
    )


def played_record(cycle_id, player_obj, role=MatchRole.FIRST_WEEKLY_MATCH):
    match_id = f"{cycle_id}:{'first' if role == MatchRole.FIRST_WEEKLY_MATCH else 'second'}"
    rules = PlaymakingTrainingRules()
    entry = entry_for(player_obj)
    return WeeklyMatchRecord(
        match_id=match_id,
        match_date=date.fromisoformat(cycle_id.split(":", 1)[0]),
        match_role=role,
        formation="3-5-2",
        lineup=(entry,),
        planned_or_played=MatchStatus.PLAYED,
        minutes_known=True,
        training_exposure_entries=(
            rules.exposure_for_entry(
                match_id,
                entry,
                "test",
                assumed_confidence(True),
            ),
        ),
    )


def make_service(tmp_path):
    repository = WeeklyTrainingRepository(tmp_path / "planner.json")
    active_week = active_training_week(date(2026, 8, 2), training_type=PLAYMAKING)
    repository.save(
        WeeklyTrainingState(
            active_training_type=PLAYMAKING,
            active_week=active_week,
        )
    )
    return WeeklyTrainingAppService(repository=repository)


def save_required(service, *players):
    state = service.load_state()
    priorities = dict(state.priorities)
    for item in players:
        priorities[player_training_id(item)] = TrainingPriorityRecord(
            player_id=player_training_id(item),
            player_name=item.name,
            priority=TrainingPriority.REQUIRED_100,
        )
    service._repository.save(
        WeeklyTrainingState(
            active_training_type=state.active_training_type,
            active_week=state.active_week,
            priorities=priorities,
            match_records=state.match_records,
            archived_weeks=state.archived_weeks,
        )
    )


def test_visible_cycle_options_are_current_plus_two_future_weeks(tmp_path):
    service = make_service(tmp_path)

    options = service.visible_cycle_options()

    assert [item.relative_offset for item in options] == [0, 1, 2]
    assert [item.cycle_id for item in options] == [
        "2026-08-02:PLAYMAKING",
        "2026-08-09:PLAYMAKING",
        "2026-08-16:PLAYMAKING",
    ]
    assert options[0].is_current is True
    assert options[0].end_date == date(2026, 8, 8)
    assert options[1].to_item_data() == {
        "cycle_id": "2026-08-09:PLAYMAKING",
        "start_date": "2026-08-09",
        "end_date": "2026-08-15",
        "relative_offset": 1,
    }


def test_required_players_are_isolated_by_explicit_cycle_id(tmp_path):
    service = make_service(tmp_path)
    trained_current = player("Already Trained Current")
    trained_future = player("Already Trained Future")
    save_required(service, trained_current, trained_future)
    state = service.load_state()
    future_cycle = "2026-08-09:PLAYMAKING"
    service._repository.save(
        WeeklyTrainingState(
            active_training_type=state.active_training_type,
            active_week=state.active_week,
            priorities=state.priorities,
            match_records=(
                played_record(state.active_week.week_id, trained_current),
                played_record(future_cycle, trained_future),
            ),
            archived_weeks=state.archived_weeks,
        )
    )

    current_required = service.required_player_ids_for_match(state.active_week.week_id)
    future_required = service.required_player_ids_for_match(future_cycle)

    assert player_training_id(trained_current) not in current_required
    assert player_training_id(trained_current) in future_required
    assert player_training_id(trained_future) in current_required
    assert player_training_id(trained_future) not in future_required


def test_match_training_context_uses_match_date_cycle(tmp_path):
    service = make_service(tmp_path)
    current_only = player("Current Only")
    future_only = player("Future Only")
    save_required(service, current_only, future_only)
    state = service.load_state()
    future_cycle = "2026-08-09:PLAYMAKING"
    service._repository.save(
        WeeklyTrainingState(
            active_training_type=state.active_training_type,
            active_week=state.active_week,
            priorities=state.priorities,
            match_records=(
                played_record(state.active_week.week_id, current_only),
                played_record(future_cycle, future_only),
            ),
            archived_weeks=state.archived_weeks,
        )
    )

    context = service.match_training_context(date(2026, 8, 12), [current_only, future_only])

    assert context.training_cycle_id == future_cycle
    assert context.suggested_role == "second"
    assert context.end_date == date(2026, 8, 15)
    assert player_training_id(current_only) in context.required_player_ids
    assert player_training_id(future_only) not in context.required_player_ids


def test_match_analysis_result_persists_training_context_fields():
    result = MatchAnalysisResult(
        player_count=19,
        opponent_name="Santa Cruz Club",
        formations=[],
        training_cycle_id="2026-08-09:PLAYMAKING",
        weekly_cycle_revision_used="abc123",
        training_context_timestamp="2026-08-04T10:00:00",
        training_context_summary="Training cycle 2026-08-09:PLAYMAKING",
        training_context_stale=True,
    )

    restored = match_analysis_result_from_dict(match_analysis_result_to_dict(result))

    assert restored.training_cycle_id == "2026-08-09:PLAYMAKING"
    assert restored.weekly_cycle_revision_used == "abc123"
    assert restored.training_context_timestamp == "2026-08-04T10:00:00"
    assert restored.training_context_summary == "Training cycle 2026-08-09:PLAYMAKING"
    assert restored.training_context_stale is True


def test_week_selector_view_uses_cycle_item_data(tmp_path):
    QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication
    from ht_coach_app.views.squad_page import SquadPage

    QApplication.instance() or QApplication([])
    service = make_service(tmp_path)
    page = SquadPage()
    options = service.visible_cycle_options()

    page.set_weekly_cycle_options(options, selected_cycle_id=options[1].cycle_id)

    assert page.selected_weekly_cycle_id() == "2026-08-09:PLAYMAKING"
    assert page.weekly_cycle_combo_v2.currentData()["relative_offset"] == 1


def test_week_selector_labels_render_offsets_without_warnings(tmp_path, caplog):
    QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication
    from ht_coach_app.views.squad_page import SquadPage

    QApplication.instance() or QApplication([])
    service = make_service(tmp_path)
    options = service.visible_cycle_options()

    expectations = {
        "en": [
            "Current - 02/08/2026 to 08/08/2026",
            "+1 - 09/08/2026 to 15/08/2026",
            "+2 - 16/08/2026 to 22/08/2026",
        ],
        "es": [
            "Actual - 02/08/2026 a 08/08/2026",
            "+1 - 09/08/2026 a 15/08/2026",
            "+2 - 16/08/2026 a 22/08/2026",
        ],
    }

    for language, expected_labels in expectations.items():
        configure_localization(language)
        page = SquadPage()
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="ht_coach_app.core.localization"):
            page.set_weekly_cycle_options(options)

        rendered = [
            page.weekly_cycle_combo_v2.itemText(index)
            for index in range(page.weekly_cycle_combo_v2.count())
        ]
        messages = [record.getMessage() for record in caplog.records]

        assert rendered == expected_labels
        assert "Missing localization parameter: offset" not in "\n".join(messages)

    configure_localization("en")
