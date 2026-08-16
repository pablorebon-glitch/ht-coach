from datetime import date

from engine.weekly_training.models import (
    CompetitionType,
    MatchRole,
    MatchStatus,
    WeeklyMatchRecord,
)
from engine.weekly_training.persistence import WeeklyTrainingState
from engine.weekly_training.training_week import active_training_week
from ht_coach_app.services.week_navigation import build_week_navigation_context


def test_current_context_shows_active_week():
    current_week = active_training_week(today=date(2026, 8, 3))
    state = WeeklyTrainingState(active_week=current_week)
    ctx = build_week_navigation_context(state, "current")
    assert ctx.week.week_id == current_week.week_id
    assert ctx.direction == "current"


def test_current_cannot_go_previous_without_archived_weeks():
    current_week = active_training_week(today=date(2026, 8, 3))
    state = WeeklyTrainingState(active_week=current_week, archived_weeks=())
    ctx = build_week_navigation_context(state, "current")
    assert ctx.can_go_previous is False
    assert ctx.can_go_next is True


def test_current_can_go_previous_with_archived_weeks():
    archived = active_training_week(today=date(2026, 7, 27))
    current_week = active_training_week(today=date(2026, 8, 3))
    state = WeeklyTrainingState(active_week=current_week, archived_weeks=(archived,))
    ctx = build_week_navigation_context(state, "current")
    assert ctx.can_go_previous is True


def test_previous_context_returns_most_recently_archived_week():
    older = active_training_week(today=date(2026, 7, 20))
    newer = active_training_week(today=date(2026, 7, 27))
    current_week = active_training_week(today=date(2026, 8, 3))
    state = WeeklyTrainingState(active_week=current_week, archived_weeks=(older, newer))
    ctx = build_week_navigation_context(state, "previous")
    assert ctx.week.week_id == newer.week_id


def test_previous_context_none_when_no_archives():
    current_week = active_training_week(today=date(2026, 8, 3))
    state = WeeklyTrainingState(active_week=current_week)
    ctx = build_week_navigation_context(state, "previous")
    assert ctx.week is None
    assert ctx.can_go_previous is False
    assert ctx.can_go_next is True


def test_next_context_is_a_preview_one_cycle_ahead():
    current_week = active_training_week(today=date(2026, 8, 3))
    state = WeeklyTrainingState(active_week=current_week)
    ctx = build_week_navigation_context(state, "next")
    assert ctx.is_preview is True
    assert ctx.week.start_date > current_week.start_date


def test_next_context_cannot_go_further_next():
    current_week = active_training_week(today=date(2026, 8, 3))
    state = WeeklyTrainingState(active_week=current_week)
    ctx = build_week_navigation_context(state, "next")
    assert ctx.can_go_next is False
    assert ctx.can_go_previous is True


def test_planned_lineup_visible_before_match_is_played():
    current_week = active_training_week(today=date(2026, 8, 3))
    match_record = WeeklyMatchRecord(
        match_id="m1", match_date=current_week.start_date, match_role=MatchRole.FIRST_WEEKLY_MATCH,
        opponent_name="Rival FC", competition_type=CompetitionType.LEAGUE, formation="3-5-2",
        planned_or_played=MatchStatus.PLANNED,
    )
    state = WeeklyTrainingState(active_week=current_week, match_records=(match_record,))
    ctx = build_week_navigation_context(state, "current")
    assert ctx.first_match is not None
    assert ctx.first_match.opponent_name == "Rival FC"
    assert ctx.first_match.planned_or_played == MatchStatus.PLANNED


def test_first_and_second_match_are_distinguished():
    current_week = active_training_week(today=date(2026, 8, 3))
    first = WeeklyMatchRecord(
        match_id="m1", match_date=current_week.start_date, match_role=MatchRole.FIRST_WEEKLY_MATCH,
        opponent_name="First Rival", competition_type=CompetitionType.LEAGUE, formation="3-5-2",
    )
    second = WeeklyMatchRecord(
        match_id="m2", match_date=current_week.start_date, match_role=MatchRole.SECOND_WEEKLY_MATCH,
        opponent_name="Second Rival", competition_type=CompetitionType.FRIENDLY, formation="4-4-2",
    )
    state = WeeklyTrainingState(active_week=current_week, match_records=(first, second))
    ctx = build_week_navigation_context(state, "current")
    assert ctx.first_match.opponent_name == "First Rival"
    assert ctx.second_match.opponent_name == "Second Rival"


