from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.player_intelligence.service import PlayerIntelligenceService
from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.widgets.formation_board.formation_board_styles import (
    formation_board_stylesheet,
)
from ht_coach_app.widgets.formation_board.layout_metrics import (
    BOARD_MINIMUM_WIDTH,
    BOARD_MINIMUM_HEIGHT,
    COMPACT_PANEL_PADDING,
    COMPACT_SECTION_SPACING,
    INSPECTOR_MINIMUM_WIDTH,
    SPLITTER_BOARD_RATIO,
    SPLITTER_HANDLE_WIDTH,
    SPLITTER_INSPECTOR_RATIO,
)
from ht_coach_app.widgets.formation_board.pitch_widget import PitchWidget
from ht_coach_app.workspace.workspace_service import WorkspaceService


class FormationBoard(QWidget):
    formation_changed = Signal(str)
    recalculate_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mapper = FormationBoardMapper()
        self._intelligence_service = PlayerIntelligenceService()
        self._workspace_service = WorkspaceService()
        self._workspace_state = None
        self._boards = {}
        self._details_by_name = {}
        self._roster_players = []
        self._current_name = ""
        self.setMinimumHeight(BOARD_MINIMUM_HEIGHT)
        self.setStyleSheet(formation_board_stylesheet())
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(COMPACT_SECTION_SPACING)

        header = QFrame()
        header.setObjectName("formationBoardPanel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(8)

        title = QLabel("Formation Board")
        title.setObjectName("formationBoardTitle")
        header_layout.addWidget(title)

        self.formation_combo = QComboBox()
        self.formation_combo.setMinimumWidth(150)
        self.formation_combo.currentTextChanged.connect(self._on_formation_changed)
        header_layout.addWidget(self.formation_combo)

        self.meta_label = QLabel("")
        self.meta_label.setObjectName("formationBoardMeta")
        header_layout.addWidget(self.meta_label)

        self.workspace_status_label = QLabel("Original Recommendation")
        self.workspace_status_label.setObjectName("workspaceStatusBadge")
        self.workspace_status_label.setProperty("state", "clean")
        header_layout.addWidget(self.workspace_status_label)

        header_layout.addStretch(1)

        self.apply_replacement_button = QPushButton("Apply Replacement")
        self.apply_replacement_button.setObjectName("workspaceAction")
        self.apply_replacement_button.setProperty("primary", "true")
        self.apply_replacement_button.clicked.connect(
            self.apply_replacement
        )
        header_layout.addWidget(self.apply_replacement_button)

        self.cancel_replacement_button = QPushButton("Cancel Replacement")
        self.cancel_replacement_button.setObjectName("workspaceAction")
        self.cancel_replacement_button.clicked.connect(
            self.cancel_replacement
        )
        header_layout.addWidget(self.cancel_replacement_button)

        self.reset_workspace_button = QPushButton("Reset Workspace")
        self.reset_workspace_button.setObjectName("workspaceAction")
        self.reset_workspace_button.clicked.connect(
            self.reset_workspace
        )
        header_layout.addWidget(self.reset_workspace_button)

        self.recalculate_button = QPushButton("Recalculate Analysis")
        self.recalculate_button.setObjectName("workspaceAction")
        self.recalculate_button.clicked.connect(
            self._emit_recalculate_requested
        )
        header_layout.addWidget(self.recalculate_button)
        layout.addWidget(header)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setObjectName("formationWorkspaceSplitter")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(SPLITTER_HANDLE_WIDTH)

        pitch_panel = QWidget()
        pitch_panel.setObjectName("pitchPanel")
        pitch_layout = QVBoxLayout(pitch_panel)
        pitch_layout.setContentsMargins(0, 0, 0, 0)
        pitch_layout.setSpacing(6)
        pitch_panel.setMinimumWidth(BOARD_MINIMUM_WIDTH)

        self.pitch = PitchWidget()
        self.pitch.player_selected.connect(self.select_player)
        self.pitch.empty_area_clicked.connect(self.clear_selection)
        pitch_layout.addWidget(self.pitch, 1)

        footer = QFrame()
        footer.setObjectName("formationFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 5, 10, 5)
        self.footer_label = QLabel("")
        self.footer_label.setObjectName("formationBoardMeta")
        footer_layout.addWidget(self.footer_label)
        footer_layout.addStretch(1)
        pitch_layout.addWidget(footer)
        self.splitter.addWidget(pitch_panel)

        self.inspector_scroll = QScrollArea()
        self.inspector_scroll.setObjectName("playerInspectorScroll")
        self.inspector_scroll.setWidgetResizable(True)
        self.inspector_scroll.setFrameShape(QFrame.NoFrame)
        self.inspector_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.inspector_scroll.setMinimumWidth(INSPECTOR_MINIMUM_WIDTH)
        self.inspector_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.inspector = QFrame()
        self.inspector.setObjectName("playerInspectorPanel")
        self.inspector_layout = QVBoxLayout(self.inspector)
        self.inspector_layout.setContentsMargins(
            COMPACT_PANEL_PADDING,
            COMPACT_PANEL_PADDING,
            COMPACT_PANEL_PADDING,
            COMPACT_PANEL_PADDING,
        )
        self.inspector_layout.setSpacing(6)
        self.inspector_scroll.setWidget(self.inspector)
        self.splitter.addWidget(self.inspector_scroll)

        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes(
            [
                int(1000 * SPLITTER_BOARD_RATIO),
                int(1000 * SPLITTER_INSPECTOR_RATIO),
            ]
        )
        layout.addWidget(self.splitter, 1)

    def set_boards(
        self,
        boards,
        selected_formation_name="",
        player_details_by_name=None,
        roster_players=None,
        workspace_state=None,
    ):
        self._details_by_name = player_details_by_name or {}
        self._roster_players = list(roster_players or [])
        if workspace_state is None:
            self._workspace_state = self._workspace_service.create(
                list(boards),
                selected_formation_name,
            )
        else:
            self._workspace_state = (
                self._workspace_service.with_evaluated_boards(
                    workspace_state,
                    list(boards),
                )
            )
        self._sync_boards_cache()
        self.formation_combo.blockSignals(True)
        self.formation_combo.clear()

        for board in boards:
            label = board.formation_name
            if board.recommendation_label:
                label = f"{label} ({board.recommendation_label})"
            self.formation_combo.addItem(label, board.formation_name)

        target = selected_formation_name or (
            boards[0].formation_name if boards else ""
        )
        if workspace_state is not None:
            target = workspace_state.current_formation_name or target
        index = self.formation_combo.findData(target)
        self.formation_combo.setCurrentIndex(index if index >= 0 else 0)
        self.formation_combo.blockSignals(False)
        self._current_name = self.formation_combo.currentData() or ""
        if self._workspace_state is not None:
            self._workspace_state = self._workspace_service.set_formation(
                self._workspace_state,
                self._current_name,
            )
            self._sync_boards_cache()
        self._render_current_board()

    def current_board(self):
        if self._workspace_state is None:
            return None
        return self._workspace_state.current_board

    def workspace_state(self):
        return self._workspace_state

    def select_player(self, player_id):
        board = self.current_board()
        if board is None:
            return

        self._workspace_state = self._workspace_service.select_player(
            self._workspace_state,
            player_id,
        )
        self._sync_boards_cache()
        self._render_current_board()

    def clear_selection(self):
        board = self.current_board()
        if board is None:
            return

        self._workspace_state = self._workspace_service.clear_selection(
            self._workspace_state
        )
        self._sync_boards_cache()
        self._render_current_board()

    def preview_replacement(self, candidate):
        if self._workspace_state is None:
            return

        self._workspace_state = self._workspace_service.preview_replacement(
            self._workspace_state,
            candidate,
        )
        self._sync_boards_cache()
        self._render_current_board()

    def apply_replacement(self):
        if self._workspace_state is None:
            return

        self._workspace_state = self._workspace_service.apply_replacement(
            self._workspace_state,
            self._roster_players,
        )
        self._sync_boards_cache()
        self._render_current_board()

    def cancel_replacement(self):
        if self._workspace_state is None:
            return

        self._workspace_state = self._workspace_service.cancel_replacement(
            self._workspace_state
        )
        self._sync_boards_cache()
        self._render_current_board()

    def reset_workspace(self):
        if self._workspace_state is None:
            return

        self._workspace_state = self._workspace_service.reset(
            self._workspace_state
        )
        self._sync_boards_cache()
        self._render_current_board()

    def _on_formation_changed(self):
        self._current_name = self.formation_combo.currentData() or ""
        if self._workspace_state is not None:
            self._workspace_state = self._workspace_service.set_formation(
                self._workspace_state,
                self._current_name,
            )
            self._sync_boards_cache()

        self.formation_changed.emit(self._current_name)
        self._render_current_board()

    def _render_current_board(self):
        board = self.current_board()
        self.pitch.set_board(board)
        self._update_workspace_toolbar()

        if board is None:
            self.meta_label.setText("")
            self.footer_label.setText("")
            self._render_inspector_message(
                "Run a match analysis to view the recommended formation."
            )
            return

        self.meta_label.setText(board.recommendation_label)
        self._update_footer(board)
        intelligence = self._intelligence_service.analyze(
            board.selected_player,
            self._roster_players,
        )
        self._render_intelligence(intelligence)

    def _update_footer(self, board):
        parts = [
            f"Formation {board.formation_name}",
            f"Tactic {board.tactic_name}",
            f"Level {board.tactic_level:.2f}",
        ]
        if board.selected_player is not None:
            player = board.selected_player
            order = player.order_label or "Normal"
            if player.order_side_label:
                order = f"{order} {player.order_side_label}"
            parts.append(f"Selected order {order}")
        self.footer_label.setText("  |  ".join(parts))

    def _render_intelligence(self, intelligence):
        self._clear_inspector()

        if intelligence.availability_state != "available":
            self._render_inspector_message(intelligence.headline)
            return

        header = QWidget()
        header_layout = QGridLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setHorizontalSpacing(8)
        header_layout.setVerticalSpacing(2)

        title = QLabel(intelligence.player_name)
        title.setObjectName("formationBoardTitle")
        header_layout.addWidget(title, 0, 0)

        badge = QLabel(intelligence.profile_label)
        badge.setObjectName("playerProfileBadge")
        header_layout.addWidget(badge, 0, 1, alignment=Qt.AlignRight)

        subtitle = QLabel(
            f"{intelligence.current_position_label} | "
            f"{intelligence.current_order_label} | "
            f"Score {intelligence.overall_score_label}"
        )
        subtitle.setObjectName("playerInspectorMeta")
        subtitle.setWordWrap(True)
        header_layout.addWidget(subtitle, 1, 0, 1, 2)
        self.inspector_layout.addWidget(header)

        if (
            self._workspace_state is not None
            and self._workspace_state.replacement_preview is not None
        ):
            self._add_preview_panel(
                self._workspace_state.replacement_preview
            )

        note = QLabel(intelligence.headline)
        note.setObjectName("coachNote")
        note.setWordWrap(True)
        self.inspector_layout.addWidget(note)

        overview = QWidget()
        overview_layout = QGridLayout(overview)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        overview_layout.setHorizontalSpacing(10)
        overview_layout.setVerticalSpacing(6)

        if intelligence.why_selected:
            overview_layout.addWidget(
                self._points_group("Why selected", intelligence.why_selected),
                0,
                0,
            )

        strengths_and_limits = QWidget()
        strengths_layout = QVBoxLayout(strengths_and_limits)
        strengths_layout.setContentsMargins(0, 0, 0, 0)
        strengths_layout.setSpacing(6)
        if intelligence.strengths:
            strengths_layout.addWidget(
                self._points_group("Strengths", intelligence.strengths)
            )
        if intelligence.limitations:
            strengths_layout.addWidget(
                self._points_group("Limitations", intelligence.limitations)
            )
        overview_layout.addWidget(strengths_and_limits, 0, 1)
        overview_layout.setColumnStretch(0, 1)
        overview_layout.setColumnStretch(1, 1)
        self.inspector_layout.addWidget(overview)

        if intelligence.tactical_contributions:
            self._add_contributions(intelligence.tactical_contributions)

        if intelligence.alternatives:
            self._add_alternatives(intelligence.alternatives)

        self._add_replacements()

        if intelligence.technical_attributes:
            self._add_technical_details(intelligence.technical_attributes)

        self.inspector_layout.addStretch(1)

    def _points_group(self, title, points):
        group = QWidget()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(self._section_label(title))
        for point in points:
            label = QLabel(f"{point.title}: {point.detail}")
            label.setWordWrap(True)
            layout.addWidget(label)
        return group

    def _add_contributions(self, contributions):
        self.inspector_layout.addWidget(self._section_label("Tactical profile"))
        for contribution in contributions:
            label = QLabel(
                f"{contribution.label}: {contribution.display_value} "
                f"({contribution.interpretation})"
            )
            label.setWordWrap(True)
            bar = QProgressBar()
            bar.setObjectName("contributionBar")
            bar.setRange(0, 100)
            bar.setValue(int(contribution.normalized_value * 100))
            bar.setTextVisible(False)
            self.inspector_layout.addWidget(label)
            self.inspector_layout.addWidget(bar)

    def _add_alternatives(self, alternatives):
        self.inspector_layout.addWidget(self._section_label("Closest alternatives"))
        for alternative in alternatives:
            label = QLabel(
                f"{alternative.player_name}: {alternative.score:.2f} "
                f"({alternative.score_difference:+.2f} player score). "
                f"{alternative.reason_not_selected}"
            )
            label.setWordWrap(True)
            self.inspector_layout.addWidget(label)

    def _add_replacements(self):
        if self._workspace_state is None:
            return

        candidates = self._workspace_service.replacement_candidates(
            self._workspace_state,
            self._roster_players,
        )
        if not candidates:
            return

        self.inspector_layout.addWidget(self._section_label("Replace Player"))
        preview = self._workspace_state.replacement_preview

        for candidate in candidates:
            button = QPushButton(
                f"{candidate.player_name}  |  "
                f"Score {candidate.score:.2f}  "
                f"({candidate.score_difference:+.2f})"
            )
            button.setObjectName("replacementCandidate")
            button.setProperty(
                "selected",
                "true"
                if (
                    preview is not None
                    and preview.replacement_player_id == candidate.player_id
                )
                else "false",
            )
            button.setToolTip(candidate.reason)
            button.clicked.connect(
                lambda checked=False, item=candidate: (
                    self.preview_replacement(item)
                )
            )
            self.inspector_layout.addWidget(button)

    def _add_preview_panel(self, preview):
        panel = QFrame()
        panel.setObjectName("coachNote")
        layout = QGridLayout(panel)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(3)

        rows = [
            ("Preview Replacement", preview.role),
            ("Current Player", preview.current_player_name),
            ("Replacement Player", preview.replacement_player_name),
            ("Player score difference", f"{preview.score_difference:+.2f}"),
        ]
        for row, (label, value) in enumerate(rows):
            key = QLabel(label)
            key.setObjectName("playerInspectorMeta")
            layout.addWidget(key, row, 0)
            layout.addWidget(QLabel(value), row, 1)

        self.inspector_layout.addWidget(panel)

    def _add_technical_details(self, attributes):
        toggle = QToolButton()
        toggle.setObjectName("technicalDetailsToggle")
        toggle.setText("Technical details")
        toggle.setCheckable(True)
        toggle.setChecked(False)
        toggle.setArrowType(Qt.RightArrow)
        toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.inspector_layout.addWidget(toggle)

        details = QWidget()
        details.setObjectName("technicalDetailsContent")
        grid = QGridLayout(details)
        grid.setContentsMargins(14, 2, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(3)
        for row, (label, value) in enumerate(attributes):
            label_widget = QLabel(label)
            label_widget.setObjectName("playerInspectorMeta")
            grid.addWidget(label_widget, row, 0)
            grid.addWidget(QLabel(str(value)), row, 1)

        details.setVisible(False)
        toggle.toggled.connect(details.setVisible)
        toggle.toggled.connect(
            lambda checked: toggle.setArrowType(
                Qt.DownArrow if checked else Qt.RightArrow
            )
        )
        self.inspector_layout.addWidget(details)

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

    def _sync_boards_cache(self):
        if self._workspace_state is None:
            self._boards = {}
            return

        self._boards = dict(self._workspace_state.workspace_boards)

    def _update_workspace_toolbar(self):
        state = self._workspace_state
        if state is None:
            status = "Original Recommendation"
            status_state = "clean"
            has_preview = False
            is_dirty = False
        else:
            status = state.status_label
            status_state = state.status_state
            has_preview = state.replacement_preview is not None
            is_dirty = state.dirty

        self.workspace_status_label.setText(status)
        self.workspace_status_label.setProperty("state", status_state)
        self.workspace_status_label.style().unpolish(
            self.workspace_status_label
        )
        self.workspace_status_label.style().polish(
            self.workspace_status_label
        )
        self.apply_replacement_button.setEnabled(has_preview)
        self.cancel_replacement_button.setEnabled(has_preview)
        self.reset_workspace_button.setEnabled(has_preview or is_dirty)
        self.recalculate_button.setEnabled(is_dirty)

    def _emit_recalculate_requested(self):
        if self._workspace_state is not None:
            self.recalculate_requested.emit(self._workspace_state)

    @staticmethod
    def _section_label(text):
        label = QLabel(text)
        label.setObjectName("formationBoardTitle")
        return label
