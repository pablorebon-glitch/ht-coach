from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.views.base_page import BasePage
from ht_coach_app.widgets.formation_board.formation_board import FormationBoard


class MatchPage(BasePage):
    browse_players_requested = Signal()
    load_players_requested = Signal()
    analyze_requested = Signal()
    copy_summary_requested = Signal()
    copy_decision_lab_requested = Signal()
    copy_lineup_requested = Signal()
    workspace_recalculate_requested = Signal(object)
    workspace_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(
            "Match",
            "Analyze a match against a saved opponent.",
            parent
        )
        self._applying_settings = False
        self._formation_checks = {}
        self._favorite_formations = []
        self._formation_board_mapper = FormationBoardMapper()
        self._roster_players = []
        self._state = "empty"
        self._analysis_inputs_collapsed = False
        self.body_layout.setContentsMargins(16, 12, 16, 12)
        self.body_layout.setSpacing(8)
        self._build_scroll_content()
        self._build_inputs()
        self._build_results()

    def _build_scroll_content(self):
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("matchPageScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.match_content = QWidget()
        self.match_content_layout = QVBoxLayout(
            self.match_content
        )
        self.match_content_layout.setContentsMargins(0, 0, 0, 0)
        self.match_content_layout.setSpacing(8)
        self.scroll_area.setWidget(
            self.match_content
        )
        self.body_layout.addWidget(self.scroll_area, 1)

    def _build_inputs(self):
        self.analysis_setup_panel = QFrame()
        self.analysis_setup_panel.setObjectName("workspacePanel")
        setup_layout = QVBoxLayout(self.analysis_setup_panel)
        setup_layout.setContentsMargins(14, 10, 14, 12)
        setup_layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        title = QLabel("Analysis Setup")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.analysis_setup_toggle = QToolButton()
        self.analysis_setup_toggle.setObjectName("analysisSetupToggle")
        self.analysis_setup_toggle.setToolButtonStyle(
            Qt.ToolButtonTextBesideIcon
        )
        self.analysis_setup_toggle.clicked.connect(
            self.toggle_analysis_inputs
        )
        header.addWidget(self.analysis_setup_toggle)
        setup_layout.addLayout(header)

        self.analysis_inputs_panel = QWidget()
        layout = QGridLayout(self.analysis_inputs_panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        csv_label = QLabel("Players CSV")
        self.players_path_edit = QLineEdit()
        self.players_path_edit.setPlaceholderText(
            "Select players.csv"
        )
        self.players_path_edit.textChanged.connect(
            self._emit_workspace_changed
        )

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(
            self.browse_players_requested
        )

        load_button = QPushButton("Load Players")
        load_button.clicked.connect(
            self.load_players_requested
        )

        self.players_loaded_label = QLabel("No players loaded")

        opponent_label = QLabel("Opponent")
        self.opponent_combo = QComboBox()
        self.opponent_combo.currentTextChanged.connect(
            self._emit_workspace_changed
        )

        formation_label = QLabel("Formations")
        formation_actions = QHBoxLayout()
        formation_actions.setContentsMargins(0, 0, 0, 0)
        formation_actions.setSpacing(8)

        select_all_button = QPushButton("Select All")
        select_all_button.clicked.connect(
            self.select_all_formations
        )
        formation_actions.addWidget(select_all_button)

        clear_all_button = QPushButton("Clear All")
        clear_all_button.clicked.connect(
            self.clear_all_formations
        )
        formation_actions.addWidget(clear_all_button)

        favorites_button = QPushButton("Favorites")
        favorites_button.clicked.connect(
            self.select_favorite_formations
        )
        formation_actions.addWidget(favorites_button)
        formation_actions.addStretch(1)

        formation_actions_widget = QWidget()
        formation_actions_widget.setLayout(
            formation_actions
        )

        self.formations_container = QWidget()
        self.formations_layout = QHBoxLayout(
            self.formations_container
        )
        self.formations_layout.setContentsMargins(0, 0, 0, 0)
        self.formations_layout.setSpacing(12)

        self.formation_warning_label = QLabel("")
        self.formation_warning_label.setWordWrap(True)
        self.formation_warning_label.setProperty(
            "state",
            "warning"
        )

        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)

        self.analyze_button = QPushButton("Analyze Match")
        self.analyze_button.setObjectName("primaryAction")
        self.analyze_button.clicked.connect(
            self.analyze_requested
        )

        layout.addWidget(csv_label, 0, 0)
        layout.addWidget(self.players_path_edit, 0, 1)
        layout.addWidget(browse_button, 0, 2)
        layout.addWidget(load_button, 0, 3)
        layout.addWidget(self.players_loaded_label, 1, 1, 1, 3)
        layout.addWidget(opponent_label, 2, 0)
        layout.addWidget(self.opponent_combo, 2, 1, 1, 3)
        layout.addWidget(formation_label, 3, 0)
        layout.addWidget(formation_actions_widget, 3, 1, 1, 3)
        layout.addWidget(self.formations_container, 4, 1, 1, 3)
        layout.addWidget(self.formation_warning_label, 5, 1, 1, 3)
        layout.addWidget(self.status_label, 6, 0, 1, 3)
        layout.addWidget(self.analyze_button, 6, 3)
        layout.setColumnStretch(1, 1)

        setup_layout.addWidget(self.analysis_inputs_panel)
        self.match_content_layout.addWidget(self.analysis_setup_panel, 0)
        self._sync_analysis_setup_toggle()

    def _build_results(self):
        self.results_host = QWidget()
        self.results_layout = QVBoxLayout(
            self.results_host
        )
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(6)
        self._show_empty_results()
        self.match_content_layout.addWidget(self.results_host, 1)

    def set_opponents(self, opponent_names, selected_name=None):
        current = (
            self.selected_opponent_name()
            if selected_name is None
            else selected_name
        )
        self.opponent_combo.blockSignals(True)
        self.opponent_combo.clear()
        self.opponent_combo.addItem("")

        for name in opponent_names:
            self.opponent_combo.addItem(name)

        index = self.opponent_combo.findText(current)
        if index >= 0:
            self.opponent_combo.setCurrentIndex(index)
        else:
            self.opponent_combo.setCurrentIndex(0)

        self.opponent_combo.blockSignals(False)

    def set_supported_formations(
        self,
        formation_names,
        favorite_formations=None
    ):
        if favorite_formations is not None:
            self._favorite_formations = list(
                favorite_formations
            )

        while self.formations_layout.count():
            item = self.formations_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.setParent(None)

        self._formation_checks = {}

        for name in formation_names:
            checkbox = QCheckBox(name)
            checkbox.stateChanged.connect(
                self._emit_workspace_changed
            )
            self._formation_checks[name] = checkbox
            self.formations_layout.addWidget(checkbox)

        self.formations_layout.addStretch(1)
        self._update_formation_warning()

    def apply_settings(self, settings):
        self._applying_settings = True
        self.players_path_edit.setText(
            settings.players_csv_path
        )

        opponent_index = self.opponent_combo.findText(
            settings.opponent_name
        )
        if opponent_index >= 0:
            self.opponent_combo.setCurrentIndex(
                opponent_index
            )

        selected = set(
            settings.selected_formations
        )
        for name, checkbox in self._formation_checks.items():
            checkbox.setChecked(
                name in selected
            )

        self._applying_settings = False
        self._update_formation_warning()

    def players_csv_path(self):
        return self.players_path_edit.text().strip()

    def set_players_csv_path(self, path):
        self.players_path_edit.setText(path)

    def selected_opponent_name(self):
        return self.opponent_combo.currentText().strip()

    def selected_formations(self):
        return [
            name for name, checkbox in self._formation_checks.items()
            if checkbox.isChecked()
        ]

    def select_all_formations(self):
        self._set_checked_formations(
            set(self._formation_checks)
        )

    def clear_all_formations(self):
        self._set_checked_formations(set())

    def select_favorite_formations(self):
        self._set_checked_formations(
            set(self._favorite_formations)
        )

    def _set_checked_formations(self, selected):
        self._applying_settings = True

        for name, checkbox in self._formation_checks.items():
            checkbox.setChecked(
                name in selected
            )

        self._applying_settings = False
        self._emit_workspace_changed()

    def choose_players_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select players.csv",
            self.players_csv_path(),
            "CSV files (*.csv);;All files (*.*)"
        )
        return path

    def set_players_loaded_count(self, count):
        self.players_loaded_label.setText(
            f"{count} players loaded"
        )

    def set_roster_players(self, players):
        self._roster_players = list(players or [])

    def set_processing(self, is_processing):
        self.analyze_button.setEnabled(
            not is_processing
        )
        self.analyze_button.setText(
            "Analyzing..." if is_processing else "Analyze Match"
        )

        if is_processing:
            self.show_loading()

    def set_workspace_processing(self, is_processing):
        self.analyze_button.setEnabled(
            not is_processing
        )
        self.analyze_button.setText(
            "Updating..." if is_processing else "Analyze Match"
        )

    def show_status(self, message):
        self.status_label.setProperty(
            "state",
            "ok"
        )
        self.status_label.setText(message)
        self.status_label.style().unpolish(
            self.status_label
        )
        self.status_label.style().polish(
            self.status_label
        )

    def show_error(self, message):
        self._state = "error"
        self.expand_analysis_inputs()
        self.status_label.setProperty(
            "state",
            "error"
        )
        self.status_label.setText(message)
        self.status_label.style().unpolish(
            self.status_label
        )
        self.status_label.style().polish(
            self.status_label
        )
        self.set_processing(False)
        self._clear_results_widgets()
        self._show_state_message(
            "Analysis could not complete",
            message
        )

    def clear_results(self):
        self._clear_results_widgets()
        self._show_empty_results()

    def show_loading(self):
        self._state = "loading"
        self._clear_results_widgets()
        self._show_state_message(
            "Analyzing match",
            "Optimizing formations, lineup, individual orders and tactic."
        )

    def show_results(self, result, restored=False, workspace_state=None):
        scroll_value = self.scroll_area.verticalScrollBar().value()
        self._state = "success"
        self._clear_results_widgets()
        self.collapse_analysis_inputs()

        recommended = result.recommended_formation

        self.results_layout.addWidget(
            self._build_analysis_context(result),
            0,
        )

        if recommended is not None:
            self.results_layout.addWidget(
                self._build_recommended_summary(
                    recommended
                )
            )

        if result.decision_lab is not None:
            self.results_layout.addWidget(
                self._build_decision_lab_panel(
                    result.decision_lab,
                    recommended,
                )
            )

        self.results_layout.addWidget(
            self._build_result_tabs(
                result,
                restored=restored,
                workspace_state=workspace_state,
            ),
            1,
        )
        self.scroll_area.verticalScrollBar().setValue(scroll_value)

    def show_workspace_updating(self):
        self.show_status("Updating Workspace analysis...")

    def show_workspace_analysis_failed(self, message):
        self.show_status(f"Analysis failed: {message}")

    def collapse_analysis_inputs(self):
        self._analysis_inputs_collapsed = True
        self.analysis_inputs_panel.setVisible(False)
        self.set_compact_header(True)
        self._sync_analysis_setup_toggle()

    def expand_analysis_inputs(self):
        self._analysis_inputs_collapsed = False
        self.analysis_inputs_panel.setVisible(True)
        self.set_compact_header(False)
        self._sync_analysis_setup_toggle()

    def toggle_analysis_inputs(self):
        if self.analysis_inputs_expanded():
            self.collapse_analysis_inputs()
        else:
            self.expand_analysis_inputs()

    def analysis_inputs_expanded(self):
        return not self._analysis_inputs_collapsed

    def _build_result_tabs(self, result, restored=False, workspace_state=None):
        tabs = QTabWidget()
        tabs.setObjectName("matchResultTabs")
        tabs.setDocumentMode(True)
        tabs.setMinimumHeight(720)

        tabs.addTab(
            self._build_formation_board_tab(
                result,
                restored,
                workspace_state=workspace_state,
            ),
            "Formation Board",
        )
        tabs.addTab(
            self._build_comparison_table(result),
            "Comparison",
        )

        recommended = result.recommended_formation
        if recommended is not None:
            tabs.addTab(
                self._build_lineup_table(recommended),
                "Detailed XI",
            )

        return tabs

    def _build_formation_board_tab(
        self,
        result,
        restored=False,
        workspace_state=None,
    ):
        try:
            boards = [
                self._formation_board_mapper.to_board(
                    formation,
                    restored=restored,
                )
                for formation in result.formations
            ]
            board = FormationBoard()
            recommended = result.recommended_formation
            board.set_boards(
                boards,
                selected_formation_name=(
                    recommended.formation_name
                    if recommended is not None
                    else ""
                ),
                roster_players=self._roster_players,
                workspace_state=workspace_state,
            )
            board.recalculate_requested.connect(
                self.workspace_recalculate_requested.emit
            )
            board.workspace_modified.connect(
                self.workspace_recalculate_requested.emit
            )
            return board
        except Exception as exc:
            panel = QFrame()
            panel.setObjectName("statePanel")
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(18, 18, 18, 18)
            layout.setSpacing(6)

            title = QLabel("Formation board could not render")
            title.setObjectName("sectionTitle")
            message = QLabel(
                "The comparison and Detailed XI tabs are still available. "
                f"Board error: {exc}"
            )
            message.setWordWrap(True)
            layout.addWidget(title)
            layout.addWidget(message)
            return panel

    def _build_recommended_summary(self, formation):
        card = QFrame()
        card.setObjectName("recommendedCard")
        layout = QGridLayout(card)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(4)

        badge = QLabel("Recommended")
        badge.setObjectName("recommendedBadge")
        layout.addWidget(badge, 0, 0)

        title = QLabel(
            f"{formation.formation_name} - {formation.recommended_tactic}"
        )
        title.setObjectName("sectionTitle")
        layout.addWidget(title, 0, 1)

        values = [
            ("Tactic level", f"{formation.tactic_level:.2f}"),
            ("Win", self._format_percent(formation.win_probability)),
            ("Draw", self._format_percent(formation.draw_probability)),
            ("Loss", self._format_percent(formation.loss_probability)),
            ("Possession", self._format_percent(formation.possession)),
            ("xG", f"{formation.expected_goals:.2f}"),
            ("Opp xG", f"{formation.opponent_expected_goals:.2f}"),
        ]

        for index, (label, value) in enumerate(values):
            metric = QLabel(f"{label}  {value}")
            metric.setObjectName("compactMetric")
            layout.addWidget(metric, 0, index + 2)

        layout.setColumnStretch(1, 1)

        return card

    def _build_decision_lab_panel(self, decision_lab, recommended):
        card = QFrame()
        card.setObjectName("compactDecisionLab")
        layout = QGridLayout(card)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(3)

        title = QLabel("Decision Lab")
        title.setObjectName("sectionTitle")
        layout.addWidget(title, 0, 0, 1, 3)

        confidence = QLabel(
            f"Recommendation confidence: {decision_lab.confidence.level}"
        )
        confidence.setObjectName("recommendedBadge")
        layout.addWidget(confidence, 0, 3)

        if recommended is None:
            headline = QLabel(decision_lab.headline)
            headline.setWordWrap(True)
            layout.addWidget(headline, 1, 0, 1, 4)
            return card

        reason = (
            decision_lab.reasons[0].description
            if decision_lab.reasons
            else decision_lab.headline
        )
        risk = (
            decision_lab.risks[0].description
            if decision_lab.risks
            else decision_lab.summary
        )
        scenarios = [
            (
                "Play to win",
                self._format_percent(recommended.win_probability),
                reason,
            ),
            (
                "Secure the draw",
                self._format_percent(recommended.draw_probability),
                decision_lab.confidence.explanation,
            ),
            (
                "Avoid defeat",
                self._format_percent(
                    recommended.win_probability + recommended.draw_probability
                ),
                risk,
            ),
        ]
        for column, (label, probability, explanation) in enumerate(scenarios):
            section = QWidget()
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(1)
            heading = QLabel(f"{label}  {probability}")
            heading.setObjectName("metadataValue")
            detail = QLabel(self._short_text(explanation))
            detail.setObjectName("compactDecisionText")
            detail.setWordWrap(True)
            section_layout.addWidget(heading)
            section_layout.addWidget(detail)
            layout.addWidget(section, 1, column)
            layout.setColumnStretch(column, 1)

        return card

    def _build_analysis_context(self, result):
        panel = QFrame()
        panel.setObjectName("metadataPanel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(12)

        items = [
            ("Opponent", result.opponent_name),
            ("Formations", str(len(result.analyzed_formations))),
        ]

        for label, value in items:
            value_label = QLabel(f"{label}: {value}")
            value_label.setObjectName("metadataValue")
            layout.addWidget(value_label)

        layout.addStretch(1)
        return panel

    def _build_comparison_table(self, result):
        card = QFrame()
        card.setObjectName("resultCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Formation comparison")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        table = QTableWidget(
            len(result.formations),
            9
        )
        table.setObjectName("comparisonTable")
        table.setHorizontalHeaderLabels(
            [
                "",
                "Formation",
                "Tactic",
                "Win / Draw / Loss",
                "Possession",
                "xG",
                "Opp xG",
                "Win diff",
                "xG diff",
            ]
        )
        self._configure_table(table)
        table.setMinimumHeight(
            86 + 28 * max(1, len(result.formations))
        )

        for row, formation in enumerate(result.formations):
            row_values = [
                "*" if formation.is_recommended else "",
                formation.formation_name,
                formation.recommended_tactic,
                (
                    f"{self._format_percent(formation.win_probability)} / "
                    f"{self._format_percent(formation.draw_probability)} / "
                    f"{self._format_percent(formation.loss_probability)}"
                ),
                self._format_percent(formation.possession),
                f"{formation.expected_goals:.2f}",
                f"{formation.opponent_expected_goals:.2f}",
                self._format_delta_percent(
                    formation.win_probability_delta
                ),
                self._format_delta_number(
                    formation.expected_goals_delta
                ),
            ]

            for column, value in enumerate(row_values):
                item = QTableWidgetItem(value)
                if formation.is_recommended:
                    item.setData(256, "recommended")
                table.setItem(row, column, item)

        table.setSortingEnabled(True)
        layout.addWidget(table)
        return card

    def _build_lineup_table(self, formation):
        card = QFrame()
        card.setObjectName("resultCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Recommended XI")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        table = QTableWidget(
            len(formation.lineup),
            6
        )
        table.setHorizontalHeaderLabels(
            [
                "No.",
                "Side",
                "Position",
                "Player",
                "Order",
                "Order Side",
            ]
        )
        self._configure_table(table)
        table.setMinimumHeight(330)

        for row, player in enumerate(formation.lineup):
            row_values = [
                str(player.number),
                player.side,
                player.position,
                player.player_name,
                player.order,
                player.order_side or "-",
            ]

            for column, value in enumerate(row_values):
                table.setItem(
                    row,
                    column,
                    QTableWidgetItem(value)
                )

        layout.addWidget(table)
        return card

    def _configure_table(self, table):
        table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        table.setSelectionMode(
            QAbstractItemView.NoSelection
        )
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

    def _clear_results_widgets(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.setParent(None)

    def _show_empty_results(self):
        self._state = "empty"
        self._show_state_message(
            "No analysis yet",
            "Run a match analysis to view the recommended formation."
        )

    def _show_state_message(self, title, message):
        panel = QFrame()
        panel.setObjectName("statePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        message_label = QLabel(message)
        message_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(message_label)
        self.results_layout.addWidget(panel)
        self.results_layout.addStretch(1)

    def copy_text_to_clipboard(self, text):
        QApplication.clipboard().setText(text)

    def current_state(self):
        return self._state

    def recommended_rows(self, result):
        return [
            formation.formation_name
            for formation in result.formations
            if formation.is_recommended
        ]

    def comparison_rows(self, result):
        return [
            {
                "formation": formation.formation_name,
                "recommended": formation.is_recommended,
                "win_delta": formation.win_probability_delta,
                "xg_delta": formation.expected_goals_delta,
            }
            for formation in result.formations
        ]

    def decision_lab_rows(self, result):
        if result.decision_lab is None:
            return {}

        return {
            "formation": result.decision_lab.recommended_formation.formation,
            "confidence": result.decision_lab.confidence.level,
            "reasons": [
                reason.title
                for reason in result.decision_lab.reasons
            ],
            "risks": [
                risk.title
                for risk in result.decision_lab.risks
            ],
            "comparisons": [
                comparison.alternative_formation
                for comparison in result.decision_lab.comparisons
            ],
            "weaknesses": [
                weakness.classification
                for weakness in result.decision_lab.opponent_weaknesses
            ],
        }

    def lineup_rows(self, formation):
        return [
            {
                "number": player.number,
                "side": player.side,
                "position": player.position,
                "player": player.player_name,
                "order": player.order,
                "order_side": player.order_side,
            }
            for player in formation.lineup
        ]

    def _format_delta_percent(self, value):
        if abs(value) < 0.0001:
            return "0.0 pp"

        return f"{value * 100:+.1f} pp"

    def _format_delta_number(self, value):
        if abs(value) < 0.0001:
            return "0.00"

        return f"{value:+.2f}"

    @staticmethod
    def _format_percent(value):
        return f"{value * 100:.1f}%"

    @staticmethod
    def _short_text(value, limit=110):
        text = " ".join(str(value or "").split())
        if len(text) <= limit:
            return text

        return f"{text[:limit - 3].rstrip()}..."

    def _emit_workspace_changed(self):
        self._update_formation_warning()

        if not self._applying_settings:
            self.workspace_changed.emit()

    def _update_formation_warning(self):
        if not hasattr(self, "formation_warning_label"):
            return

        selected_count = len(self.selected_formations())

        if selected_count > 4:
            self.formation_warning_label.setText(
                "Many formations selected. Analysis can take longer."
            )
        else:
            self.formation_warning_label.setText("")

    def _sync_analysis_setup_toggle(self):
        if not hasattr(self, "analysis_setup_toggle"):
            return

        if self.analysis_inputs_expanded():
            self.analysis_setup_toggle.setText("Hide analysis setup")
            self.analysis_setup_toggle.setArrowType(Qt.DownArrow)
        else:
            self.analysis_setup_toggle.setText("Show analysis setup")
            self.analysis_setup_toggle.setArrowType(Qt.RightArrow)
