from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.widgets.formation_board.formation_board_styles import (
    formation_board_stylesheet,
)
from ht_coach_app.widgets.formation_board.pitch_widget import PitchWidget


class FormationBoard(QWidget):
    formation_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mapper = FormationBoardMapper()
        self._boards = {}
        self._details_by_name = {}
        self._current_name = ""
        self.setStyleSheet(formation_board_stylesheet())
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QFrame()
        header.setObjectName("formationBoardPanel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(10)

        title = QLabel("Formation Board")
        title.setObjectName("formationBoardTitle")
        header_layout.addWidget(title)

        self.formation_combo = QComboBox()
        self.formation_combo.currentTextChanged.connect(
            self._on_formation_changed
        )
        header_layout.addWidget(self.formation_combo)

        self.meta_label = QLabel("")
        self.meta_label.setObjectName("formationBoardMeta")
        header_layout.addWidget(self.meta_label)
        header_layout.addStretch(1)
        layout.addWidget(header)

        splitter = QSplitter()

        self.pitch = PitchWidget()
        self.pitch.player_selected.connect(
            self.select_player
        )
        self.pitch.empty_area_clicked.connect(
            self.clear_selection
        )
        splitter.addWidget(self.pitch)

        self.inspector = QFrame()
        self.inspector.setObjectName("playerInspectorPanel")
        self.inspector_layout = QVBoxLayout(self.inspector)
        self.inspector_layout.setContentsMargins(14, 14, 14, 14)
        self.inspector_layout.setSpacing(8)
        splitter.addWidget(self.inspector)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

    def set_boards(
        self,
        boards,
        selected_formation_name="",
        player_details_by_name=None,
    ):
        self._details_by_name = player_details_by_name or {}
        self._boards = {
            board.formation_name: board
            for board in boards
        }
        self.formation_combo.blockSignals(True)
        self.formation_combo.clear()

        for board in boards:
            label = board.formation_name
            if board.recommendation_label:
                label = f"{label} ({board.recommendation_label})"
            self.formation_combo.addItem(label, board.formation_name)

        target = selected_formation_name or (
            boards[0].formation_name
            if boards
            else ""
        )
        index = self.formation_combo.findData(target)
        self.formation_combo.setCurrentIndex(index if index >= 0 else 0)
        self.formation_combo.blockSignals(False)
        self._current_name = self.formation_combo.currentData() or ""
        self._render_current_board()

    def current_board(self):
        return self._boards.get(self._current_name)

    def select_player(self, player_id):
        board = self.current_board()

        if board is None:
            return

        updated = self._mapper.select_player(
            board,
            player_id
        )
        self._boards[updated.formation_name] = updated
        self._render_current_board()

    def clear_selection(self):
        board = self.current_board()

        if board is None:
            return

        updated = self._mapper.clear_selection(board)
        self._boards[updated.formation_name] = updated
        self._render_current_board()

    def _on_formation_changed(self):
        self._current_name = self.formation_combo.currentData() or ""
        self.formation_changed.emit(self._current_name)
        self._render_current_board()

    def _render_current_board(self):
        board = self.current_board()
        self.pitch.set_board(board)

        if board is None:
            self.meta_label.setText("")
            self._render_inspector_message(
                "Run a match analysis to view the recommended formation."
            )
            return

        self.meta_label.setText(
            f"{board.tactic_name} | Tactic level {board.tactic_level:.2f}"
        )
        inspector = self._mapper.inspector_for_player(
            board,
            self._details_by_name,
        )
        self._render_inspector(inspector)

    def _render_inspector(self, inspector):
        self._clear_inspector()

        if not inspector.player_name:
            self._render_inspector_message(
                inspector.unavailable_message
            )
            return

        title = QLabel(inspector.player_name)
        title.setObjectName("formationBoardTitle")
        self.inspector_layout.addWidget(title)

        rows = [
            ("Position", inspector.assigned_position),
            ("Side", inspector.assigned_side),
            ("Order", inspector.individual_order),
            ("Order side", inspector.order_side or "-"),
            ("Best position", inspector.best_position or "-"),
            ("Position score", self._format_optional_float(inspector.position_score)),
            ("Form", self._format_optional_int(inspector.form)),
            ("Stamina", self._format_optional_int(inspector.stamina)),
            ("Experience", self._format_optional_int(inspector.experience)),
            ("TSI", self._format_optional_int(inspector.tsi)),
            ("Specialty", inspector.specialty or "-"),
        ]

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(5)

        for row, (label, value) in enumerate(rows):
            label_widget = QLabel(label)
            label_widget.setObjectName("playerInspectorMeta")
            value_widget = QLabel(str(value))
            grid.addWidget(label_widget, row, 0)
            grid.addWidget(value_widget, row, 1)

        grid_host = QWidget()
        grid_host.setLayout(grid)
        self.inspector_layout.addWidget(grid_host)

        if inspector.relevant_skills:
            self.inspector_layout.addWidget(
                self._section_label("Core skills")
            )
            for label, value in inspector.relevant_skills:
                self.inspector_layout.addWidget(
                    QLabel(f"{label}: {value}")
                )

        if inspector.rankings_by_position:
            self.inspector_layout.addWidget(
                self._section_label("Position rankings")
            )
            for label, score, rank in inspector.rankings_by_position:
                self.inspector_layout.addWidget(
                    QLabel(f"{rank}. {label}: {score:.2f}")
                )

        if inspector.unavailable_message:
            message = QLabel(inspector.unavailable_message)
            message.setWordWrap(True)
            message.setObjectName("playerInspectorMeta")
            self.inspector_layout.addWidget(message)

        self.inspector_layout.addStretch(1)

    def _render_inspector_message(self, message):
        self._clear_inspector()
        label = QLabel(message)
        label.setWordWrap(True)
        label.setObjectName("playerInspectorMeta")
        self.inspector_layout.addWidget(label)
        self.inspector_layout.addStretch(1)

    def _clear_inspector(self):
        while self.inspector_layout.count():
            item = self.inspector_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.setParent(None)

    def _section_label(self, text):
        label = QLabel(text)
        label.setObjectName("formationBoardTitle")
        return label

    @staticmethod
    def _format_optional_float(value):
        if value is None:
            return "-"

        return f"{value:.2f}"

    @staticmethod
    def _format_optional_int(value):
        if value is None:
            return "-"

        return str(value)
