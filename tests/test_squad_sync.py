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
    from ht_coach_app.controllers.squad_controller import SquadController
    from ht_coach_app.persistence.match_workspace_repository import (
        MatchWorkspaceRepository,
    )
    from ht_coach_app.services.match_workspace_service import (
        MatchWorkspaceService,
    )
    from ht_coach_app.services.squad_service import RosterResult
    from ht_coach_app.state.app_events import AppEvents


class FakeSquadView(QObject):
    if HAS_PYSIDE:
        browse_requested = Signal()
        load_requested = Signal()
        reload_requested = Signal()
        filters_changed = Signal()
        export_requested = Signal()
        player_selected = Signal(str)

    def __init__(self, csv_path):
        super().__init__()
        self._csv_path = str(csv_path)
        self.loaded_count = 0
        self.status = ""
        self.positions = []
        self.specialties = []
        self.rows = []

    def set_supported_positions(self, positions):
        self.positions = list(positions)

    def set_csv_path(self, path):
        self._csv_path = str(path)

    def csv_path(self):
        return self._csv_path

    def choose_players_file(self):
        return self._csv_path

    def filter_values(self):
        return {
            "search_text": "",
            "minimum_form": 0,
            "minimum_stamina": 0,
            "speciality": "",
            "selected_position": "",
        }

    def show_loading(self):
        self.status = "loading"

    def show_error(self, message):
        self.status = message

    def show_status(self, message):
        self.status = message

    def set_specialties(self, specialties):
        self.specialties = list(specialties)

    def set_players(self, rows):
        self.rows = list(rows)

    def set_loaded_count(self, count):
        self.loaded_count = count

    def clear_detail(self):
        pass

    def show_player_detail(self, detail):
        pass


class FakeMatchView(QObject):
    if HAS_PYSIDE:
        browse_players_requested = Signal()
        load_players_requested = Signal()
        analyze_requested = Signal()
        copy_summary_requested = Signal()
        copy_lineup_requested = Signal()
        workspace_changed = Signal()

    def __init__(self):
        super().__init__()
        self.path = ""
        self.loaded_count = 0
        self.status = ""
        self.opponents = []

    def set_opponents(self, opponent_names, selected_name=None):
        self.opponents = list(opponent_names)

    def set_supported_formations(
        self,
        formation_names,
        favorite_formations=None
    ):
        pass

    def apply_settings(self, settings):
        self.path = settings.players_csv_path

    def show_results(self, result, restored=False):
        pass

    def selected_opponent_name(self):
        return ""

    def players_csv_path(self):
        return self.path

    def set_players_csv_path(self, path):
        self.path = str(path)

    def selected_formations(self):
        return ["3-5-2"]

    def set_players_loaded_count(self, count):
        self.loaded_count = count

    def show_status(self, message):
        self.status = message

    def show_error(self, message):
        self.status = message


class FakeSquadService:
    def __init__(self, roster):
        self.roster = roster

    def supported_positions(self):
        return ["GOALKEEPER"]

    def load_roster(self, csv_path):
        return self.roster

    def map_players(self, players, selected_position=""):
        return self.roster.rows

    def filter_rows(self, rows, **_kwargs):
        return rows

    def player_detail(self, players, player_name):
        return None

    def export_rows_to_csv(self, rows, output_path):
        return str(output_path)


class FakeMatchService:
    def list_opponents(self):
        return []

    def supported_formations(self):
        return ["3-5-2"]

    def default_formations(self):
        return ["3-5-2"]


@unittest.skipIf(
    not HAS_PYSIDE,
    "PySide6 is not installed"
)
class SquadSyncTest(unittest.TestCase):
    def test_loading_squad_updates_match_roster_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "players.csv"
            csv_path.write_text("placeholder", encoding="utf-8")
            settings_path = Path(temp_dir) / "match_workspace.json"
            repository = MatchWorkspaceRepository(settings_path)
            events = AppEvents()
            roster = RosterResult(
                players=[object(), object()],
                rows=[],
                source_path=str(csv_path)
            )
            squad_view = FakeSquadView(csv_path)
            match_view = FakeMatchView()

            squad_controller = SquadController(
                squad_view,
                FakeSquadService(roster),
                repository,
                events
            )
            match_controller = MatchController(
                match_view,
                MatchWorkspaceService(
                    opponent_service=FakeMatchService(),
                    importer=lambda _path: [],
                    optimizer=lambda *_args: []
                ),
                repository,
                events
            )
            self.assertIsNotNone(squad_controller)
            self.assertIsNotNone(match_controller)

            squad_view.load_requested.emit()

            self.assertEqual(match_view.players_csv_path(), str(csv_path))
            self.assertEqual(match_view.loaded_count, 2)
            self.assertEqual(
                repository.load().players_csv_path,
                str(csv_path)
            )


if __name__ == "__main__":
    unittest.main()
