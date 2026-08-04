import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.models import SectorRatings
from engine.history.official_ratings.models import OfficialRatingSnapshot, RatedAttribute
from engine.history.provisional_record import (
    consolidate_with_official_pre,
    find_or_create_provisional_record,
)
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    MatchAnalysisResult,
    MatchWorkspaceService,
    TeamRatingsResult,
)
from ht_coach_app.services.official_rating_service import OfficialRatingImportService
from ht_coach_app.services.opponent_service import OpponentService
from ht_coach_app.views.match_page import MatchPage


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def _lineup():
    return [
        LineupPlayerResult(
            number=i, position="INNER_MIDFIELDER", side="CENTER",
            order="Normal", order_side="", player_name=f"P{i}",
        )
        for i in range(1, 12)
    ]


def _result(opponent="CA Chaco", match_type="LEAGUE"):
    formation = FormationAnalysisResult(
        formation_name="2-5-3", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=TeamRatingsResult(), lineup=_lineup(),
    )
    return MatchAnalysisResult(
        player_count=18,
        opponent_name=opponent,
        formations=[formation],
        match_type=match_type,
    )


def make_controller(tmp_path):
    hist_repo = HistoricalMatchRepository(tmp_path / "snapshots.json")
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
    opponent_service = OpponentService(opponent_repo)
    match_service = MatchWorkspaceService(opponent_service)
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    official_service = OfficialRatingImportService(repository=hist_repo)
    page = MatchPage()
    controller = MatchController(
        page, match_service, settings_repo, official_rating_service=official_service,
    )
    page.set_match_type("LEAGUE")
    return page, controller, hist_repo


def test_import_button_is_relocated_beside_the_pitch(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result())
    assert page.official_import_button.parent() is page._pre_side_panel


def test_import_button_never_left_in_the_old_setup_form_position(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result())
    setup_layout = page.analysis_inputs_panel.layout()
    assert setup_layout.indexOf(page.official_import_button) == -1


def test_missing_pre_warning_shown_by_default(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result())
    controller._update_pre_status_and_ratings_panel()
    assert page._pre_status_label.text() == "Falta importar el PRE oficial"
    assert page._pre_status_label.property("semanticStatus") == "danger"


def test_pre_loaded_replaces_warning_with_confirmation(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    consolidate_with_official_pre(hist_repo, record, OfficialRatingSnapshot(), "770918226")

    controller._settings_repository.save_last_result(_result())
    page.set_match_date("2026-08-09")
    page.show_results(_result())
    controller._update_pre_status_and_ratings_panel()

    assert page._pre_status_label.text() == "PRE oficial cargado"
    assert page._pre_status_label.property("semanticStatus") == "success"


def test_compact_ratings_panel_shows_not_loaded_before_pre_exists(tmp_path):
    """Alpha 0.6.7 HF-02, Part 15's own worked example: before PRE,
    the card shows its title plus "No cargadas" -- never a silently
    empty container."""
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result())
    controller._update_pre_status_and_ratings_panel()
    title = page._compact_ratings_container.itemAt(0).widget().text()
    body = page._compact_ratings_container.itemAt(1).widget().text()
    assert title == "Calificaciones"
    assert body == "No cargadas"


