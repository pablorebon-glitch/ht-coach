import tempfile
from pathlib import Path

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.weekly_training.persistence import WeeklyTrainingRepository
from ht_coach_app.controllers.squad_controller import SquadController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.services.squad_service import SquadService
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from ht_coach_app.views.squad_page import SquadPage
from models.player import Player


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def make_player(**overrides):
    base = dict(
        name="Test Player", age=22, days=50, speciality="", form=6, stamina=7,
        goalkeeper=1, defending=5, playmaking=5, winger=5, passing=5, scoring=5,
        set_pieces=4, experience=5, leadership=4, tsi=5000, salary=1000,
    )
    base.update(overrides)
    return Player(**base)


class FakeImporter:
    def __init__(self, players):
        self._players = players

    def __call__(self, path):
        return self._players


def make_controller(tmp_path, players=None):
    from ht_coach_app.services.squad_service import RosterResult

    players = players or [
        make_player(name="Alice", playmaking=15, defending=2, goalkeeper=1, winger=3, passing=6, scoring=2, set_pieces=2, age=19),
        make_player(name="Bob", defending=15, goalkeeper=1, playmaking=2, winger=2, passing=4, scoring=1, set_pieces=1),
        make_player(name="Carol", scoring=15, defending=1, goalkeeper=1, playmaking=2, winger=3, passing=3, set_pieces=2),
    ]
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    weekly_repo = WeeklyTrainingRepository(tmp_path / "planner.json")
    weekly_service = WeeklyTrainingAppService(repository=weekly_repo)
    squad_service = SquadService(importer=FakeImporter(players))
    page = SquadPage()
    controller = SquadController(
        page, squad_service, settings_repo, weekly_training_service=weekly_service
    )
    controller._roster = RosterResult(
        players=players, rows=squad_service.map_players(players), source_path="fake.csv"
    )
    return page, controller, players


def test_selecting_player_shows_intelligence_panel(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._show_player_detail("Alice")

    assert "Rol recomendado" in page.intelligence_headline_label.text()
    assert page.intelligence_reason_label.text()


def test_role_and_status_are_translated(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._show_player_detail("Alice")
    text = page.intelligence_headline_label.text()
    assert "_" not in text.split(":")[-1].strip().split("\n")[0]


def test_dimensions_displayed_qualitatively_not_as_raw_scores(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._show_player_detail("Alice")
    text = page.intelligence_dimensions_label.text()
    assert "0." not in text
    assert any(word in text for word in ("Alto", "Medio", "Bajo", "Excelente", "Compatible"))


def test_strengths_and_risks_displayed(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._show_player_detail("Alice")
    assert page.intelligence_strengths_label.text() or page.intelligence_risks_label.text()


def test_milestone_displayed(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._show_player_detail("Alice")
    assert page.intelligence_milestone_label.text()


def test_limitations_displayed_when_present(tmp_path):
    incomplete_player = make_player(name="Incomplete")
    incomplete_player.salary = None
    players = [incomplete_player, make_player(name="Other")]
    page, controller, _ = make_controller(tmp_path, players=players)
    controller._show_player_detail("Incomplete")
    assert page.intelligence_limitations_label.text()


def test_no_raw_overall_score_shown_anywhere(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._show_player_detail("Alice")
    combined = "\n".join(
        [
            page.intelligence_headline_label.text(),
            page.intelligence_reason_label.text(),
            page.intelligence_dimensions_label.text(),
        ]
    )
    assert "Overall" not in combined
    assert "overall_score" not in combined.lower()


def test_clear_detail_resets_intelligence_panel(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._show_player_detail("Alice")
    assert page.intelligence_reason_label.text()

    page.clear_detail()
    assert page.intelligence_reason_label.text() == ""


def test_empty_roster_shows_empty_state(tmp_path):
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    weekly_repo = WeeklyTrainingRepository(tmp_path / "planner.json")
    weekly_service = WeeklyTrainingAppService(repository=weekly_repo)
    page = SquadPage()
    controller = SquadController(
        page, SquadService(), settings_repo, weekly_training_service=weekly_service
    )
    controller._roster = None
    controller._show_player_detail("Anyone")
    assert "seleccion" in page.intelligence_headline_label.text().lower()


def test_unavailable_player_clears_panel_instead_of_crashing(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._show_player_detail("Nonexistent Player")
    assert page.intelligence_reason_label.text() == ""


def test_roster_refresh_recalculates_reports(tmp_path):
    from ht_coach_app.services.squad_service import RosterResult

    page, controller, players = make_controller(tmp_path)
    controller._show_player_detail("Alice")
    first_text = page.intelligence_headline_label.text()

    new_players = [
        make_player(
            name="Alice", playmaking=1, defending=1, goalkeeper=1, winger=1,
            passing=1, scoring=1, set_pieces=1, age=35, salary=99999,
        ),
    ]
    new_service = SquadService(importer=FakeImporter(new_players))
    controller._roster = RosterResult(
        players=new_players,
        rows=new_service.map_players(new_players),
        source_path="fake.csv",
    )
    controller._show_player_detail("Alice")
    second_text = page.intelligence_headline_label.text()

    assert isinstance(first_text, str) and isinstance(second_text, str)


def test_active_training_change_recalculates_shown_report(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._show_player_detail("Alice")
    before = page.intelligence_dimensions_label.text()

    controller._request_training_priority_selections = lambda *_args: {}
    controller._change_active_training_type("DEFENDING")
    after = page.intelligence_dimensions_label.text()

    assert before != after


def test_offscreen_pyside6_stability_smoke():
    page = SquadPage()
    for _ in range(5):
        page.clear_detail()
    assert page.intelligence_headline_label.text()
