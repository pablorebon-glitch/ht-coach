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
        match_type=None,
        required_player_ids=None,
        training_rules=None,
        required_slot_classes=None,
        match_1_player_ids=None,
        parent=None
    ):
        super().__init__(parent)
        self._service = service
        self._players_csv_path = players_csv_path
        self._opponent_name = opponent_name
        self._formation_names = formation_names
        self._workspace_state = workspace_state
        self._availability_mode = availability_mode
        self._match_type = match_type
        self._required_player_ids = required_player_ids
        self._training_rules = training_rules
        self._required_slot_classes = required_slot_classes
        self._match_1_player_ids = match_1_player_ids

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
                workspace_kwargs = {
                    "availability_mode": self._availability_mode,
                }
                if self._match_type is not None:
                    workspace_kwargs["match_type"] = self._match_type
                result = self._service.analyze_workspace(
                    self._players_csv_path,
                    self._opponent_name,
                    self._workspace_state,
                    **workspace_kwargs,
                )
                self.finished.emit(result)
                return

            self.progress_changed.emit(
                t("match.status_recalculating_recommendation")
            )
            analyze_kwargs = {
                "availability_mode": self._availability_mode,
            }
            if self._match_type is not None:
                analyze_kwargs["match_type"] = self._match_type
            analyze_kwargs["required_player_ids"] = self._required_player_ids
            analyze_kwargs["training_rules"] = self._training_rules
            analyze_kwargs["required_slot_classes"] = self._required_slot_classes
            analyze_kwargs["match_1_player_ids"] = self._match_1_player_ids
            result = self._service.analyze(
                self._players_csv_path,
                self._opponent_name,
                self._formation_names,
                **analyze_kwargs,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
