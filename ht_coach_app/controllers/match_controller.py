from PySide6.QtCore import QObject, QThread

from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceSettings,
)
from ht_coach_app.services.match_workspace_service import (
    MatchWorkspaceValidationError,
)
from ht_coach_app.workers.match_analysis_worker import (
    MatchAnalysisWorker,
)


class MatchController(QObject):
    def __init__(
        self,
        view,
        service,
        settings_repository,
        app_events=None,
        parent=None
    ):
        super().__init__(parent)
        self._view = view
        self._service = service
        self._settings_repository = settings_repository
        self._app_events = app_events
        self._thread = None
        self._worker = None

        self._connect_view()
        self._connect_app_events()
        self.refresh()

    def _connect_view(self):
        self._view.browse_players_requested.connect(
            self._browse_players
        )
        self._view.load_players_requested.connect(
            self._load_players
        )
        self._view.analyze_requested.connect(
            self._analyze
        )
        self._view.workspace_changed.connect(
            self._save_current_settings
        )

    def _connect_app_events(self):
        if self._app_events is not None:
            self._app_events.opponents_changed.connect(
                self._sync_opponents
            )

    def refresh(self):
        self._refresh_opponents()
        self._view.set_supported_formations(
            self._service.supported_formations()
        )
        self._view.apply_settings(
            self._settings_repository.load()
        )

    def _refresh_opponents(self, selected_name=None):
        opponents = self._service.list_opponents()
        self._view.set_opponents(
            [opponent.name for opponent in opponents],
            selected_name=selected_name
        )

    def _sync_opponents(
        self,
        action,
        previous_name,
        current_name
    ):
        selected_name = self._view.selected_opponent_name()

        if action == "updated" and selected_name == previous_name:
            selected_name = current_name
        elif action == "deleted" and selected_name == previous_name:
            selected_name = ""

        self._refresh_opponents(
            selected_name=selected_name
        )
        self._save_current_settings()

    def _browse_players(self):
        path = self._view.choose_players_file()

        if path:
            self._view.set_players_csv_path(path)
            self._save_current_settings()

    def _load_players(self):
        try:
            count = self._service.load_players_count(
                self._view.players_csv_path()
            )
        except Exception as exc:
            self._view.show_error(
                str(exc)
            )
            return

        self._view.set_players_loaded_count(
            count
        )
        self._view.show_status(
            f"Loaded {count} players."
        )
        self._save_current_settings()

    def _analyze(self):
        try:
            self._service.validate_inputs(
                self._view.players_csv_path(),
                self._view.selected_opponent_name(),
                self._view.selected_formations()
            )
        except MatchWorkspaceValidationError as exc:
            self._view.show_error(
                str(exc)
            )
            return

        self._save_current_settings()
        self._view.clear_results()
        self._view.set_processing(
            True
        )
        self._view.show_status(
            "Starting match analysis..."
        )

        self._thread = QThread(self)
        self._worker = MatchAnalysisWorker(
            self._service,
            self._view.players_csv_path(),
            self._view.selected_opponent_name(),
            self._view.selected_formations()
        )
        self._worker.moveToThread(
            self._thread
        )

        self._thread.started.connect(
            self._worker.run
        )
        self._worker.progress_changed.connect(
            self._view.show_status
        )
        self._worker.finished.connect(
            self._analysis_finished
        )
        self._worker.failed.connect(
            self._analysis_failed
        )
        self._worker.finished.connect(
            self._thread.quit
        )
        self._worker.failed.connect(
            self._thread.quit
        )
        self._thread.finished.connect(
            self._worker.deleteLater
        )
        self._thread.finished.connect(
            self._thread.deleteLater
        )
        self._thread.finished.connect(
            self._clear_worker_refs
        )

        self._thread.start()

    def _analysis_finished(self, result):
        self._view.set_processing(
            False
        )
        self._view.show_results(
            result
        )
        self._view.show_status(
            "Match analysis complete."
        )

    def _analysis_failed(self, message):
        self._view.set_processing(
            False
        )
        self._view.show_error(
            message
        )

    def _clear_worker_refs(self):
        self._thread = None
        self._worker = None

    def _save_current_settings(self):
        self._settings_repository.save(
            MatchWorkspaceSettings(
                players_csv_path=self._view.players_csv_path(),
                opponent_name=self._view.selected_opponent_name(),
                selected_formations=self._view.selected_formations()
            )
        )
