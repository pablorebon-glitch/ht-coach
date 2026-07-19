from PySide6.QtCore import QObject, Signal, Slot

from ht_coach_app.core.localization import t


class MatchAnalysisWorker(QObject):
    progress_changed = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        service,
        players_csv_path,
        opponent_name,
        formation_names,
        workspace_state=None,
        availability_mode="current_available",
        parent=None
    ):
        super().__init__(parent)
        self._service = service
        self._players_csv_path = players_csv_path
        self._opponent_name = opponent_name
        self._formation_names = formation_names
        self._workspace_state = workspace_state
        self._availability_mode = availability_mode

    @Slot()
    def run(self):
        try:
            self.progress_changed.emit(
                t("match.status_evaluating_eligible_players")
            )
            if self._workspace_state is not None:
                self.progress_changed.emit(
                    t("match.status_updating_available_lineup")
                )
                result = self._service.analyze_workspace(
                    self._players_csv_path,
                    self._opponent_name,
                    self._workspace_state,
                    availability_mode=self._availability_mode,
                )
                self.finished.emit(result)
                return

            self.progress_changed.emit(
                t("match.status_recalculating_recommendation")
            )
            result = self._service.analyze(
                self._players_csv_path,
                self._opponent_name,
                self._formation_names,
                availability_mode=self._availability_mode,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
