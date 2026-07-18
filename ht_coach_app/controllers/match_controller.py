from PySide6.QtCore import QObject, QThread, QTimer

from dataclasses import replace

from ht_coach_app.change_analysis.service import ChangeAnalysisService
from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceSettings,
)
from ht_coach_app.services.match_workspace_service import (
    MatchWorkspaceValidationError,
    format_decision_lab,
    format_match_summary,
    format_recommended_lineup,
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
        self._change_analysis_service = ChangeAnalysisService()
        self._thread = None
        self._worker = None
        self._roster_players = []
        self._pending_workspace_state = None
        self._queued_workspace_state = None
        self._latest_workspace_revision = None
        self._workspace_recalc_timer = QTimer(self)
        self._workspace_recalc_timer.setSingleShot(True)
        self._workspace_recalc_timer.setInterval(300)
        self._workspace_recalc_timer.timeout.connect(
            self._start_queued_workspace_recalculation
        )

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
        self._view.copy_summary_requested.connect(
            self._copy_summary
        )
        self._view.copy_decision_lab_requested.connect(
            self._copy_decision_lab
        )
        self._view.copy_lineup_requested.connect(
            self._copy_lineup
        )
        if hasattr(self._view, "workspace_recalculate_requested"):
            self._view.workspace_recalculate_requested.connect(
                self._recalculate_workspace
            )
        self._view.workspace_changed.connect(
            self._save_current_settings
        )

    def _connect_app_events(self):
        if self._app_events is not None:
            self._app_events.opponents_changed.connect(
                self._sync_opponents
            )
            self._app_events.roster_changed.connect(
                self._sync_roster
            )

    def refresh(self):
        self._refresh_opponents()
        self._view.set_supported_formations(
            self._service.supported_formations(),
            favorite_formations=self._service.default_formations()
        )
        self._view.apply_settings(
            self._settings_repository.load()
        )
        self._load_current_roster_for_inspector(show_errors=False)
        last_result = self._settings_repository.load_last_result()

        if last_result is not None:
            self._view.show_results(
                last_result,
                restored=True
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

    def _sync_roster(self, players_csv_path, player_count):
        self._view.set_players_csv_path(
            players_csv_path
        )
        self._view.set_players_loaded_count(
            player_count
        )
        self._load_current_roster_for_inspector(show_errors=False)
        self._view.show_status(
            f"Roster updated from Squad: {player_count} players."
        )
        self._save_current_settings()

    def _browse_players(self):
        path = self._view.choose_players_file()

        if path:
            self._view.set_players_csv_path(path)
            self._save_current_settings()

    def _load_players(self):
        try:
            players = self._service.load_players(
                self._view.players_csv_path()
            )
        except Exception as exc:
            self._view.show_error(
                str(exc)
            )
            return

        self._roster_players = players
        self._set_view_roster_players(players)
        self._view.set_players_loaded_count(
            len(players)
        )
        self._view.show_status(
            f"Loaded {len(players)} players."
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
        self._pending_workspace_state = None
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

    def _recalculate_workspace(self, workspace_state):
        self._queued_workspace_state = workspace_state
        self._latest_workspace_revision = workspace_state.revision
        if hasattr(self._view, "show_workspace_updating"):
            self._view.show_workspace_updating()
        self._workspace_recalc_timer.start()

    def _start_queued_workspace_recalculation(self):
        workspace_state = self._queued_workspace_state
        if workspace_state is None:
            return
        if self._thread is not None:
            return
        self._queued_workspace_state = None
        try:
            self._service.validate_inputs(
                self._view.players_csv_path(),
                self._view.selected_opponent_name(),
                list(workspace_state.workspace_boards.keys())
            )
        except MatchWorkspaceValidationError as exc:
            self._view.show_error(
                str(exc)
            )
            return

        self._save_current_settings()
        self._pending_workspace_state = workspace_state
        if hasattr(self._view, "set_workspace_processing"):
            self._view.set_workspace_processing(True)
        else:
            self._view.set_processing(True)
        self._view.show_status(
            "Updating Workspace analysis..."
        )

        self._thread = QThread(self)
        self._worker = MatchAnalysisWorker(
            self._service,
            self._view.players_csv_path(),
            self._view.selected_opponent_name(),
            list(workspace_state.workspace_boards.keys()),
            workspace_state=workspace_state,
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
        finished_workspace_state = self._pending_workspace_state
        if (
            finished_workspace_state is not None
            and self._latest_workspace_revision is not None
            and finished_workspace_state.revision != self._latest_workspace_revision
        ):
            self._pending_workspace_state = None
            if hasattr(self._view, "set_workspace_processing"):
                self._view.set_workspace_processing(False)
            else:
                self._view.set_processing(False)
            return

        if finished_workspace_state is not None:
            previous_result = self._settings_repository.load_last_result()
            change_analysis = self._change_analysis_service.analyze(
                previous_result,
                result,
                finished_workspace_state,
            )
            result = replace(
                result,
                change_analysis=change_analysis,
            )

        if finished_workspace_state is not None and hasattr(
            self._view,
            "set_workspace_processing",
        ):
            self._view.set_workspace_processing(False)
        else:
            self._view.set_processing(False)
        self._settings_repository.save_last_result(
            result
        )
        self._load_current_roster_for_inspector(show_errors=False)
        self._view.show_results(
            result,
            workspace_state=self._pending_workspace_state,
        )
        self._pending_workspace_state = None
        self._view.show_status(
            "Match analysis complete."
        )

    def _analysis_failed(self, message):
        if self._pending_workspace_state is not None and hasattr(
            self._view,
            "set_workspace_processing",
        ):
            self._view.set_workspace_processing(False)
        else:
            self._view.set_processing(False)
        failed_state = self._pending_workspace_state
        self._pending_workspace_state = None
        if failed_state is not None:
            if hasattr(self._view, "show_workspace_analysis_failed"):
                self._view.show_workspace_analysis_failed(message)
            return
        self._view.show_error(
            message
        )

    def _copy_summary(self):
        result = self._settings_repository.load_last_result()

        if result is None:
            self._view.show_error(
                "Run an analysis before copying the summary."
            )
            return

        self._view.copy_text_to_clipboard(
            format_match_summary(result)
        )
        self._view.show_status(
            "Match summary copied."
        )

    def _copy_lineup(self):
        result = self._settings_repository.load_last_result()

        if result is None:
            self._view.show_error(
                "Run an analysis before copying the lineup."
            )
            return

        self._view.copy_text_to_clipboard(
            format_recommended_lineup(result)
        )
        self._view.show_status(
            "Recommended lineup copied."
        )

    def _copy_decision_lab(self):
        result = self._settings_repository.load_last_result()

        if result is None:
            self._view.show_error(
                "Run an analysis before copying Decision Lab."
            )
            return

        self._view.copy_text_to_clipboard(
            format_decision_lab(result)
        )
        self._view.show_status(
            "Decision Lab copied."
        )

    def _clear_worker_refs(self):
        self._thread = None
        self._worker = None
        if self._queued_workspace_state is not None:
            self._workspace_recalc_timer.start()

    def _save_current_settings(self):
        self._settings_repository.save(
            MatchWorkspaceSettings(
                players_csv_path=self._view.players_csv_path(),
                opponent_name=self._view.selected_opponent_name(),
                selected_formations=self._view.selected_formations()
            )
        )

    def _load_current_roster_for_inspector(self, show_errors):
        try:
            players = self._service.load_players(
                self._view.players_csv_path()
            )
        except Exception as exc:
            self._roster_players = []
            self._set_view_roster_players([])
            if show_errors:
                self._view.show_error(str(exc))
            return

        self._roster_players = players
        self._set_view_roster_players(players)

    def _set_view_roster_players(self, players):
        if hasattr(self._view, "set_roster_players"):
            self._view.set_roster_players(players)
