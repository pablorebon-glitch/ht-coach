from PySide6.QtCore import Qt, Signal
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
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.core.localization import t
from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.services.squad_builder_service import AUTO_FORMATION
from ht_coach_app.views.base_page import BasePage
from ht_coach_app.widgets.formation_board.formation_board import FormationBoard
from ht_coach_app.widgets.sortable_table_item import SortableTableItem


class SquadPage(BasePage):
    browse_requested = Signal()
    load_requested = Signal()
    reload_requested = Signal()
    filters_changed = Signal()
    export_requested = Signal()
    player_selected = Signal(str)
    ideal_formation_changed = Signal(str)

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
        self._formation_board_mapper = FormationBoardMapper()
        self._readiness_rows = []
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
        self.tabs = QTabWidget()
        self.tabs.setObjectName("squadTabs")
        self.tabs.setDocumentMode(True)

        self._build_ideal_tab()
        self._build_players_tab()
        self.body_layout.addWidget(self.tabs, 1)

    def _build_ideal_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        summary = QFrame()
        summary.setObjectName("workspacePanel")
        summary_layout = QGridLayout(summary)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        summary_layout.setHorizontalSpacing(12)
        summary_layout.setVerticalSpacing(6)

        self.ideal_formation_combo = QComboBox()
        self.ideal_formation_combo.currentTextChanged.connect(
            self.ideal_formation_changed
        )
        self.ideal_best_label = QLabel(t("squad_builder.empty_title"))
        self.ideal_best_label.setObjectName("sectionTitle")
        self.ideal_score_label = QLabel("")
        self.ideal_confidence_label = QLabel("")
        self.ideal_reason_label = QLabel(t("squad_builder.empty_message"))
        self.ideal_reason_label.setWordWrap(True)

        summary_layout.addWidget(QLabel(t("squad_builder.formation")), 0, 0)
        summary_layout.addWidget(self.ideal_formation_combo, 0, 1)
        summary_layout.addWidget(self.ideal_best_label, 0, 2)
        summary_layout.addWidget(self.ideal_score_label, 0, 3)
        summary_layout.addWidget(self.ideal_confidence_label, 0, 4)
        summary_layout.addWidget(self.ideal_reason_label, 1, 0, 1, 5)
        summary_layout.setColumnStretch(2, 1)
        layout.addWidget(summary)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        self.ideal_board = FormationBoard()
        self.ideal_board.formation_combo.setVisible(False)
        self.ideal_board.reset_workspace_button.setVisible(False)
        splitter.addWidget(self.ideal_board)

        side_scroll = QScrollArea()
        side_scroll.setWidgetResizable(True)
        side_scroll.setFrameShape(QFrame.NoFrame)
        side_panel = QFrame()
        side_panel.setObjectName("workspacePanel")
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(12, 12, 12, 12)
        side_layout.setSpacing(8)

        identity_title = QLabel(t("squad_identity.title"))
        identity_title.setObjectName("sectionTitle")
        self.identity_label = QLabel(t("squad_identity.empty_title"))
        self.identity_label.setObjectName("sectionTitle")
        self.identity_explanation_label = QLabel(t("squad_identity.empty_message"))
        self.identity_explanation_label.setWordWrap(True)
        self.identity_contributors_label = QLabel("")
        self.identity_contributors_label.setWordWrap(True)

        strengths_title = QLabel(t("squad_identity.strengths"))
        strengths_title.setObjectName("sectionTitle")
        self.identity_strengths_label = QLabel("-")
        self.identity_strengths_label.setWordWrap(True)

        weaknesses_title = QLabel(t("squad_identity.weaknesses"))
        weaknesses_title.setObjectName("sectionTitle")
        self.identity_weaknesses_label = QLabel("-")
        self.identity_weaknesses_label.setWordWrap(True)

        readiness_title = QLabel(t("squad_identity.tactical_readiness"))
        readiness_title.setObjectName("sectionTitle")
        self.readiness_table = QTableWidget(0, 2)
        self.readiness_table.setHorizontalHeaderLabels(
            [
                t("squad_identity.tactic"),
                t("squad_identity.readiness_label"),
            ]
        )
        self.readiness_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.readiness_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.readiness_table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.readiness_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.readiness_table.itemSelectionChanged.connect(
            self._show_selected_tactic_detail
        )
        self.readiness_detail_label = QLabel(t("squad_identity.select_tactic"))
        self.readiness_detail_label.setWordWrap(True)

        affinity_title = QLabel(t("squad_identity.formation_affinity"))
        affinity_title.setObjectName("sectionTitle")
        self.formation_affinity_table = QTableWidget(0, 4)
        self.formation_affinity_table.setHorizontalHeaderLabels(
            [
                t("squad_builder.formation"),
                t("squad_identity.affinity"),
                t("squad_builder.score"),
                t("squad_builder.delta"),
            ]
        )
        self.formation_affinity_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.formation_affinity_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        ranking_title = QLabel(t("squad_builder.best_formations"))
        ranking_title.setObjectName("sectionTitle")
        self.ideal_ranking_table = QTableWidget(0, 6)
        self.ideal_ranking_table.setHorizontalHeaderLabels(
            [
                t("squad_builder.rank"),
                t("squad_builder.formation"),
                t("squad_builder.score"),
                t("squad_builder.delta"),
                t("squad_builder.midfield"),
                t("squad_builder.profile"),
            ]
        )
        self.ideal_ranking_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.ideal_ranking_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.ideal_ranking_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        side_layout.addWidget(identity_title)
        side_layout.addWidget(self.identity_label)
        side_layout.addWidget(self.identity_explanation_label)
        side_layout.addWidget(self.identity_contributors_label)
        side_layout.addWidget(strengths_title)
        side_layout.addWidget(self.identity_strengths_label)
        side_layout.addWidget(weaknesses_title)
        side_layout.addWidget(self.identity_weaknesses_label)
        side_layout.addWidget(readiness_title)
        side_layout.addWidget(self.readiness_table)
        side_layout.addWidget(self.readiness_detail_label)
        side_layout.addWidget(affinity_title)
        side_layout.addWidget(self.formation_affinity_table)
        side_layout.addWidget(ranking_title)
        side_layout.addWidget(self.ideal_ranking_table)
        side_layout.addStretch(1)
        side_scroll.setWidget(side_panel)
        splitter.addWidget(side_scroll)
        splitter.setSizes([820, 320])
        layout.addWidget(splitter, 1)

        self.tabs.addTab(tab, t("squad_builder.ideal_xi"))

    def _build_players_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

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
        tab_layout.addWidget(splitter, 1)
        self.tabs.addTab(tab, t("squad_builder.players"))

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

    def set_ideal_formation_options(self, formations):
        current = self.ideal_formation_combo.currentText() or AUTO_FORMATION
        self.ideal_formation_combo.blockSignals(True)
        self.ideal_formation_combo.clear()

        for formation in formations:
            self.ideal_formation_combo.addItem(formation)

        index = self.ideal_formation_combo.findText(current)
        self.ideal_formation_combo.setCurrentIndex(
            index if index >= 0 else 0
        )
        self.ideal_formation_combo.blockSignals(False)

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

    def show_ideal_empty(self):
        self.ideal_best_label.setText(t("squad_builder.empty_title"))
        self.ideal_score_label.setText("")
        self.ideal_confidence_label.setText("")
        self.ideal_reason_label.setText(t("squad_builder.empty_message"))
        self.ideal_ranking_table.setRowCount(0)
        self._set_squad_identity(None)

    def show_ideal_xi(
        self,
        result,
        player_details_by_name=None,
        roster_players=None,
    ):
        self.ideal_formation_combo.blockSignals(True)
        index = self.ideal_formation_combo.findText(result.mode)
        if index >= 0:
            self.ideal_formation_combo.setCurrentIndex(index)
        self.ideal_formation_combo.blockSignals(False)

        self.ideal_best_label.setText(
            t(
                "squad_builder.best_formation_value",
                formation=result.selected_formation_name,
            )
        )
        self.ideal_score_label.setText(
            t(
                "squad_builder.overall_score_value",
                score=f"{result.overall_score:.2f}",
            )
        )
        self.ideal_confidence_label.setText(
            t(
                "squad_builder.confidence_value",
                confidence=result.confidence,
            )
        )
        self.ideal_reason_label.setText(result.reason)
        self._set_ideal_rankings(result.rankings)
        self._set_squad_identity(result.squad_identity)

        boards = [
            self._formation_board_mapper.to_board(
                formation,
                player_details_by_name=player_details_by_name,
            )
            for formation in result.formations
        ]
        self.ideal_board.set_boards(
            boards,
            selected_formation_name=result.selected_formation_name,
            player_details_by_name=player_details_by_name,
            roster_players=roster_players,
        )

    def _set_ideal_rankings(self, rankings):
        self.ideal_ranking_table.setRowCount(len(rankings))

        for row, ranking in enumerate(rankings):
            values = [
                row + 1,
                (
                    f"{ranking.formation_name} *"
                    if ranking.is_best
                    else ranking.formation_name
                ),
                f"{ranking.overall_score:.2f}",
                f"{ranking.score_delta:.2f}",
                f"{ranking.midfield:.2f}",
                ranking.reason,
            ]
            sort_values = [
                row + 1,
                ranking.formation_name.casefold(),
                ranking.overall_score,
                ranking.score_delta,
                ranking.midfield,
                ranking.reason.casefold(),
            ]

            for column, value in enumerate(values):
                item = SortableTableItem(
                    value,
                    sort_values[column],
                )
                if ranking.is_selected:
                    item.setBackground(Qt.GlobalColor.lightGray)
                self.ideal_ranking_table.setItem(row, column, item)

    def _set_squad_identity(self, identity):
        if identity is None:
            self._readiness_rows = []
            self.identity_label.setText(t("squad_identity.empty_title"))
            self.identity_explanation_label.setText(
                t("squad_identity.empty_message")
            )
            self.identity_contributors_label.setText("")
            self.identity_strengths_label.setText("-")
            self.identity_weaknesses_label.setText("-")
            self.readiness_table.setRowCount(0)
            self.readiness_detail_label.setText(
                t("squad_identity.select_tactic")
            )
            self.formation_affinity_table.setRowCount(0)
            return

        self.identity_label.setText(identity.identity)
        self.identity_explanation_label.setText(identity.explanation)
        self.identity_contributors_label.setText(
            self._contributors_text(identity.contributors)
        )
        self.identity_strengths_label.setText(
            ", ".join(identity.strengths) or "-"
        )
        self.identity_weaknesses_label.setText(
            ", ".join(identity.weaknesses) or "-"
        )
        self._set_tactical_readiness(identity.tactical_readiness)
        self._set_formation_affinity(identity.formation_affinity)

    def _set_tactical_readiness(self, readiness_rows):
        self._readiness_rows = list(readiness_rows or [])
        self.readiness_table.setRowCount(len(self._readiness_rows))

        for row, readiness in enumerate(self._readiness_rows):
            values = [
                readiness.tactic_name,
                readiness.level,
            ]
            for column, value in enumerate(values):
                self.readiness_table.setItem(
                    row,
                    column,
                    SortableTableItem(
                        value,
                        str(value).casefold(),
                    ),
                )

        if self._readiness_rows:
            self.readiness_table.selectRow(0)
            self._render_tactic_detail(self._readiness_rows[0])
        else:
            self.readiness_detail_label.setText(
                t("squad_identity.select_tactic")
            )

    def _set_formation_affinity(self, affinity_rows):
        self.formation_affinity_table.setRowCount(len(affinity_rows or []))

        for row, affinity in enumerate(affinity_rows or []):
            values = [
                (
                    f"{affinity.formation_name} *"
                    if affinity.is_best
                    else affinity.formation_name
                ),
                affinity.level,
                f"{affinity.overall_score:.2f}",
                f"{affinity.score_delta:.2f}",
            ]
            sort_values = [
                affinity.formation_name.casefold(),
                affinity.level.casefold(),
                affinity.overall_score,
                affinity.score_delta,
            ]

            for column, value in enumerate(values):
                self.formation_affinity_table.setItem(
                    row,
                    column,
                    SortableTableItem(
                        value,
                        sort_values[column],
                    ),
                )

    def _show_selected_tactic_detail(self):
        selected = self.readiness_table.selectedItems()

        if not selected:
            return

        row = selected[0].row()
        if row < 0 or row >= len(getattr(self, "_readiness_rows", [])):
            return

        self._render_tactic_detail(self._readiness_rows[row])

    def _render_tactic_detail(self, readiness):
        self.readiness_detail_label.setText(
            "\n".join(
                [
                    readiness.why_suitable,
                    t(
                        "squad_identity.detail_strengths",
                        values=", ".join(readiness.strengths) or "-",
                    ),
                    t(
                        "squad_identity.detail_limitations",
                        values=", ".join(readiness.limitations) or "-",
                    ),
                    self._contributors_text(readiness.contributors),
                    t(
                        "squad_identity.compatible_formations_value",
                        formations=", ".join(readiness.compatible_formations) or "-",
                    ),
                ]
            )
        )

    def _contributors_text(self, contributors):
        names = [
            (
                f"{contributor.player_name} ({contributor.value_label})"
                if contributor.value_label
                else contributor.player_name
            )
            for contributor in contributors or []
        ]
        return t(
            "squad_identity.contributors_value",
            players=", ".join(names) or "-",
        )

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
