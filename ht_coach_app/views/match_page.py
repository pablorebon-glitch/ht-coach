from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.views.base_page import BasePage


class MatchPage(BasePage):
    browse_players_requested = Signal()
    load_players_requested = Signal()
    analyze_requested = Signal()
    workspace_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(
            "Match",
            "Analyze a match against a saved opponent.",
            parent
        )
        self._applying_settings = False
        self._formation_checks = {}
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
        self.formations_container = QWidget()
        self.formations_layout = QHBoxLayout(
            self.formations_container
        )
        self.formations_layout.setContentsMargins(0, 0, 0, 0)
        self.formations_layout.setSpacing(12)

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
        layout.addWidget(self.formations_container, 3, 1, 1, 3)
        layout.addWidget(self.status_label, 4, 0, 1, 3)
        layout.addWidget(self.analyze_button, 4, 3)
        layout.setColumnStretch(1, 1)

        self.body_layout.addWidget(controls)

    def _build_results(self):
        title = QLabel("Results")
        title.setObjectName("sectionTitle")
        self.body_layout.addWidget(title)

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

    def set_supported_formations(self, formation_names):
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

    def clear_results(self):
        self._clear_results_widgets()
        self._show_empty_results()

    def show_results(self, result):
        self._clear_results_widgets()

        summary = QLabel(
            f"{result.player_count} players analyzed against {result.opponent_name}"
        )
        summary.setObjectName("sectionTitle")
        self.results_layout.addWidget(summary)

        for formation in result.formations:
            self.results_layout.addWidget(
                self._build_formation_card(formation)
            )

        self.results_layout.addStretch(1)

    def _build_formation_card(self, formation):
        card = QFrame()
        card.setObjectName("resultCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        badge = "Recommended" if formation.is_recommended else ""
        title = QLabel(
            f"{formation.formation_name} {badge}".strip()
        )
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        comparison = QTableWidget(1, 9)
        comparison.setHorizontalHeaderLabels(
            [
                "Formation",
                "Tactic",
                "Level",
                "Win",
                "Draw",
                "Loss",
                "Possession",
                "xG",
                "Opp xG",
            ]
        )
        comparison.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        comparison.setSelectionMode(
            QAbstractItemView.NoSelection
        )
        comparison.verticalHeader().setVisible(False)
        comparison.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        comparison.setMaximumHeight(92)

        values = [
            formation.formation_name,
            formation.recommended_tactic,
            f"{formation.tactic_level:.2f}",
            self._format_percent(formation.win_probability),
            self._format_percent(formation.draw_probability),
            self._format_percent(formation.loss_probability),
            self._format_percent(formation.possession),
            f"{formation.expected_goals:.2f}",
            f"{formation.opponent_expected_goals:.2f}",
        ]

        for column, value in enumerate(values):
            comparison.setItem(
                0,
                column,
                QTableWidgetItem(value)
            )

        layout.addWidget(comparison)

        lineup = QTableWidget(
            len(formation.lineup),
            5
        )
        lineup.setHorizontalHeaderLabels(
            [
                "Position",
                "Side",
                "Order",
                "Order Side",
                "Player",
            ]
        )
        lineup.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        lineup.setSelectionMode(
            QAbstractItemView.NoSelection
        )
        lineup.verticalHeader().setVisible(False)
        lineup.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        lineup.setMinimumHeight(280)

        for row, player in enumerate(formation.lineup):
            row_values = [
                player.position,
                player.side,
                player.order,
                player.order_side,
                player.player_name,
            ]

            for column, value in enumerate(row_values):
                lineup.setItem(
                    row,
                    column,
                    QTableWidgetItem(value)
                )

        layout.addWidget(lineup)
        return card

    def _clear_results_widgets(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.setParent(None)

    def _show_empty_results(self):
        empty_results_label = QLabel(
            "Run an analysis to see formation comparison and recommended XI."
        )
        empty_results_label.setWordWrap(True)
        self.results_layout.addWidget(
            empty_results_label
        )
        self.results_layout.addStretch(1)

    def _emit_workspace_changed(self):
        if not self._applying_settings:
            self.workspace_changed.emit()

    @staticmethod
    def _format_percent(value):
        return f"{value * 100:.1f}%"
