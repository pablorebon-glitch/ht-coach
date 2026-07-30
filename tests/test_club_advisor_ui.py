import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from ht_coach_app.controllers.club_advisor_controller import ClubAdvisorController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.services.club_advisor_service import ClubAdvisorAppService
from ht_coach_app.services.squad_service import SquadService
from ht_coach_app.views.club_advisor_page import ClubAdvisorPage
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
    players = players or [
        make_player(name="Alice", goalkeeper=15, defending=2, playmaking=1, winger=1, passing=2, scoring=1, set_pieces=1),
        make_player(name="Bob", defending=15, goalkeeper=1, playmaking=2, winger=2, passing=4, scoring=1, set_pieces=1),
        make_player(name="Carol", playmaking=15, defending=3, goalkeeper=1, winger=4, passing=8, scoring=3, set_pieces=3, age=19),
        make_player(name="Dave", winger=15, defending=2, goalkeeper=1, playmaking=4, passing=5, scoring=6, set_pieces=2),
        make_player(name="Eve", scoring=15, defending=1, goalkeeper=1, playmaking=2, winger=3, passing=3, set_pieces=2),
    ]
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    squad_service = SquadService(importer=FakeImporter(players))
    fake_csv = tmp_path / "fake.csv"
    fake_csv.write_text("name\n", encoding="utf-8")
    settings_repo.remember_players_csv_path(str(fake_csv))
    page = ClubAdvisorPage()
    controller = ClubAdvisorController(
        page, squad_service, settings_repo, club_advisor_service=ClubAdvisorAppService()
    )
    return page, controller, players


def test_page_shows_empty_state_with_no_roster(tmp_path):
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    page = ClubAdvisorPage()
    controller = ClubAdvisorController(page, SquadService(), settings_repo)
    assert page.empty_state_label.isVisible() or not page._sections_container.isVisible()


def test_generate_report_populates_all_sections(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._generate_report()

    assert page.status_label.text()
    assert page.priorities_label.text()
    assert page.training_label.text()
    assert page.squad_label.text()
    assert page.depth_label.text()
    assert page.limitations_label.text()


def test_no_overall_score_shown_in_any_section(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._generate_report()

    combined = "\n".join(
        [
            page.status_label.text(),
            page.priorities_label.text(),
            page.strengths_label.text(),
            page.risks_label.text(),
        ]
    )
    assert "Overall" not in combined
    assert "score" not in combined.lower()


def test_project_status_is_translated(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._generate_report()
    assert "_" not in page.status_label.text().split("\n")[0]


def test_limitations_always_shown(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._generate_report()
    assert "financ" in page.limitations_label.text().lower() or "Financ" in page.limitations_label.text()


def test_empty_players_shows_empty_state(tmp_path):
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    squad_service = SquadService(importer=FakeImporter([]))
    fake_csv = tmp_path / "fake.csv"
    fake_csv.write_text("name\n", encoding="utf-8")
    settings_repo.remember_players_csv_path(str(fake_csv))
    page = ClubAdvisorPage()
    controller = ClubAdvisorController(page, squad_service, settings_repo)
    controller._generate_report()
    assert not page._sections_container.isVisible()


def test_offscreen_pyside6_stability_smoke():
    page = ClubAdvisorPage()
    page.show_empty_state()
    for _ in range(3):
        page.show_report(
            {
                "status": "x", "priorities": "x", "strengths": "x", "risks": "x",
                "training": "x", "squad": "x", "depth": "x", "warnings": "x", "limitations": "x",
            }
        )
    assert page.status_label.text() == "x"
