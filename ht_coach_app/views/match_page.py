from PySide6.QtCore import Signal
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
    copy_lineup_requested = Signal()
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
        self._state = "empty"
        self._build_inputs()
        self._build_results()

    def _build_inputs(self):
        controls = QFrame()
        controls.setObjectName("workspacePanel")
        layout = QGridLayout(controls)
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

        self.body_layout.addWidget(controls, 0)

    def _build_results(self):
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setFrameShape(QFrame.NoFrame)

        self.results_host = QWidget()
        self.results_layout = QVBoxLayout(
            self.results_host
        )
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(12)
        self.results_scroll.setWidget(
            self.results_host
        )

        self._show_empty_results()

        self.body_layout.addWidget(
            self.results_scroll,
            1
        )

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

    def set_processing(self, is_processing):
        self.analyze_button.setEnabled(
            not is_processing
        )
        self.analyze_button.setText(
            "Analyzing..." if is_processing else "Analyze Match"
        )

        if is_processing:
            self.show_loading()

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

    def show_results(self, result, restored=False):
        self._state = "success"
        self._clear_results_widgets()

        header = QHBoxLayout()
        title = QLabel(
            "Last analysis" if restored else "Analysis results"
        )
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)

        copy_summary = QPushButton("Copy Summary")
        copy_summary.clicked.connect(
            self.copy_summary_requested
        )
        header.addWidget(copy_summary)

        copy_lineup = QPushButton("Copy Lineup")
        copy_lineup.clicked.connect(
            self.copy_lineup_requested
        )
        header.addWidget(copy_lineup)

        header_widget = QWidget()
        header_widget.setLayout(header)
        self.results_layout.addWidget(header_widget)

        recommended = result.recommended_formation

        if recommended is not None:
            self.results_layout.addWidget(
                self._build_recommended_summary(
                    recommended
                )
            )

        self.results_layout.addWidget(
            self._build_metadata_panel(result)
        )

        self.results_layout.addWidget(
            self._build_result_tabs(result, restored=restored)
        )

        self.results_layout.addStretch(1)

    def _build_result_tabs(self, result, restored=False):
        tabs = QTabWidget()
        tabs.setObjectName("matchResultTabs")

        tabs.addTab(
            self._build_formation_board_tab(result, restored),
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

    def _build_formation_board_tab(self, result, restored=False):
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
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)

        badge = QLabel("Recommended")
        badge.setObjectName("recommendedBadge")
        layout.addWidget(badge, 0, 0)

        title = QLabel(
            f"{formation.formation_name} - {formation.recommended_tactic}"
        )
        title.setObjectName("resultHeadline")
        layout.addWidget(title, 0, 1, 1, 4)

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
            metric = self._build_metric(label, value)
            layout.addWidget(metric, 1 + index // 4, index % 4)

        return card

    def _build_metadata_panel(self, result):
        panel = QFrame()
        panel.setObjectName("metadataPanel")
        layout = QGridLayout(panel)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(6)

        items = [
            ("Opponent", result.opponent_name),
            ("CSV", result.players_csv_filename),
            ("Players", str(result.player_count)),
            ("Formations", ", ".join(result.analyzed_formations)),
            ("Completed", result.completed_at),
        ]

        for index, (label, value) in enumerate(items):
            layout.addWidget(QLabel(label), 0, index)
            value_label = QLabel(value)
            value_label.setObjectName("metadataValue")
            layout.addWidget(value_label, 1, index)

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

    def _build_metric(self, label, value):
        frame = QFrame()
        frame.setObjectName("metricTile")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        label_widget = QLabel(label)
        label_widget.setObjectName("metricLabel")
        value_widget = QLabel(value)
        value_widget.setObjectName("metricValue")

        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        return frame

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