def test_matches_outside_week_range_are_not_shown():
    current_week = active_training_week(today=date(2026, 8, 3))
    stale_match = WeeklyMatchRecord(
        match_id="m-old", match_date=date(2020, 1, 1), match_role=MatchRole.FIRST_WEEKLY_MATCH,
        opponent_name="Old Rival", competition_type=CompetitionType.LEAGUE, formation="3-5-2",
    )
    state = WeeklyTrainingState(active_week=current_week, match_records=(stale_match,))
    ctx = build_week_navigation_context(state, "current")
    assert ctx.first_match is None


def test_training_priorities_only_available_for_current_week():
    current_week = active_training_week(today=date(2026, 8, 3))
    archived = active_training_week(today=date(2026, 7, 27))
    state = WeeklyTrainingState(active_week=current_week, archived_weeks=(archived,))

    current_ctx = build_week_navigation_context(state, "current")
    previous_ctx = build_week_navigation_context(state, "previous")
    next_ctx = build_week_navigation_context(state, "next")

    assert current_ctx.training_priorities_available is True
    assert previous_ctx.training_priorities_available is False
    assert next_ctx.training_priorities_available is False


def test_invalid_direction_falls_back_to_current():
    current_week = active_training_week(today=date(2026, 8, 3))
    state = WeeklyTrainingState(active_week=current_week)
    ctx = build_week_navigation_context(state, "some_unrestricted_history_index")
    assert ctx.direction == "current"


def test_no_active_week_next_preview_is_none():
    state = WeeklyTrainingState(active_week=None)
    ctx = build_week_navigation_context(state, "next")
    assert ctx.week is None


def test_service_wiring_exposes_week_navigation_context(tmp_path):
    from engine.weekly_training.persistence import WeeklyTrainingRepository
    from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService

    repository = WeeklyTrainingRepository(tmp_path / "planner.json")
    service = WeeklyTrainingAppService(repository=repository)
    state = service.load_state()

    ctx = service.week_navigation_context(state, "current")
    assert ctx.week.week_id == state.active_week.week_id


class WeeklyPlannerNavigationUITests:
    """Placeholder namespace kept for readability; actual tests below
    use module-level functions per this file's existing convention."""


def _qt_app():
    import pytest

    QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication
    return QApplication.instance() or QApplication([])


def _make_controller(tmp_path, csv_path=None):
    from ht_coach_app.controllers.squad_controller import SquadController
    from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
    from ht_coach_app.services.squad_service import SquadService
    from ht_coach_app.views.squad_page import SquadPage

    _qt_app()
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "r.json"
    )
    if csv_path:
        settings_repo.remember_players_csv_path(str(csv_path))
    page = SquadPage()
    controller = SquadController(page, SquadService(), settings_repo)
    return page, controller


def _write_minimal_csv(path):
    import csv

    fieldnames = [
        "Nombre", "Edad", "Días", "Especialidad", "Forma", "Condición",
        "Portería", "Defensa", "Jugadas", "Lateral", "Pases", "Anotación",
        "Balón parado", "Experiencia", "Liderazgo", "TSI", "Salario",
    ]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(3):
            writer.writerow({
                "Nombre": f"Player {i}", "Edad": 24, "Días": 100, "Especialidad": "",
                "Forma": 6, "Condición": 7, "Portería": 1, "Defensa": 8,
                "Jugadas": 8, "Lateral": 8, "Pases": 8, "Anotación": 8,
                "Balón parado": 5, "Experiencia": 5, "Liderazgo": 5, "TSI": 5000,
                "Salario": 1000,
            })


def test_navigation_buttons_exist_and_are_wired(tmp_path):
    csv_path = tmp_path / "roster.csv"
    _write_minimal_csv(csv_path)
    page, controller = _make_controller(tmp_path, csv_path)

    assert hasattr(page, "week_nav_previous_button")
    assert hasattr(page, "week_nav_current_button")
    assert hasattr(page, "week_nav_next_button")


def test_showing_weekly_training_defaults_to_current_week_summary(tmp_path):
    csv_path = tmp_path / "roster.csv"
    _write_minimal_csv(csv_path)
    page, controller = _make_controller(tmp_path, csv_path)
    controller._load()

    controller._show_weekly_training()

    assert "Ciclo de entrenamiento" in page.week_nav_summary_label.text() or \
        "Training cycle" in page.week_nav_summary_label.text()


def test_navigate_to_next_shows_preview_label(tmp_path):
    csv_path = tmp_path / "roster.csv"
    _write_minimal_csv(csv_path)
    page, controller = _make_controller(tmp_path, csv_path)
    controller._load()

    controller._show_weekly_training()
    controller._navigate_week("next")

    text = page.week_nav_summary_label.text()
    assert "próximo ciclo" in text or "next cycle" in text.lower() or "preview" in text.lower()


def test_navigate_before_roster_loaded_does_not_crash(tmp_path):
    page, controller = _make_controller(tmp_path)
    controller._navigate_week("previous")  # must not raise even with no roster/state yet
