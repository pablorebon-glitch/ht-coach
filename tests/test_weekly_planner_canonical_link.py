from datetime import date, datetime

import pytest

from engine.history.match_deletion import find_linked_weekly_match_records
from engine.history.models import (
    HistoricalMatchSnapshot,
    MatchContext,
    OpponentReference,
    TacticalSetup,
)
from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.provisional_record import find_or_create_provisional_record
from engine.history.repository import HistoricalMatchRepository
from engine.weekly_training.models import (
    CompetitionType,
    MatchRole,
    MatchStatus,
    WeeklyMatchRecord,
)
from engine.weekly_training.persistence import WeeklyTrainingRepository, WeeklyTrainingState
from models.player import Player


@pytest.fixture()
def repository(tmp_path):
    return HistoricalMatchRepository(tmp_path / "snapshots.json")


@pytest.fixture()
def weekly_repository(tmp_path):
    return WeeklyTrainingRepository(tmp_path / "planner.json")


def _weekly_match(linked_match_record_id="", opponent="CA Chaco", match_date=date(2026, 8, 9)):
    return WeeklyMatchRecord(
        match_id="w1", match_date=match_date, match_role=MatchRole.FIRST_WEEKLY_MATCH,
        opponent_name=opponent, competition_type=CompetitionType.LEAGUE, formation="3-5-2",
        linked_match_record_id=linked_match_record_id,
    )


def test_weekly_match_record_defaults_to_no_link():
    record = WeeklyMatchRecord(
        match_id="w1", match_date=date(2026, 8, 9), match_role=MatchRole.FIRST_WEEKLY_MATCH,
    )
    assert record.linked_match_record_id == ""


def test_weekly_match_record_link_roundtrips_through_persistence(weekly_repository):
    record = _weekly_match(linked_match_record_id="canonical-123")
    weekly_repository.save(WeeklyTrainingState(match_records=(record,)))

    reloaded = weekly_repository.load()
    assert reloaded.match_records[0].linked_match_record_id == "canonical-123"


def test_legacy_weekly_record_without_link_still_loads(weekly_repository, tmp_path):
    import json

    payload = {
        "schema_version": 1,
        "active_training_type": "PLAYMAKING",
        "active_week": None,
        "priorities": {},
        "match_records": [{
            "match_id": "legacy1", "match_date": "2026-08-09",
            "match_role": "FIRST_WEEKLY_MATCH", "opponent_name": "CA Chaco",
            "competition_type": "LEAGUE", "formation": "3-5-2",
            "lineup": [], "planned_or_played": "PLANNED", "source": "manual",
            "minutes_known": False, "notes": "", "training_exposure_entries": [],
        }],
        "archived_weeks": [], "diagnostics": [],
    }
    (tmp_path / "legacy.json").write_text(json.dumps(payload), encoding="utf-8")
    legacy_repo = WeeklyTrainingRepository(tmp_path / "legacy.json")

    state = legacy_repo.load()
    assert state.match_records[0].linked_match_record_id == ""


