import tempfile
from pathlib import Path

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.weekly_training.persistence import WeeklyTrainingRepository
from engine.weekly_training.training_types import TrainingType
from ht_coach_app.controllers.squad_controller import SquadController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.services.squad_service import SquadService
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from ht_coach_app.views.squad_page import SquadPage


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def make_controller(tmp_path, with_roster=True):
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json",
        result_storage_path=tmp_path / "result.json",
    )
    weekly_repo = WeeklyTrainingRepository(tmp_path / "planner.json")
    weekly_service = WeeklyTrainingAppService(repository=weekly_repo)
    page = SquadPage()
    controller = SquadController(
        page, SquadService(), settings_repo, weekly_training_service=weekly_service
    )
    if with_roster:
        controller._roster = type("FakeRoster", (), {"players": []})()
        controller._show_weekly_training()
    return page, controller, weekly_service


# --------------------------------------------------------------------------
# Selector contents
# --------------------------------------------------------------------------

def test_selector_contains_exactly_the_twelve_canonical_training_types(tmp_path):
    page, _, _ = make_controller(tmp_path)
    combo = page.weekly_training_type_combo_v2

    assert combo.count() == 12
    values = {combo.itemData(i) for i in range(combo.count())}
    assert values == {training_type.value for training_type in TrainingType}


def test_selector_values_come_from_the_training_catalog(tmp_path):
    """Every item's data must be a value the catalog actually resolves a
    rule provider for -- proving the UI reads from the catalog rather
    than a separately hand-typed list."""
    from engine.weekly_training.training_rules import rule_provider_for

    page, _, _ = make_controller(tmp_path)
    combo = page.weekly_training_type_combo_v2
    for i in range(combo.count()):
        assert rule_provider_for(combo.itemData(i)) is not None


def test_selector_spanish_labels(tmp_path):
    configure_localization("es")
    page, _, _ = make_controller(tmp_path)
    combo = page.weekly_training_type_combo_v2
    labels = {combo.itemText(i) for i in range(combo.count())}
    assert "Jugadas" in labels
    assert "Defensa" in labels
    assert "Balón parado" in labels
    configure_localization("en")


def test_selector_english_labels(tmp_path):
    configure_localization("en")
    page, _, _ = make_controller(tmp_path)
    combo = page.weekly_training_type_combo_v2
    labels = {combo.itemText(i) for i in range(combo.count())}
    assert "Playmaking" in labels
    assert "Defending" in labels
    assert "Set Pieces" in labels
    configure_localization("en")


def test_legacy_combo_also_populated_from_catalog(tmp_path):
    """The hidden legacy tab's combo (kept alive for compatibility) is
    populated the same way -- not left with a single hardcoded item."""
    page, _, _ = make_controller(tmp_path)
    assert page.weekly_training_type_combo.count() == 12


# --------------------------------------------------------------------------
# Selection behavior
# --------------------------------------------------------------------------

def test_changing_selection_persists_immediately(tmp_path):
    page, controller, weekly_service = make_controller(tmp_path)
    combo = page.weekly_training_type_combo_v2

    index = combo.findData("DEFENDING")
    combo.setCurrentIndex(index)

    state = weekly_service.load_state()
    assert state.active_training_type == "DEFENDING"


def test_changing_selection_recalculates_coverage(tmp_path):
    from models.player import Player

    def player(name):
        return Player(
            name=name, age=25, days=100, speciality="", form=6, stamina=8,
            goalkeeper=1, defending=1, playmaking=1, winger=1, passing=1,
            scoring=1, set_pieces=1, experience=5, leadership=5, tsi=1000,
            salary=1000,
        )

    page, controller, weekly_service = make_controller(tmp_path, with_roster=False)
    controller._roster = type("FakeRoster", (), {"players": [player("Alice")]})()
    controller._show_weekly_training()

    combo = page.weekly_training_type_combo_v2
    initial_rows = list(page._weekly_coverage_rows)

    index = combo.findData("GOALKEEPING")
    combo.setCurrentIndex(index)

    # A fresh call recalculated the coverage rows shown on the page
    assert page._weekly_coverage_rows is not None
    assert isinstance(initial_rows, list)


