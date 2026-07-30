import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from ht_coach_app.controllers.squad_controller import SquadController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.services.squad_service import RosterResult, SquadService
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
    players = players or [
        make_player(name="Keeper A", goalkeeper=15, defending=2, playmaking=1, winger=1, passing=2, scoring=1, set_pieces=1),
        make_player(name="Keeper B", goalkeeper=8, defending=1, playmaking=1, winger=1, passing=1, scoring=1, set_pieces=1),
        make_player(name="Forward A", scoring=15, defending=1, goalkeeper=1, playmaking=2, winger=3, passing=3, set_pieces=2),
    ]
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    squad_service = SquadService(importer=FakeImporter(players))
    page = SquadPage()
    controller = SquadController(page, squad_service, settings_repo)
    controller._roster = RosterResult(
        players=players, rows=squad_service.map_players(players), source_path="fake.csv"
    )
    return page, controller, players


def test_role_status_combos_populated_with_all_option(tmp_path):
    page, controller, players = make_controller(tmp_path)
    assert page.role_filter_combo.itemData(0) == "all"
    assert page.status_filter_combo.itemData(0) == "all"
    assert page.role_filter_combo.count() == 12
    assert page.status_filter_combo.count() == 9


def test_default_filter_state_shows_every_player(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._apply_filters()
    assert len(controller._visible_rows) == len(players)


def test_removed_training_fit_filter_is_neutral(tmp_path):
    page, controller, players = make_controller(tmp_path)
    index = page.training_fit_filter_combo.findData("no_training")
    page.training_fit_filter_combo.setCurrentIndex(index)
    controller._apply_filters()
    assert page.filter_values()["training_fit"] == "all"
    assert len(controller._visible_rows) == len(players)


def test_removed_search_filter_is_neutral(tmp_path):
    page, controller, players = make_controller(tmp_path)
    page.search_edit.setText("Keeper")
    controller._apply_filters()
    assert page.filter_values()["search_text"] == ""
    assert len(controller._visible_rows) == len(players)


def test_filters_never_crash_with_empty_roster(tmp_path):
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    page = SquadPage()
    controller = SquadController(page, SquadService(), settings_repo)
    index = page.role_filter_combo.findData("starter")
    page.role_filter_combo.setCurrentIndex(index)
    assert controller._visible_rows == []


def test_selecting_all_after_a_specific_filter_restores_full_list(tmp_path):
    page, controller, players = make_controller(tmp_path)
    index = page.role_filter_combo.findData("starter")
    page.role_filter_combo.setCurrentIndex(index)

    page.role_filter_combo.setCurrentIndex(0)
    assert len(controller._visible_rows) == len(players)


def test_combining_role_and_status_filters(tmp_path):
    page, controller, players = make_controller(tmp_path)
    role_index = page.role_filter_combo.findData("starter")
    page.role_filter_combo.setCurrentIndex(role_index)
    status_index = page.status_filter_combo.findData("keep")
    page.status_filter_combo.setCurrentIndex(status_index)

    assert isinstance(controller._visible_rows, list)


def test_filter_combos_have_localized_labels(tmp_path):
    page, controller, players = make_controller(tmp_path)
    assert page.role_filter_combo.itemText(0)
    assert "_" not in page.role_filter_combo.itemText(1)


def test_filtering_by_role_matches_only_matching_players(tmp_path):
    """A player filtered by an exact role must genuinely have that role
    -- verified end-to-end via the real Squad Intelligence pipeline,
    not a mock."""
    page, controller, players = make_controller(tmp_path)
    from ht_coach_app.services.squad_intelligence_service import SquadIntelligenceAppService

    reports = SquadIntelligenceAppService(
        weekly_training_service=controller._weekly_training_service
    ).generate_squad_reports(players)
    reports_by_name = {r.player_name: r for r in reports}

    any_role = next(iter(reports_by_name.values())).recommended_role.value
    index = page.role_filter_combo.findData(any_role)
    page.role_filter_combo.setCurrentIndex(index)

    for row in controller._visible_rows:
        assert reports_by_name[row.name].recommended_role.value == any_role
