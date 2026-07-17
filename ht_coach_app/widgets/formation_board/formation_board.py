from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.player_intelligence.service import (
    PlayerIntelligenceService,
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
        self._intelligence_service = PlayerIntelligenceService()
        self._boards = {}
        self._details_by_name = {}
        self._roster_players = []
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
        roster_players=None,
    ):
        self._details_by_name = player_details_by_name or {}
        self._roster_players = list(roster_players or [])
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
        board = self.current_board()

        if board is not None and board.selected_player_id:
            self._boards[board.formation_name] = self._mapper.clear_selection(
                board
            )

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
        intelligence = self._intelligence_service.analyze(
            board.selected_player,
            self._roster_players,
        )
        self._render_intelligence(intelligence)

    def _render_intelligence(self, intelligence):
        self._clear_inspector()

        if intelligence.availability_state != "available":
            self._render_inspector_message(
                intelligence.headline
            )
            return

        title = QLabel(intelligence.player_name)
        title.setObjectName("formationBoardTitle")
        self.inspector_layout.addWidget(title)

        badge = QLabel(intelligence.profile_label)
        badge.setObjectName("playerProfileBadge")
        self.inspector_layout.addWidget(badge)

        subtitle = QLabel(
            f"{intelligence.current_position_label} | "
            f"{intelligence.current_order_label} | "
            f"Score {intelligence.overall_score_label}"
        )
        subtitle.setObjectName("playerInspectorMeta")
        subtitle.setWordWrap(True)
        self.inspector_layout.addWidget(subtitle)

        note = QLabel(intelligence.headline)
        note.setObjectName("coachNote")
        note.setWordWrap(True)
        self.inspector_layout.addWidget(note)

        if intelligence.why_selected:
            self._add_points(
                "Why selected",
                intelligence.why_selected,
            )

        if intelligence.tactical_contributions:
            self._add_contributions(
                intelligence.tactical_contributions
            )

        if intelligence.strengths:
            self._add_points("Strengths", intelligence.strengths)

        if intelligence.limitations:
            self._add_points("Limitations", intelligence.limitations)

        if intelligence.alternatives:
            self._add_alternatives(intelligence.alternatives)

        if intelligence.technical_attributes:
            self._add_technical_details(
                intelligence.technical_attributes
            )

        self.inspector_layout.addStretch(1)

    def _add_points(self, title, points):
        self.inspector_layout.addWidget(
            self._section_label(title)
        )

        for point in points:
            label = QLabel(
                f"{point.title}: {point.detail}"
            )
            label.setWordWrap(True)
            self.inspector_layout.addWidget(label)

    def _add_contributions(self, contributions):
        self.inspector_layout.addWidget(
            self._section_label("Tactical profile")
        )

        for contribution in contributions:
            label = QLabel(
                f"{contribution.label}: {contribution.display_value} "
                f"({contribution.interpretation})"
            )
            label.setWordWrap(True)
            bar = QProgressBar()
            bar.setObjectName("contributionBar")
            bar.setRange(0, 100)
            bar.setValue(
                int(contribution.normalized_value * 100)
            )
            bar.setTextVisible(False)
            self.inspector_layout.addWidget(label)
            self.inspector_layout.addWidget(bar)

    def _add_alternatives(self, alternatives):
        self.inspector_layout.addWidget(
            self._section_label("Closest alternatives")
        )

        for alternative in alternatives:
            label = QLabel(
                f"{alternative.player_name}: {alternative.score:.2f} "
                f"({alternative.score_difference:+.2f} player score). "
                f"{alternative.reason_not_selected}"
            )
            label.setWordWrap(True)
            self.inspector_layout.addWidget(label)

    def _add_technical_details(self, attributes):
        self.inspector_layout.addWidget(
            self._section_label("Technical details")
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(5)

        for row, (label, value) in enumerate(attributes):
            label_widget = QLabel(label)
            label_widget.setObjectName("playerInspectorMeta")
            value_widget = QLabel(str(value))
            grid.addWidget(label_widget, row, 0)
            grid.addWidget(value_widget, row, 1)

        grid_host = QWidget()
        grid_host.setLayout(grid)
        self.inspector_layout.addWidget(grid_host)

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