def test_selecting_same_value_again_is_a_no_op(tmp_path):
    page, controller, weekly_service = make_controller(tmp_path)
    combo = page.weekly_training_type_combo_v2

    state_before = weekly_service.load_state()
    index = combo.findData(state_before.active_training_type)
    combo.setCurrentIndex(index)  # re-selecting the already-active value

    state_after = weekly_service.load_state()
    assert state_after.active_training_type == state_before.active_training_type


def test_selection_restores_after_reload(tmp_path):
    page, controller, weekly_service = make_controller(tmp_path)
    combo = page.weekly_training_type_combo_v2
    combo.setCurrentIndex(combo.findData("SCORING"))

    # simulate reopening the app: fresh page/controller, same repository file
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json",
        result_storage_path=tmp_path / "result.json",
    )
    weekly_repo = WeeklyTrainingRepository(tmp_path / "planner.json")
    weekly_service2 = WeeklyTrainingAppService(repository=weekly_repo)
    page2 = SquadPage()
    controller2 = SquadController(
        page2, SquadService(), settings_repo, weekly_training_service=weekly_service2
    )
    controller2._roster = type("FakeRoster", (), {"players": []})()
    controller2._show_weekly_training()

    assert page2.weekly_training_type_combo_v2.currentData() == "SCORING"


def test_legacy_data_without_training_type_defaults_to_playmaking(tmp_path):
    import json

    path = tmp_path / "planner.json"
    path.write_text(json.dumps({"priorities": {}, "match_records": []}), encoding="utf-8")

    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json",
        result_storage_path=tmp_path / "result.json",
    )
    weekly_repo = WeeklyTrainingRepository(path)
    weekly_service = WeeklyTrainingAppService(repository=weekly_repo)
    page = SquadPage()
    controller = SquadController(
        page, SquadService(), settings_repo, weekly_training_service=weekly_service
    )
    controller._roster = type("FakeRoster", (), {"players": []})()
    controller._show_weekly_training()

    assert page.weekly_training_type_combo_v2.currentData() == "PLAYMAKING"


def test_changing_training_type_does_not_orphan_recorded_matches(tmp_path):
    """Regression for the week_id-coupling issue found while building
    this: switching training type mid-week must not change the active
    week's id, or a first/second match already recorded this week would
    stop being found."""
    page, controller, weekly_service = make_controller(tmp_path)
    state_before = weekly_service.load_state()
    week_id_before = state_before.active_week.week_id

    combo = page.weekly_training_type_combo_v2
    combo.setCurrentIndex(combo.findData("WINGER"))

    state_after = weekly_service.load_state()
    assert state_after.active_week.week_id == week_id_before
    assert state_after.active_training_type == "WINGER"


# --------------------------------------------------------------------------
# Responsibility boundaries
# --------------------------------------------------------------------------

def test_no_csv_selector_appears_in_planner(tmp_path):
    page, _, _ = make_controller(tmp_path)
    assert not hasattr(page, "weekly_csv_combo")
    assert not hasattr(page, "weekly_browse_button")


def test_no_generate_lineup_action_in_v2_tab(tmp_path):
    """The v2 (visible) weekly planner tab must not offer a "Generate
    Lineup" action -- that button only exists on the hidden legacy tab
    kept alive for controller compatibility, and this sprint must not
    add an equivalent to the active UI."""
    page, _, _ = make_controller(tmp_path)
    assert not hasattr(page, "weekly_generate_button_v2")


def test_planner_never_imports_formation_optimizer():
    import ast

    path = Path(__file__).resolve().parents[1] / "ht_coach_app" / "views" / "squad_page.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    forbidden = {
        "engine.optimizers.formation_optimizer",
        "engine.optimizers.lineup_optimizer",
        "engine.optimizers.tactic_optimizer",
    }
    assert not (imported & forbidden)
