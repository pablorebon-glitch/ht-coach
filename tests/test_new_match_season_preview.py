import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.calendar.season_calendar import SeasonCalendarConfig
from engine.calendar.season_calendar_repository import SeasonCalendarRepository
from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.services.match_workspace_service import MatchWorkspaceService
from ht_coach_app.services.opponent_service import OpponentService
from ht_coach_app.views.match_page import MatchPage


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def make_controller(tmp_path):
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
    opponent_service = OpponentService(opponent_repo)
    match_service = MatchWorkspaceService(opponent_service)
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    season_repo = SeasonCalendarRepository(tmp_path / "season.json")
    page = MatchPage()
    controller = MatchController(
        page, match_service, settings_repo, season_calendar_repository=season_repo,
    )
    return page, controller, season_repo


def test_preview_shows_not_configured_when_no_season_calendar_set(tmp_path):
    page, controller, season_repo = make_controller(tmp_path)
    page.set_match_date("2026-08-09")
    assert "sin configurar" in page.season_preview_label.text()


def test_preview_never_blocks_match_creation_without_config(tmp_path):
    page, controller, season_repo = make_controller(tmp_path)
    page.set_match_date("2026-08-09")
    assert "Ciclo de entrenamiento" in page.season_preview_label.text()


def test_preview_shows_season_and_week_once_configured(tmp_path):
    page, controller, season_repo = make_controller(tmp_path)
    season_repo.save(
        SeasonCalendarConfig(season_number=95, season_start_date="2026-07-27", total_weeks=16)
    )
    page.set_match_date("2026-08-09")

    text = page.season_preview_label.text()
    assert "Temporada HT 95" in text
    assert "Semana competitiva 2" in text


def test_preview_updates_when_date_changes(tmp_path):
    page, controller, season_repo = make_controller(tmp_path)
    season_repo.save(
        SeasonCalendarConfig(season_number=95, season_start_date="2026-07-27", total_weeks=16)
    )
    page.set_match_date("2026-08-09")
    first_text = page.season_preview_label.text()

    page.set_match_date("2026-08-17")
    second_text = page.season_preview_label.text()

    assert first_text != second_text
    assert "Semana competitiva 4" in second_text


def test_preview_shows_training_cycle_alongside_season(tmp_path):
    page, controller, season_repo = make_controller(tmp_path)
    season_repo.save(
        SeasonCalendarConfig(season_number=95, season_start_date="2026-07-27", total_weeks=16)
    )
    page.set_match_date("2026-08-09")

    text = page.season_preview_label.text()
    assert "Ciclo de entrenamiento" in text


def test_preview_computed_on_controller_init_for_default_date(tmp_path):
    page, controller, season_repo = make_controller(tmp_path)
    assert page.season_preview_label.text() != ""


def test_controller_without_season_repository_does_not_crash(tmp_path):
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
    opponent_service = OpponentService(opponent_repo)
    match_service = MatchWorkspaceService(opponent_service)
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    page = MatchPage()
    controller = MatchController(page, match_service, settings_repo)
    page.set_match_date("2026-08-09")
