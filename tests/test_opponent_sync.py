import tempfile
import unittest
from pathlib import Path

try:
    from PySide6.QtCore import QObject, Signal
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise

    QObject = object
    Signal = None


HAS_PYSIDE = Signal is not None


if HAS_PYSIDE:
    from ht_coach_app.controllers.match_controller import MatchController
    from ht_coach_app.controllers.opponent_controller import OpponentController
    from ht_coach_app.persistence.match_workspace_repository import (
        MatchWorkspaceRepository,
    )
    from ht_coach_app.persistence.opponent_repository import OpponentRepository
    from ht_coach_app.services.match_workspace_service import MatchWorkspaceService
    from ht_coach_app.services.opponent_service import (
        DEFAULT_RATINGS,
        OpponentService,
    )
    from ht_coach_app.state.app_events import AppEvents

else:
    DEFAULT_RATINGS = {}


class FakeOpponentsView(QObject):
    if HAS_PYSIDE:
        new_requested = Signal()
        save_requested = Signal()
        duplicate_requested = Signal()
        delete_requested = Signal()
        selection_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.opponents = []
        self.selected_name = None
        self.editor_name = ""
        self.editor_ratings = dict(DEFAULT_RATINGS)

    def set_opponents(self, opponents, selected_name=None):
        self.opponents = opponents
        self.selected_name = selected_name

    def clear_editor(self, ratings):
        self.selected_name = None
        self.editor_name = ""
        self.editor_ratings = dict(ratings)

    def current_opponent_name(self):
        return self.selected_name

    def editor_data(self):
        return self.editor_name, dict(self.editor_ratings)

    def show_status(self, _message):
        pass

    def show_error(self, _message):
        pass

    def confirm_delete(self, _name):
        return True


class FakeMatchView(QObject):
    if HAS_PYSIDE:
        browse_players_requested = Signal()
        load_players_requested = Signal()
        analyze_requested = Signal()
        workspace_changed = Signal()

    def __init__(self):
        super().__init__()
        self.opponent_names = []
        self.selected_name = ""
        self.supported_formations = []
        self.settings = None

    def set_opponents(self, opponent_names, selected_name=None):
        self.opponent_names = list(opponent_names)

        if selected_name is None:
            selected_name = self.selected_name

        self.selected_name = (
            selected_name
            if selected_name in self.opponent_names
            else ""
        )

    def set_supported_formations(self, formation_names):
        self.supported_formations = list(formation_names)

    def apply_settings(self, settings):
        self.settings = settings
        if settings.opponent_name in self.opponent_names:
            self.selected_name = settings.opponent_name

    def selected_opponent_name(self):
        return self.selected_name

    def players_csv_path(self):
        return ""

    def selected_formations(self):
        return ["3-5-2"]


@unittest.skipIf(
    not HAS_PYSIDE,
    "PySide6 is not installed"
)
class OpponentSyncTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.opponent_path = (
            Path(self.temp_dir.name)
            / "opponents.json"
        )
        self.settings_path = (
            Path(self.temp_dir.name)
            / "match_workspace.json"
        )
        self.events = AppEvents()
        self.opponent_service = OpponentService(
            OpponentRepository(self.opponent_path)
        )
        self.match_service = MatchWorkspaceService(
            self.opponent_service,
            importer=lambda _path: [],
            optimizer=lambda *_args: []
        )
        self.opponents_view = FakeOpponentsView()
        self.match_view = FakeMatchView()
        self.opponents_controller = OpponentController(
            self.opponents_view,
            self.opponent_service,
            self.events
        )
        self.match_controller = MatchController(
            self.match_view,
            self.match_service,
            MatchWorkspaceRepository(self.settings_path),
            self.events
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_creating_opponent_refreshes_match_selector(self):
        self.opponents_view.editor_name = "Rival FC"

        self.opponents_controller.save_opponent()

        self.assertIn(
            "Rival FC",
            self.match_view.opponent_names
        )
        self.assertEqual(
            self.opponent_service.get_opponent("Rival FC").name,
            "Rival FC"
        )

    def test_renaming_selected_opponent_refreshes_and_preserves_selection(self):
        self.opponent_service.create_opponent(
            "Rival FC",
            DEFAULT_RATINGS
        )
        self.match_controller.refresh()
        self.match_view.selected_name = "Rival FC"
        self.opponents_view.selected_name = "Rival FC"
        self.opponents_view.editor_name = "Renamed FC"

        self.opponents_controller.save_opponent()

        self.assertNotIn(
            "Rival FC",
            self.match_view.opponent_names
        )
        self.assertIn(
            "Renamed FC",
            self.match_view.opponent_names
        )
        self.assertEqual(
            self.match_view.selected_opponent_name(),
            "Renamed FC"
        )

    def test_duplicate_adds_opponent_to_match_selector(self):
        self.opponent_service.create_opponent(
            "Rival FC",
            DEFAULT_RATINGS
        )
        self.opponents_view.selected_name = "Rival FC"

        self.opponents_controller.duplicate_opponent()

        self.assertIn(
            "Rival FC Copy",
            self.match_view.opponent_names
        )

    def test_deleting_selected_opponent_clears_match_selection(self):
        self.opponent_service.create_opponent(
            "Rival FC",
            DEFAULT_RATINGS
        )
        self.match_controller.refresh()
        self.match_view.selected_name = "Rival FC"
        self.opponents_view.selected_name = "Rival FC"

        self.opponents_controller.delete_opponent()

        self.assertNotIn(
            "Rival FC",
            self.match_view.opponent_names
        )
        self.assertEqual(
            self.match_view.selected_opponent_name(),
            ""
        )
        self.assertIsNone(
            self.opponent_service.get_opponent("Rival FC")
        )

    def test_match_workspace_persistence_tracks_synced_selection(self):
        self.opponent_service.create_opponent(
            "Rival FC",
            DEFAULT_RATINGS
        )
        self.match_controller.refresh()
        self.match_view.selected_name = "Rival FC"
        self.opponents_view.selected_name = "Rival FC"
        self.opponents_view.editor_name = "Renamed FC"

        self.opponents_controller.save_opponent()

        settings = MatchWorkspaceRepository(
            self.settings_path
        ).load()

        self.assertEqual(
            settings.opponent_name,
            "Renamed FC"
        )


if __name__ == "__main__":
    unittest.main()