def test_find_linked_prefers_canonical_id_over_inference():
    canonical = HistoricalMatchSnapshot(
        snapshot_id="canonical-1",
        match_context=MatchContext(
            match_date="2026-08-09", opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
    )
    weekly_state = WeeklyTrainingState(match_records=(_weekly_match(linked_match_record_id="canonical-1"),))

    linked = find_linked_weekly_match_records(weekly_state, canonical)
    assert len(linked) == 1
    assert linked[0].linked_match_record_id == "canonical-1"


def test_find_linked_falls_back_to_inference_when_no_id_present():
    canonical = HistoricalMatchSnapshot(
        snapshot_id="canonical-1",
        match_context=MatchContext(
            match_date="2026-08-09", opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
    )
    weekly_state = WeeklyTrainingState(match_records=(_weekly_match(linked_match_record_id=""),))

    linked = find_linked_weekly_match_records(weekly_state, canonical)
    assert len(linked) == 1


def test_find_linked_never_claims_a_record_linked_to_a_different_canonical_id():
    other_canonical = HistoricalMatchSnapshot(
        snapshot_id="canonical-2",
        match_context=MatchContext(
            match_date="2026-08-09", opponent=OpponentReference(opponent_name="CA Chaco"),
        ),
    )
    weekly_state = WeeklyTrainingState(
        match_records=(_weekly_match(linked_match_record_id="canonical-1"),)
    )

    linked = find_linked_weekly_match_records(weekly_state, other_canonical)
    assert linked == ()


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication
    QApplication.instance() or QApplication([])


def make_match_controller(tmp_path):
    from ht_coach_app.controllers.match_controller import MatchController
    from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
    from ht_coach_app.persistence.opponent_repository import OpponentRepository
    from ht_coach_app.services.match_workspace_service import MatchWorkspaceService
    from ht_coach_app.services.official_rating_service import OfficialRatingImportService
    from ht_coach_app.services.opponent_service import OpponentService
    from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
    from ht_coach_app.views.match_page import MatchPage

    hist_repo = HistoricalMatchRepository(tmp_path / "snapshots.json")
    weekly_repo = WeeklyTrainingRepository(tmp_path / "planner.json")
    weekly_service = WeeklyTrainingAppService(repository=weekly_repo)
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
    opponent_service = OpponentService(opponent_repo)
    match_service = MatchWorkspaceService(opponent_service)
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    official_service = OfficialRatingImportService(repository=hist_repo)
    page = MatchPage()
    controller = MatchController(
        page, match_service, settings_repo, weekly_training_service=weekly_service,
        official_rating_service=official_service,
    )
    page.set_match_type("LEAGUE")
    return page, controller, hist_repo, weekly_repo


def _analysis_result(opponent="CA Chaco", match_type="LEAGUE", formation_name="3-5-2"):
    from ht_coach_app.services.match_workspace_service import (
        FormationAnalysisResult,
        LineupPlayerResult,
        MatchAnalysisResult,
        TeamRatingsResult,
    )

    formation = FormationAnalysisResult(
        formation_name=formation_name, recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=TeamRatingsResult(),
        lineup=[
            LineupPlayerResult(
                number=i, position="INNER_MIDFIELDER", side="CENTER",
                order="Normal", order_side="", player_name=f"P{i}",
            )
            for i in range(1, 12)
        ],
    )
    return MatchAnalysisResult(
        player_count=18,
        opponent_name=opponent,
        formations=[formation],
        match_type=match_type,
    )


def _analysis_result_with_recommendation_and_visible_option(match_type="CUP"):
    from dataclasses import replace
    from ht_coach_app.services.match_workspace_service import MatchAnalysisResult

    recommended = _analysis_result(match_type=match_type, formation_name="3-5-2").formations[0]
    visible = replace(
        _analysis_result(match_type=match_type, formation_name="2-5-3").formations[0],
        is_recommended=False,
    )
    return MatchAnalysisResult(
        player_count=18,
        opponent_name="CA Chaco",
        formations=[recommended, visible],
        match_type=match_type,
    )


def _historical_253_result(match_type="CUP"):
    from ht_coach_app.services.match_workspace_service import (
        FormationAnalysisResult,
        LineupPlayerResult,
        MatchAnalysisResult,
        TeamRatingsResult,
    )

    slots = (
        ("GOALKEEPER", "CENTER"),
        ("CENTRAL_DEFENDER", "LEFT"),
        ("CENTRAL_DEFENDER", "RIGHT"),
        ("INNER_MIDFIELDER", "LEFT"),
        ("INNER_MIDFIELDER", "CENTER"),
        ("INNER_MIDFIELDER", "RIGHT"),
        ("WINGER", "LEFT"),
        ("WINGER", "RIGHT"),
        ("FORWARD", "LEFT"),
        ("FORWARD", "CENTER"),
        ("FORWARD", "RIGHT"),
    )
    formation = FormationAnalysisResult(
        formation_name="2-5-3",
        recommended_tactic="Normal",
        tactic_level=5,
        win_probability=0.5,
        draw_probability=0.3,
        loss_probability=0.2,
        possession=50.0,
        expected_goals=1.5,
        opponent_expected_goals=1.2,
        is_recommended=True,
        team_ratings=TeamRatingsResult(),
        lineup=[
            LineupPlayerResult(
                number=index,
                position=position,
                side=side,
                order="Normal",
                order_side="",
                player_name=f"Historico {index}",
            )
            for index, (position, side) in enumerate(slots, start=1)
        ],
    )
    return MatchAnalysisResult(
        player_count=18,
        opponent_name="Santa Cruz Club",
        formations=[formation],
        match_type=match_type,
    )


def _manual_roster(count=11):
    return [
        Player(
            name=f"Manual Player {index}",
            age=25,
            days=0,
            speciality="",
            form=7,
            stamina=7,
            goalkeeper=8 if index == 1 else 1,
            defending=9,
            playmaking=9,
            winger=9,
            passing=7,
            scoring=9,
            set_pieces=5,
            experience=5,
            leadership=4,
            tsi=1000 + index,
            salary=1000,
        )
        for index in range(1, count + 1)
    ]


def _fill_visible_board_from_roster(board_widget, roster):
    for slot, player in zip(board_widget.current_board().slots, roster):
        state = board_widget.workspace_state()
        board_widget._workspace_state = board_widget._workspace_service.place_bench_player_in_empty_slot(
            state,
            roster,
            "2-5-3",
            slot.slot_id,
            player.name.lower().replace(" ", "_"),
            state.revision,
            interaction_source="TEST",
        )
        board_widget._sync_boards_cache()
    board_widget.workspace_modified.emit(board_widget.workspace_state())


def test_saving_first_match_populates_the_canonical_link(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    controller._settings_repository.save_last_result(_analysis_result())
    controller._roster_players = []

    controller._save_as_first_match()

    weekly_state = weekly_repo.load()
    linked_id = weekly_state.match_records[0].linked_match_record_id
    assert linked_id
    assert hist_repo.get(linked_id) is not None
    assert controller._active_match_record_id == linked_id
    assert controller._editing_snapshot_id == linked_id


def test_saving_first_match_never_creates_a_second_canonical_record_on_repeat_save(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    page.confirm_replace_first_match = lambda *args: True
    controller._settings_repository.save_last_result(_analysis_result())
    controller._roster_players = []

    controller._save_as_first_match()
    controller._save_as_first_match()

    assert len(hist_repo.list_all()) == 1


def test_weekly_save_keeps_workspace_open_and_uses_same_canonical_record(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    controller._roster_players = []
    controller._analysis_finished(_analysis_result())

    controller._save_as_first_match()

    weekly_state = weekly_repo.load()
    linked_id = weekly_state.match_records[0].linked_match_record_id
    assert linked_id == controller._active_match_record_id
    assert linked_id == controller._editing_snapshot_id
    assert page._formation_board_widget is not None
    assert page._state == "success"
    assert len(hist_repo.list_all()) == 1


def test_weekly_link_failure_keeps_canonical_save_and_workspace_intact(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    controller._roster_players = []
    controller._analysis_finished(_analysis_result())

    def fail_record_first_match(*args, **kwargs):
        raise RuntimeError("planner storage unavailable")

    controller._weekly_training_service.record_first_match = fail_record_first_match

    controller._save_as_first_match()

    records = hist_repo.list_all()
    assert len(records) == 1
    assert controller._active_match_record_id == records[0].snapshot_id
    assert page._formation_board_widget is not None
    assert page._state == "error"
    assert weekly_repo.load().match_records == ()


def test_editing_record_links_saved_match_to_the_record_being_edited(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    controller._editing_snapshot_id = record.snapshot_id
    controller._settings_repository.save_last_result(_analysis_result())
    controller._roster_players = []

    controller._save_as_first_match()

    weekly_state = weekly_repo.load()
    assert weekly_state.match_records[0].linked_match_record_id == record.snapshot_id
    assert len(hist_repo.list_all()) == 1


def test_cup_analysis_saved_as_second_match_preserves_cup_metadata(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    page.set_match_type("CUP")
    page.confirm_save_match_type_mismatch = lambda *args: pytest.fail(
        "slot save must not ask for a match-type override"
    )
    controller._roster_players = []
    controller._analysis_finished(_analysis_result(match_type="CUP"))

    controller._save_as_second_match()

    weekly_state = weekly_repo.load()
    record = weekly_state.match_records[0]
    assert record.match_role == MatchRole.SECOND_WEEKLY_MATCH
    assert record.competition_type == CompetitionType.CUP
    linked = hist_repo.get(record.linked_match_record_id)
    assert linked.match_context.competition_type.value == "cup"


def test_saving_second_match_persists_visible_formation_not_cached_recommendation(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    page.set_match_type("CUP")
    controller._roster_players = []
    controller._analysis_finished(_analysis_result_with_recommendation_and_visible_option())

    combo = page._formation_board_widget.formation_combo
    combo.setCurrentIndex(combo.findData("2-5-3"))
    assert page._formation_board_widget.current_board().formation_name == "2-5-3"
    assert controller._settings_repository.load_last_result().recommended_formation.formation_name == "3-5-2"

    controller._save_as_second_match()

    record = weekly_repo.load().match_records[0]
    saved = hist_repo.get(record.linked_match_record_id)
    assert record.formation == "2-5-3"
    assert saved.tactical_setup.formation == "2-5-3"


def test_league_analysis_saved_as_first_match_preserves_league_metadata(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    page.set_match_type("LEAGUE")
    controller._roster_players = []
    controller._analysis_finished(_analysis_result(match_type="LEAGUE"))

    controller._save_as_first_match()

    record = weekly_repo.load().match_records[0]
    assert record.match_role == MatchRole.FIRST_WEEKLY_MATCH
    assert record.competition_type == CompetitionType.LEAGUE


def test_cup_analysis_saved_as_first_match_is_not_forced_to_league(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    page.set_match_type("CUP")
    controller._roster_players = []
    controller._analysis_finished(_analysis_result(match_type="CUP"))

    controller._save_as_first_match()

    record = weekly_repo.load().match_records[0]
    assert record.match_role == MatchRole.FIRST_WEEKLY_MATCH
    assert record.competition_type == CompetitionType.CUP


def test_changing_match_type_after_analysis_marks_result_stale(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    page.set_match_type("LEAGUE")
    controller._analysis_finished(_analysis_result(match_type="LEAGUE"))

    page.set_match_type("CUP")

    assert page._analysis_stale is True
    assert page._formation_board_widget.save_as_first_match_button.isEnabled() is False
    assert page._formation_board_widget.save_as_second_match_button.isEnabled() is False
    controller._save_as_second_match()
    assert weekly_repo.load().match_records == ()


def test_reanalysis_refreshes_match_type_provenance_after_stale_change(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    page.set_match_type("LEAGUE")
    controller._analysis_finished(_analysis_result(match_type="LEAGUE"))
    page.set_match_type("CUP")

    controller._analysis_finished(_analysis_result(match_type="CUP"))
    controller._save_as_second_match()

    assert page._analysis_stale is False
    saved_result = controller._settings_repository.load_last_result()
    assert saved_result.match_type == "CUP"
    assert weekly_repo.load().match_records[0].competition_type == CompetitionType.CUP


def test_new_match_clears_inherited_match_type_and_results(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    page.set_match_type("LEAGUE")
    controller._analysis_finished(_analysis_result(match_type="LEAGUE"))
    page.confirm_unsaved_changes = lambda: "discard"

    assert controller.start_new_match() is True

    assert page.match_type() == ""
    assert page._last_result is None
    assert page._analysis_stale is False


def test_saved_match_restores_its_canonical_match_type(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    page.set_match_type("LEAGUE")
    record = find_or_create_provisional_record(
        hist_repo,
        opponent_name="CA Chaco",
        match_date="2026-08-09",
        competition_type="cup",
    )

    controller.edit_record(record.snapshot_id)

    assert page.match_type() == "CUP"


def test_saved_historical_sunday_can_be_assigned_as_match_one_without_reanalysis(tmp_path):
    from engine.calendar import HTCalendarService
    from ht_coach_app.core.localization import t
    from ht_coach_app.services import ht_week_context_provider

    original_service = ht_week_context_provider.get_calendar_service()
    ht_week_context_provider.set_calendar_service(
        HTCalendarService(clock=lambda: datetime(2026, 9, 7, 12, 0))
    )
    try:
        page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
        page.set_match_type("CUP")
        page.set_match_date("2026-09-06")
        controller._analysis_finished(_historical_253_result())
        controller._save_formation()
        record = hist_repo.list_all()[0]
        controller._settings_repository.clear_last_result()
        controller._editing_snapshot_id = ""
        controller._active_match_record_id = ""

        controller.edit_record(record.snapshot_id)

        assert page.status_label.text() == t("match.saved_formation_restored")
        controller._settings_repository.clear_last_result()

        controller._save_as_first_match()

        weekly_state = weekly_repo.load()
        saved = next(
            item
            for item in weekly_state.match_records
            if item.linked_match_record_id == record.snapshot_id
        )
        assert saved.match_id == "2026-09-06:PLAYMAKING:first"
        assert saved.match_role == MatchRole.FIRST_WEEKLY_MATCH
        assert saved.match_date.isoformat() == "2026-09-06"
        assert saved.planned_or_played == MatchStatus.PLAYED
        assert saved.formation == "2-5-3"
        assert len(saved.lineup) == 11
        assert len(saved.training_exposure_entries) == 11
        assert len(hist_repo.list_all()) == 1
    finally:
        ht_week_context_provider.set_calendar_service(original_service)


def test_historical_weekly_link_moves_between_slots_without_duplicate_exposure(tmp_path):
    from engine.calendar import HTCalendarService
    from ht_coach_app.services import ht_week_context_provider

    original_service = ht_week_context_provider.get_calendar_service()
    ht_week_context_provider.set_calendar_service(
        HTCalendarService(clock=lambda: datetime(2026, 9, 7, 12, 0))
    )
    try:
        page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
        page.set_match_type("CUP")
        page.set_match_date("2026-09-06")
        controller._analysis_finished(_historical_253_result())
        controller._save_formation()
        record = hist_repo.list_all()[0]
        controller.edit_record(record.snapshot_id)

        controller._save_as_second_match()
        controller._save_as_first_match()

        linked_records = [
            item
            for item in weekly_repo.load().match_records
            if item.linked_match_record_id == record.snapshot_id
        ]
        assert len(linked_records) == 1
        assert linked_records[0].match_id == "2026-09-06:PLAYMAKING:first"
        assert linked_records[0].match_role == MatchRole.FIRST_WEEKLY_MATCH
    finally:
        ht_week_context_provider.set_calendar_service(original_service)


def test_saved_match_without_lineup_opens_reconstructable_board(tmp_path):
    from ht_coach_app.core.localization import t

    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    record = find_or_create_provisional_record(
        hist_repo,
        opponent_name="Santa Cruz Club",
        match_date="2026-09-06",
        competition_type="cup",
    )
    hist_repo.save(
        record.with_updates(
            tactical_setup=TacticalSetup(
                formation="2-5-3",
                selected_tactic="Normal",
                tactic_level=0,
            )
        )
    )

    controller.edit_record(record.snapshot_id)

    assert page.status_label.text() == t("match.historical_lineup_missing")
    assert page._formation_board_widget is not None
    assert page._formation_board_widget.current_board().formation_name == "2-5-3"
    assert [
        slot
        for slot in page._formation_board_widget.current_board().slots
        if slot.player is not None
    ] == []
    controller._save_as_first_match()
    assert weekly_repo.load().match_records == ()


def test_manual_historical_reconstruction_persists_and_links_with_pre_evidence(tmp_path):
    from engine.calendar import HTCalendarService
    from ht_coach_app.services import ht_week_context_provider

    original_service = ht_week_context_provider.get_calendar_service()
    ht_week_context_provider.set_calendar_service(
        HTCalendarService(clock=lambda: datetime(2026, 9, 7, 12, 0))
    )
    try:
        page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
        record = find_or_create_provisional_record(
            hist_repo,
            opponent_name="Santa Cruz Club",
            match_date="2026-09-06",
            competition_type="cup",
        )
        hist_repo.save(
            record.with_updates(
                official_pre=OfficialRatingSnapshot(hattrick_match_id="pre-1"),
                tactical_setup=TacticalSetup(
                    formation="2-5-3",
                    selected_tactic="Normal",
                    tactic_level=0,
                ),
            )
        )
        roster = _manual_roster()
        controller._roster_players = roster
        controller._set_view_roster_players(roster)
        controller.edit_record(record.snapshot_id)

        board_widget = page._formation_board_widget
        _fill_visible_board_from_roster(board_widget, roster)

        assert board_widget.is_dirty()
        controller._save_formation()

        saved = hist_repo.get(record.snapshot_id)
        assert len(hist_repo.list_all()) == 1
        assert saved.official_pre is not None
        assert len(saved.lineup) == 11
        assert saved.provenance.lineup_source == "MANUAL_HISTORICAL_RECONSTRUCTION"

        controller._settings_repository.clear_last_result()
        controller._editing_snapshot_id = ""
        controller._active_match_record_id = ""
        controller.edit_record(record.snapshot_id)
        assert len(page._formation_board_widget.current_board().slots) == 11

        controller._save_as_first_match()
        weekly = next(
            item
            for item in weekly_repo.load().match_records
            if item.linked_match_record_id == record.snapshot_id
        )
        assert weekly.match_id == "2026-09-06:PLAYMAKING:first"
        assert len(weekly.lineup) == 11
    finally:
        ht_week_context_provider.set_calendar_service(original_service)


def test_reconstructed_saved_match_enables_and_clicks_match_one_without_analysis(tmp_path):
    from engine.calendar import HTCalendarService
    from ht_coach_app.core.localization import t
    from ht_coach_app.services import ht_week_context_provider

    original_service = ht_week_context_provider.get_calendar_service()
    ht_week_context_provider.set_calendar_service(
        HTCalendarService(clock=lambda: datetime(2026, 9, 7, 12, 0))
    )
    try:
        page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
        record = find_or_create_provisional_record(
            hist_repo,
            opponent_name="Santa Cruz Club",
            match_date="2026-09-06",
            competition_type="cup",
        )
        hist_repo.save(
            record.with_updates(
                tactical_setup=TacticalSetup(
                    formation="2-5-3",
                    selected_tactic="Normal",
                    tactic_level=0,
                ),
            )
        )
        roster = _manual_roster()
        controller._roster_players = roster
        controller._set_view_roster_players(roster)
        controller.edit_record(record.snapshot_id)
        controller._settings_repository.clear_last_result()

        board_widget = page._formation_board_widget
        assert board_widget.save_as_first_match_button.isEnabled() is False

        _fill_visible_board_from_roster(board_widget, roster)

        assert page._last_result is not None
        assert controller._settings_repository.load_last_result() is None
        assert board_widget.save_as_first_match_button.isEnabled() is True
        board_widget.save_as_first_match_button.click()

        weekly = next(
            item
            for item in weekly_repo.load().match_records
            if item.linked_match_record_id == record.snapshot_id
        )
        assert weekly.match_id == "2026-09-06:PLAYMAKING:first"
        assert weekly.match_role == MatchRole.FIRST_WEEKLY_MATCH
        assert weekly.planned_or_played == MatchStatus.PLAYED
        assert len(weekly.lineup) == 11
        saved = hist_repo.get(record.snapshot_id)
        assert len(saved.lineup) == 11
        assert page.status_label.text() == t(
            "match.save_as_weekly_success_with_range",
            slot=1,
            week_start="06/09/2026",
            week_end="12/09/2026",
        )
        assert len(hist_repo.list_all()) == 1
    finally:
        ht_week_context_provider.set_calendar_service(original_service)


def test_reconstructed_saved_match_enables_and_clicks_match_two_without_analysis(tmp_path):
    from engine.calendar import HTCalendarService
    from ht_coach_app.core.localization import t
    from ht_coach_app.services import ht_week_context_provider

    original_service = ht_week_context_provider.get_calendar_service()
    ht_week_context_provider.set_calendar_service(
        HTCalendarService(clock=lambda: datetime(2026, 9, 7, 12, 0))
    )
    try:
        page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
        record = find_or_create_provisional_record(
            hist_repo,
            opponent_name="Santa Cruz Club",
            match_date="2026-09-06",
            competition_type="cup",
        )
        hist_repo.save(
            record.with_updates(
                tactical_setup=TacticalSetup(
                    formation="2-5-3",
                    selected_tactic="Normal",
                    tactic_level=0,
                ),
            )
        )
        roster = _manual_roster()
        controller._roster_players = roster
        controller._set_view_roster_players(roster)
        controller.edit_record(record.snapshot_id)
        controller._settings_repository.clear_last_result()

        board_widget = page._formation_board_widget
        _fill_visible_board_from_roster(board_widget, roster)

        assert board_widget.save_as_second_match_button.isEnabled() is True
        board_widget.save_as_second_match_button.click()

        weekly = next(
            item
            for item in weekly_repo.load().match_records
            if item.linked_match_record_id == record.snapshot_id
        )
        assert weekly.match_id == "2026-09-06:PLAYMAKING:second"
        assert weekly.match_role == MatchRole.SECOND_WEEKLY_MATCH
        assert weekly.planned_or_played == MatchStatus.PLAYED
        assert len(weekly.lineup) == 11
        assert page.status_label.text() == t(
            "match.save_as_weekly_success_with_range",
            slot=2,
            week_start="06/09/2026",
            week_end="12/09/2026",
        )
        assert len(hist_repo.list_all()) == 1
    finally:
        ht_week_context_provider.set_calendar_service(original_service)


def test_match_type_uses_combo_item_data_not_visible_label(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    index = page.match_type_combo.findData("CUP")
    page.match_type_combo.setItemText(index, "Liga visual")
    page.match_type_combo.setCurrentIndex(index)

    assert page.match_type() == "CUP"
    assert controller._current_match_type() == "CUP"


def test_invalid_match_type_item_data_does_not_default_to_league(tmp_path):
    page, controller, hist_repo, weekly_repo = make_match_controller(tmp_path)
    page.match_type_combo.addItem("Valor invalido", "BROKEN")
    page.match_type_combo.setCurrentIndex(page.match_type_combo.count() - 1)

    assert controller._current_match_type() is None
    assert "valid" in page.status_label.text().lower() or "válido" in page.status_label.text().lower()