def test_compact_ratings_panel_shows_all_required_sectors(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    record = find_or_create_provisional_record(
        hist_repo, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    pre = OfficialRatingSnapshot(
        team_name="Hit em up",
        ratings=SectorRatings(
            left_defense=4.25, central_defense=7.0, right_defense=3.75, midfield=7.25,
            left_attack=7.75, central_attack=9.75, right_attack=8.0,
        ),
        formation=RatedAttribute(label="2-5-3"),
        tactic=RatedAttribute(label="Atacar por el centro", level=13),
        team_attitude="Normal",
    )
    consolidate_with_official_pre(hist_repo, record, pre, "770918226")

    controller._settings_repository.save_last_result(_result())
    page.set_match_date("2026-08-09")
    page.show_results(_result())
    controller._update_pre_status_and_ratings_panel()

    fragments = []
    for i in range(page._compact_ratings_container.count()):
        item = page._compact_ratings_container.itemAt(i)
        widget = item.widget()
        if widget is not None:
            fragments.append(widget.text())
            continue
        nested_layout = item.layout()
        if nested_layout is not None:
            for j in range(nested_layout.count()):
                nested_item = nested_layout.itemAt(j)
                if nested_item is not None and nested_item.widget() is not None:
                    fragments.append(nested_item.widget().text())
    texts = "\n".join(fragments)
    assert "4.25" in texts
    assert "7.25" in texts
    assert "7.75" in texts
    assert "Atacar por el centro" in texts
    assert "13" in texts
    assert "2-5-3" in texts
    assert "Normal" in texts


def test_show_compact_official_ratings_with_none_shows_not_loaded_state(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result())
    page.show_compact_official_ratings({"left_defense": 5.0, "midfield": 6.0})
    assert page._compact_ratings_container.count() > 0
    page.show_compact_official_ratings(None)
    body = page._compact_ratings_container.itemAt(1).widget().text()
    assert body == "No cargadas"


def test_pitch_and_side_panel_never_overlap_in_the_same_container(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result())
    container = page._formation_board_tab_container
    layout = container.layout()
    assert layout.count() == 2
    assert layout.itemAt(0).widget() is page._formation_board_widget
    assert layout.itemAt(1).widget() is page._pre_side_panel


def test_side_panel_persists_across_multiple_show_results_calls(tmp_path):
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result())
    first_panel = page._pre_side_panel
    page.show_results(_result())
    assert page._pre_side_panel is first_panel


def test_compact_ratings_title_is_calificaciones_not_pre_oficial(tmp_path):
    """Alpha 0.6.7 HF-02, Part 15: the card title must be exactly
    "Calificaciones" -- never "PRE oficial"."""
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result())
    page.show_compact_official_ratings({"left_defense": 5.0, "midfield": 6.0})

    title = page._compact_ratings_container.itemAt(0).widget().text()
    assert title == "Calificaciones"
    assert "PRE" not in title


def test_compact_ratings_never_shows_verbose_sector_labels(tmp_path):
    """Part 15: no "Izquierda:"/"Central:"/"Derecha:" text -- position
    alone must communicate the sector."""
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result())
    page.show_compact_official_ratings({
        "left_defense": 4.25, "central_defense": 7.0, "right_defense": 3.75,
        "midfield": 7.25, "left_attack": 7.75, "central_attack": 9.75, "right_attack": 8.0,
    })

    fragments = []
    for i in range(page._compact_ratings_container.count()):
        item = page._compact_ratings_container.itemAt(i)
        widget = item.widget()
        if widget is not None:
            fragments.append(widget.text())
            continue
        nested_layout = item.layout()
        if nested_layout is not None:
            for j in range(nested_layout.count()):
                nested_item = nested_layout.itemAt(j)
                if nested_item is not None and nested_item.widget() is not None:
                    fragments.append(nested_item.widget().text())

    for forbidden in ("Izquierda:", "Central:", "Derecha:", "Left:", "Right:"):
        assert not any(forbidden in text for text in fragments)


def test_compact_ratings_values_positioned_spatially(tmp_path):
    """Defense row (3 columns), midfield (centered), attack row (3
    columns) -- values only, laid out by grid position."""
    page, controller, hist_repo = make_controller(tmp_path)
    page.show_results(_result())
    page.show_compact_official_ratings({
        "left_defense": "4.25", "central_defense": "7.0", "right_defense": "3.75",
        "midfield": "7.25",
        "left_attack": "7.75", "central_attack": "9.75", "right_attack": "8.0",
    })

    grid = page._compact_ratings_container.itemAt(1).layout()
    assert grid.itemAtPosition(0, 0).widget().text() == "4.25"
    assert grid.itemAtPosition(0, 1).widget().text() == "7.0"
    assert grid.itemAtPosition(0, 2).widget().text() == "3.75"
    assert grid.itemAtPosition(1, 0).widget().text() == "7.25"
    assert grid.itemAtPosition(2, 0).widget().text() == "7.75"
    assert grid.itemAtPosition(2, 1).widget().text() == "9.75"
    assert grid.itemAtPosition(2, 2).widget().text() == "8.0"
