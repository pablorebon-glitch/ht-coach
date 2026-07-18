from dataclasses import replace

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
from ht_coach_app.widgets.formation_board.bench_panel import BenchPanel
from ht_coach_app.widgets.formation_board.formation_board_models import (
    PlayerCardViewModel,
)
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
    workspace_modified = Signal(object)

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
        self._selected_bench_player_id = ""
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

        self.reset_workspace_button = QPushButton("Reset Workspace")
        self.reset_workspace_button.setObjectName("workspaceAction")
        self.reset_workspace_button.setToolTip(
            "Restore the original recommended lineup."
        )
        self.reset_workspace_button.clicked.connect(
            self.reset_workspace
        )
        header_layout.addWidget(self.reset_workspace_button)
        layout.addWidget(header)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setObjectName("formationWorkspaceSplitter")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(SPLITTER_HANDLE_WIDTH)

        board_bench_panel = QWidget()
        board_bench_layout = QHBoxLayout(board_bench_panel)
        board_bench_layout.setContentsMargins(0, 0, 0, 0)
        board_bench_layout.setSpacing(8)

        pitch_panel = QWidget()
        pitch_panel.setObjectName("pitchPanel")
        pitch_layout = QVBoxLayout(pitch_panel)
        pitch_layout.setContentsMargins(0, 0, 0, 0)
        pitch_layout.setSpacing(6)
        pitch_panel.setMinimumWidth(BOARD_MINIMUM_WIDTH)

        self.pitch = PitchWidget()
        self.pitch.player_selected.connect(self.select_player)
        self.pitch.empty_area_clicked.connect(self.clear_selection)
        self.pitch.player_dropped.connect(self._handle_player_dropped)
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

        self.bench_panel = BenchPanel()
        self.bench_panel.setMinimumWidth(160)
        self.bench_panel.setMaximumWidth(230)
        self.bench_panel.player_selected.connect(self.select_bench_player)
        self.bench_panel.preview_requested.connect(
            self.preview_bench_player_for_selected_slot
        )
        self.bench_panel.starter_dropped_on_player.connect(
            self._handle_starter_dropped_on_bench
        )

        board_bench_layout.addWidget(pitch_panel, 4)
        board_bench_layout.addWidget(self.bench_panel, 1)
        self.splitter.addWidget(board_bench_panel)

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
        self._selected_bench_player_id = ""
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
        if self._selected_bench_player_id:
            target_slot = next(
                (
                    slot for slot in board.slots
                    if slot.player is not None
                    and slot.player.player_id == player_id
                ),
                None,
            )
            if target_slot is not None:
                self._commit_bench_exchange(
                    target_slot.slot_id,
                    self._selected_bench_player_id,
                    "CLICK",
                )
                return
        if board.selected_player_id == player_id:
            self.clear_selection()
            return

        self._workspace_state = self._workspace_service.select_player(
            self._workspace_state,
            player_id,
        )
        self._selected_bench_player_id = ""
        self._sync_boards_cache()
        self._render_current_board()

    def clear_selection(self):
        board = self.current_board()
        if board is None:
            return

        self._workspace_state = self._workspace_service.clear_selection(
            self._workspace_state
        )
        self._selected_bench_player_id = ""
        self._sync_boards_cache()
        self._render_current_board()

    def select_bench_player(self, player_id):
        if self._workspace_state is None:
            return
        board = self.current_board()
        if board is not None and board.selected_player is not None:
            selected_slot = next(
                (
                    slot for slot in board.slots
                    if slot.player is not None
                    and slot.player.player_id == board.selected_player_id
                ),
                None,
            )
            if selected_slot is not None:
                self._commit_bench_exchange(
                    selected_slot.slot_id,
                    player_id,
                    "CLICK",
                )
                return
        if self._selected_bench_player_id == player_id:
            self._selected_bench_player_id = ""
            self._render_current_board()
            return
        self._selected_bench_player_id = player_id
        self._workspace_state = replace(
            self._workspace_state,
            last_error="",
        )
        self._render_current_board()

    def preview_bench_player_for_selected_slot(self, player_id):
        if self._workspace_state is None:
            return
        board = self.current_board()
        if board is None or board.selected_player is None:
            self._workspace_state = replace(
                self._workspace_state,
                last_error="Select a lineup slot before previewing a bench replacement.",
            )
            self._selected_bench_player_id = player_id
            self._render_current_board()
            return
        selected_slot = next(
            (
                slot for slot in board.slots
                if slot.player is not None
                and slot.player.player_id == board.selected_player_id
            ),
            None,
        )
        if selected_slot is None:
            return
        self._commit_bench_exchange(
            selected_slot.slot_id,
            player_id,
            "CLICK",
        )

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

        self._workspace_state = self._workspace_service.apply_preview(
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

        was_dirty = self._workspace_state.dirty
        self._workspace_state = self._workspace_service.reset(
            self._workspace_state
        )
        self._selected_bench_player_id = ""
        if was_dirty:
            self._workspace_state = self._workspace_service.mark_updating(
                self._workspace_state
            )
        self._sync_boards_cache()
        self._render_current_board()
        if was_dirty:
            self.workspace_modified.emit(self._workspace_state)

    def _on_formation_changed(self):
        self._current_name = self.formation_combo.currentData() or ""
        self._selected_bench_player_id = ""
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
        revision = (
            self._workspace_state.revision
            if self._workspace_state is not None
            else 0
        )
        self.pitch.set_board(board, revision=revision)
        self._render_bench()
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
            self._intelligence_player(board),
            self._roster_players,
        )
        self._render_intelligence(intelligence, board)

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

    def _render_intelligence(self, intelligence, board=None):
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
            and self._workspace_state.last_error
        ):
            note = QLabel(self._workspace_state.last_error)
            note.setObjectName("playerInspectorMeta")
            note.setWordWrap(True)
            self.inspector_layout.addWidget(note)

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
                self._points_group(
                    self._why_heading(board.selected_player),
                    intelligence.why_selected,
                ),
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

        self._add_slot_score_comparison(board.selected_player)

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

    def _add_slot_score_comparison(self, selected_player):
        modification = self._modification_for_player(selected_player)
        if modification is None:
            return

        panel = QFrame()
        panel.setObjectName("coachNote")
        panel.setToolTip(
            "Difference between each player's calculated contribution score "
            "for this specific tactical slot."
        )
        layout = QGridLayout(panel)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(3)
        rows = [
            ("Position fit comparison", modification.role),
            (
                "Previous player",
                f"{modification.original_player_name}: "
                f"{modification.previous_slot_score:.2f}",
            ),
            (
                "Current player",
                f"{modification.replacement_player_name}: "
                f"{modification.current_slot_score:.2f}",
            ),
            (
                "Difference",
                f"{modification.score_difference:+.2f} in this slot",
            ),
        ]
        for row, (label, value) in enumerate(rows):
            key = QLabel(label)
            key.setObjectName("playerInspectorMeta")
            layout.addWidget(key, row, 0)
            layout.addWidget(QLabel(value), row, 1)
        self.inspector_layout.addWidget(panel)

    def _add_preview_panel(self, state):
        panel = QFrame()
        panel.setObjectName("coachNote")
        layout = QGridLayout(panel)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(3)

        if state.swap_preview is not None:
            preview = state.swap_preview
            rows = [
                ("Preview Swap", preview.formation_name),
                ("Move", f"{preview.source_player_name} to {preview.target_role}"),
                ("Move", f"{preview.target_player_name} to {preview.source_role}"),
            ]
        else:
            preview = state.replacement_preview
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

    def _render_bench(self):
        if self._workspace_state is None:
            self.bench_panel.set_players((), "", 0, "Bench unavailable.")
            return
        board = self.current_board()
        if board is None:
            self.bench_panel.set_players(
                (),
                "",
                self._workspace_state.revision,
                "Run an analysis to view the bench.",
            )
            return
        if not self._roster_players:
            self.bench_panel.set_players(
                (),
                board.formation_name,
                self._workspace_state.revision,
                "Bench unavailable for restored result.",
            )
            return

        players = self._workspace_service.derive_bench(
            self._workspace_state,
            self._roster_players,
            self._selected_bench_player_id,
        )
        self.bench_panel.set_players(
            players,
            board.formation_name,
            self._workspace_state.revision,
        )

    def _intelligence_player(self, board):
        if self._selected_bench_player_id:
            for item in self._workspace_service.derive_bench(
                self._workspace_state,
                self._roster_players,
                self._selected_bench_player_id,
            ):
                if item.player_id == self._selected_bench_player_id:
                    return PlayerCardViewModel(
                        player_id=item.player_id,
                        player_name=item.player_name,
                        display_name=item.player_name,
                        position=item.best_position,
                        position_label=item.best_position_label,
                        position_abbreviation=item.best_position_abbreviation,
                        side="center",
                        side_label="Center",
                        individual_order="Normal",
                        order_label="Normal",
                        position_score=item.score,
                        is_selected=True,
                    )
        return board.selected_player

    def _update_workspace_toolbar(self):
        state = self._workspace_state
        if state is None:
            status = "Original Recommendation"
            status_state = "clean"
            is_dirty = False
        else:
            status = state.status_label
            status_state = state.status_state
            is_dirty = state.dirty

        self.workspace_status_label.setText(status)
        self.workspace_status_label.setProperty("state", status_state)
        self.workspace_status_label.style().unpolish(
            self.workspace_status_label
        )
        self.workspace_status_label.style().polish(
            self.workspace_status_label
        )
        self.reset_workspace_button.setEnabled(is_dirty)

    def _emit_recalculate_requested(self):
        if self._workspace_state is not None:
            self.recalculate_requested.emit(self._workspace_state)

    def _handle_player_dropped(self, payload, target_slot_id):
        if self._workspace_state is None:
            return

        if payload.get("source_type") == "lineup":
            valid, message = self._workspace_service.validate_swap(
                self._workspace_state,
                payload,
                target_slot_id,
            )
            if valid:
                self._workspace_state = self._workspace_service.swap_slots_immediately(
                    self._workspace_state,
                    self._current_name,
                    payload.get("source_slot_id", ""),
                    target_slot_id,
                    payload.get("revision", -1),
                    interaction_source="DRAG",
                )
                self._selected_bench_player_id = ""
                if not self._workspace_state.last_error:
                    self._workspace_state = self._workspace_service.mark_updating(
                        self._workspace_state
                    )
                self._sync_boards_cache()
                self._render_current_board()
                if not self._workspace_state.last_error:
                    self.workspace_modified.emit(self._workspace_state)
                return
            else:
                self._workspace_state = replace(
                    self._workspace_state,
                    last_error=message,
                )
        elif payload.get("source_type") in ("candidate", "bench"):
            valid, message = self._workspace_service.validate_swap(
                self._workspace_state,
                payload,
                target_slot_id,
            )
            candidate = (
                self._workspace_service.candidate_for_player(
                    self._workspace_state,
                    self._roster_players,
                    payload.get("player_id", ""),
                    target_slot_id,
                )
                if valid
                else None
            )
            if candidate is None:
                self._workspace_state = replace(
                    self._workspace_state,
                    last_error=(
                        message
                        or "This player cannot replace that slot."
                    ),
                )
            else:
                self._commit_bench_exchange(
                    target_slot_id,
                    candidate.player_id,
                    "DRAG",
                )
                return

        self._sync_boards_cache()
        self._render_current_board()

    def _handle_starter_dropped_on_bench(self, payload, bench_player_id):
        if self._workspace_state is None:
            return
        board = self.current_board()
        if board is None:
            return
        try:
            payload_revision = int(payload.get("revision", -1))
        except (TypeError, ValueError):
            payload_revision = -1
        if (
            payload.get("source_type") != "lineup"
            or payload.get("formation_name") != board.formation_name
            or payload_revision != self._workspace_state.revision
        ):
            self._workspace_state = replace(
                self._workspace_state,
                last_error="The lineup changed. Try the drag again.",
            )
        else:
            self._commit_bench_exchange(
                payload.get("source_slot_id", ""),
                bench_player_id,
                "DRAG",
            )
            return
        self._sync_boards_cache()
        self._render_current_board()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.clear_selection()
            event.accept()
            return

        super().keyPressEvent(event)

    def _commit_bench_exchange(self, target_slot_id, bench_player_id, source):
        if self._workspace_state is None:
            return
        board = self.current_board()
        if board is None:
            return
        self._workspace_state = self._workspace_service.replace_slot_immediately(
            self._workspace_state,
            self._roster_players,
            board.formation_name,
            target_slot_id,
            bench_player_id,
            self._workspace_state.revision,
            interaction_source=source,
        )
        self._selected_bench_player_id = ""
        if not self._workspace_state.last_error:
            self._workspace_state = self._workspace_service.clear_selection(
                self._workspace_state
            )
            self._workspace_state = self._workspace_service.mark_updating(
                self._workspace_state
            )
        self._sync_boards_cache()
        self._render_current_board()
        if not self._workspace_state.last_error:
            self.workspace_modified.emit(self._workspace_state)

    @staticmethod
    def _section_label(text):
        label = QLabel(text)
        label.setObjectName("formationBoardTitle")
        return label

    @staticmethod
    def _why_heading(selected_player):
        if selected_player is not None and selected_player.is_modified:
            return "Workspace Impact"
        return "Why Recommended"

    def _modification_for_player(self, selected_player):
        if selected_player is None or self._workspace_state is None:
            return None
        if not selected_player.is_modified:
            return None
        for modification in reversed(self._workspace_state.history):
            if (
                modification.replacement_player_name
                == selected_player.player_name
                and modification.previous_slot_score is not None
                and modification.current_slot_score is not None
            ):
                return modification
        return None
