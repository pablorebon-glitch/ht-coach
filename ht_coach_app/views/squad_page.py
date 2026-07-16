from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.views.base_page import BasePage
from ht_coach_app.widgets.sortable_table_item import SortableTableItem


class SquadPage(BasePage):
    browse_requested = Signal()
    load_requested = Signal()
    reload_requested = Signal()
    filters_changed = Signal()
    export_requested = Signal()
    player_selected = Signal(str)

    HEADERS = [
        "Name",
        "Age",
        "Form",
        "Stamina",
        "Experience",
        "Leadership",
        "TSI",
        "Salary",
        "Goalkeeper",
        "Defending",
        "Playmaking",
        "Winger",
        "Passing",
        "Scoring",
        "Set Pieces",
        "Specialty",
        "Pos. Score",
        "Pos. Rank",
        "Best Position",
    ]

    def __init__(self, parent=None):
        super().__init__(
            "Squad",
            "Load and inspect the player squad without changing engine behavior.",
            parent
        )
        self._state = "empty"
        self._build_controls()
        self._build_content()

    def _build_controls(self):
        panel = QFrame()
        panel.setObjectName("workspacePanel")
        layout = QGridLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select players.csv")

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_requested)

        load_button = QPushButton("Load")
        load_button.setObjectName("primaryAction")
        load_button.clicked.connect(self.load_requested)

        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(self.reload_requested)

        export_button = QPushButton("Export Visible")
        export_button.clicked.connect(self.export_requested)

        self.loaded_label = QLabel("No players loaded")
        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search player name")
        self.search_edit.textChanged.connect(self.filters_changed)

        self.minimum_form = QSpinBox()
        self.minimum_form.setRange(0, 20)
        self.minimum_form.valueChanged.connect(self.filters_changed)

        self.minimum_stamina = QSpinBox()
        self.minimum_stamina.setRange(0, 20)
        self.minimum_stamina.valueChanged.connect(self.filters_changed)

        self.speciality_combo = QComboBox()
        self.speciality_combo.currentTextChanged.connect(
            self.filters_changed
        )

        self.position_combo = QComboBox()
        self.position_combo.currentTextChanged.connect(
            self.filters_changed
        )

        layout.addWidget(QLabel("Players CSV"), 0, 0)
        layout.addWidget(self.path_edit, 0, 1, 1, 4)
        layout.addWidget(browse_button, 0, 5)
        layout.addWidget(load_button, 0, 6)
        layout.addWidget(reload_button, 0, 7)
        layout.addWidget(export_button, 0, 8)
        layout.addWidget(self.loaded_label, 1, 1, 1, 2)
        layout.addWidget(self.status_label, 1, 3, 1, 6)
        layout.addWidget(QLabel("Search"), 2, 0)
        layout.addWidget(self.search_edit, 2, 1, 1, 2)
        layout.addWidget(QLabel("Min form"), 2, 3)
        layout.addWidget(self.minimum_form, 2, 4)
        layout.addWidget(QLabel("Min stamina"), 2, 5)
        layout.addWidget(self.minimum_stamina, 2, 6)
        layout.addWidget(self.speciality_combo, 2, 7)
        layout.addWidget(self.position_combo, 2, 8)
        layout.setColumnStretch(1, 1)

        self.body_layout.addWidget(panel)

    def _build_content(self):
        splitter = QSplitter()

        table_panel = QFrame()
        table_panel.setObjectName("workspacePanel")
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(12, 12, 12, 12)
        table_layout.setSpacing(8)

        self.state_label = QLabel("Load a roster to inspect players.")
        self.state_label.setWordWrap(True)
        table_layout.addWidget(self.state_label)

        self.players_table = QTableWidget(0, len(self.HEADERS))
        self.players_table.setHorizontalHeaderLabels(self.HEADERS)
        self.players_table.setSortingEnabled(True)
        self.players_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.players_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.players_table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.players_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Interactive
        )
        self.players_table.itemSelectionChanged.connect(
            self._emit_selected_player
        )
        table_layout.addWidget(self.players_table, 1)

        detail_panel = QFrame()
        detail_panel.setObjectName("workspacePanel")
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(12, 12, 12, 12)
        detail_layout.setSpacing(8)

        title = QLabel("Player Detail")
        title.setObjectName("sectionTitle")
        self.detail_label = QLabel("Select a player to see details.")
        self.detail_label.setWordWrap(True)
        self.rankings_table = QTableWidget(0, 3)
        self.rankings_table.setHorizontalHeaderLabels(
            ["Position", "Score", "Rank"]
        )
        self.rankings_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.rankings_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        detail_layout.addWidget(title)
        detail_layout.addWidget(self.detail_label)
        detail_layout.addWidget(self.rankings_table)

        splitter.addWidget(table_panel)
        splitter.addWidget(detail_panel)
        splitter.setSizes([760, 280])
        self.body_layout.addWidget(splitter, 1)

    def csv_path(self):
        return self.path_edit.text().strip()

    def set_csv_path(self, path):
        self.path_edit.setText(path)

    def choose_players_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select players.csv",
            self.csv_path(),
            "CSV files (*.csv);;All files (*.*)"
        )
        return path

    def choose_export_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export visible squad",
            "squad_export.csv",
            "CSV files (*.csv);;All files (*.*)"
        )
        return path

    def set_supported_positions(self, positions):
        current = self.position_combo.currentText()
        self.position_combo.blockSignals(True)
        self.position_combo.clear()
        self.position_combo.addItem("")

        for position in positions:
            self.position_combo.addItem(position)

        index = self.position_combo.findText(current)
        self.position_combo.setCurrentIndex(index if index >= 0 else 0)
        self.position_combo.blockSignals(False)

    def set_specialties(self, specialties):
        current = self.speciality_combo.currentText()
        self.speciality_combo.blockSignals(True)
        self.speciality_combo.clear()
        self.speciality_combo.addItem("")

        for speciality in specialties:
            self.speciality_combo.addItem(speciality)

        index = self.speciality_combo.findText(current)
        self.speciality_combo.setCurrentIndex(index if index >= 0 else 0)
        self.speciality_combo.blockSignals(False)

    def filter_values(self):
        return {
            "search_text": self.search_edit.text(),
            "minimum_form": self.minimum_form.value(),
            "minimum_stamina": self.minimum_stamina.value(),
            "speciality": self.speciality_combo.currentText(),
            "selected_position": self.position_combo.currentText(),
        }

    def set_players(self, rows):
        self.players_table.setSortingEnabled(False)
        self.players_table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            values = [
                row.name,
                row.age,
                row.form,
                row.stamina,
                row.experience,
                row.leadership,
                row.tsi,
                row.salary,
                row.goalkeeper,
                row.defending,
                row.playmaking,
                row.winger,
                row.passing,
                row.scoring,
                row.set_pieces,
                row.speciality,
                f"{row.selected_position_score:.2f}",
                row.selected_position_rank or "",
                row.best_position,
            ]
            sort_values = [
                row.name.casefold(),
                row.age,
                row.form,
                row.stamina,
                row.experience,
                row.leadership,
                row.tsi,
                row.salary,
                row.goalkeeper,
                row.defending,
                row.playmaking,
                row.winger,
                row.passing,
                row.scoring,
                row.set_pieces,
                row.speciality.casefold(),
                row.selected_position_score,
                row.selected_position_rank or None,
                row.best_position.casefold(),
            ]

            for column, value in enumerate(values):
                item = self._build_table_item(
                    value,
                    sort_values[column]
                )
                item.setData(256, row.name)
                self.players_table.setItem(row_index, column, item)

        self.players_table.setSortingEnabled(True)
        self.show_success(f"Showing {len(rows)} players.")

    def set_loaded_count(self, count):
        self.loaded_label.setText(f"{count} players loaded")

    def show_loading(self):
        self._state = "loading"
        self.state_label.setText("Loading roster...")

    def show_success(self, message):
        self._state = "success"
        self.state_label.setText(message)

    def show_status(self, message):
        self.status_label.setProperty("state", "ok")
        self.status_label.setText(message)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def show_error(self, message):
        self._state = "error"
        self.status_label.setProperty("state", "error")
        self.status_label.setText(message)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.state_label.setText(message)

    def clear_detail(self):
        self.detail_label.setText("Select a player to see details.")
        self.rankings_table.setRowCount(0)

    def show_player_detail(self, detail):
        player = detail.player
        self.detail_label.setText(
            "\n".join(
                [
                    f"Name: {player.name}",
                    f"Best position: {player.best_position} ({player.best_position_score:.2f})",
                    f"Form: {player.form}",
                    f"Stamina: {player.stamina}",
                    f"Experience: {player.experience}",
                    f"Leadership: {player.leadership}",
                    f"TSI: {player.tsi}",
                    f"Salary: {player.salary}",
                    f"GK/Def/PM/Wing/Pass/Score/SP: "
                    f"{player.goalkeeper}/{player.defending}/{player.playmaking}/"
                    f"{player.winger}/{player.passing}/{player.scoring}/"
                    f"{player.set_pieces}",
                ]
            )
        )
        self.rankings_table.setRowCount(len(detail.rankings))

        for row, (position, score, rank) in enumerate(detail.rankings):
            for column, value in enumerate(
                [position, f"{score:.2f}", rank]
            ):
                item = SortableTableItem(
                    value,
                    sort_value=(
                        value
                        if column in {1, 2}
                        else str(value).casefold()
                    )
                )
                self.rankings_table.setItem(row, column, item)

    def current_state(self):
        return self._state

    def _emit_selected_player(self):
        selected = self.players_table.selectedItems()

        if not selected:
            return

        name = selected[0].data(256)

        if name:
            self.player_selected.emit(name)

    def _build_table_item(self, value, sort_value):
        return SortableTableItem(
            value,
            sort_value=sort_value
        )
