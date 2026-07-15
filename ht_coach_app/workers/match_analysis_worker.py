from PySide6.QtCore import QObject, Signal, Slot


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
        parent=None
    ):
        super().__init__(parent)
        self._service = service
        self._players_csv_path = players_csv_path
        self._opponent_name = opponent_name
        self._formation_names = formation_names

    @Slot()
    def run(self):
        try:
            self.progress_changed.emit(
                "Loading players..."
            )
            self.progress_changed.emit(
                "Running formation, lineup, order and tactic optimization..."
            )
            result = self._service.analyze(
                self._players_csv_path,
                self._opponent_name,
                self._formation_names
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
