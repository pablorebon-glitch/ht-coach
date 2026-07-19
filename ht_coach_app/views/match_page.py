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

from ht_coach_app.core.localization import t
from engine.squad_health.availability_service import (
    CURRENT_AVAILABLE,
    FULL_STRENGTH,
)
from engine.advisor.recommendation_engine import (
    format_win_delta,
    impact_band,
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
            t("match.title"),
            t("match.subtitle"),
            parent
        )
        self._applying_settings = False
        self._formation_checks = {}
        self._favorite_formations = []
        self._formation_board_mapper = FormationBoardMapper()
        self._roster_players = []
        self._state = "empty"
        self._last_result = None
        self._last_restored = False
        self._last_workspace_state = None
        self._advisor_verbosity = "detailed"
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
        title = QLabel(t("match.analysis_setup"))
        self.analysis_setup_title = title
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

        csv_label = QLabel(t("match.players_csv"))
        self.csv_label = csv_label
        self.players_path_edit = QLineEdit()
        self.players_path_edit.setPlaceholderText(
            t("match.select_players_csv")
        )
        self.players_path_edit.textChanged.connect(
            self._emit_workspace_changed
        )

        browse_button = QPushButton(t("match.browse"))
        self.browse_button = browse_button
        browse_button.clicked.connect(
            self.browse_players_requested
        )

        load_button = QPushButton(t("match.load_players"))
        self.load_button = load_button
        load_button.clicked.connect(
            self.load_players_requested
        )

        self.players_loaded_label = QLabel(t("match.no_players_loaded"))

        availability_label = QLabel(t("match.availability_mode"))
        self.availability_label = availability_label
        self.availability_combo = QComboBox()
        self.availability_combo.addItem(
            t("match.availability_current"),
            CURRENT_AVAILABLE,
        )
        self.availability_combo.addItem(
            t("match.availability_full_strength"),
            FULL_STRENGTH,
        )
        self.availability_combo.currentIndexChanged.connect(
            self._emit_workspace_changed
        )
        self.availability_warning_label = QLabel("")
        self.availability_warning_label.setWordWrap(True)

        opponent_label = QLabel(t("match.opponent"))
        self.opponent_label = opponent_label
        self.opponent_combo = QComboBox()
        self.opponent_combo.currentTextChanged.connect(
            self._emit_workspace_changed
        )

        formation_label = QLabel(t("match.formations"))
        self.formation_label = formation_label
        formation_actions = QHBoxLayout()
        formation_actions.setContentsMargins(0, 0, 0, 0)
        formation_actions.setSpacing(8)

        select_all_button = QPushButton(t("match.select_all"))
        self.select_all_button = select_all_button
        select_all_button.clicked.connect(
            self.select_all_formations
        )
        formation_actions.addWidget(select_all_button)

        clear_all_button = QPushButton(t("match.clear_all"))
        self.clear_all_button = clear_all_button
        clear_all_button.clicked.connect(
            self.clear_all_formations
        )
        formation_actions.addWidget(clear_all_button)

        favorites_button = QPushButton(t("match.favorites"))
        self.favorites_button = favorites_button
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

        self.status_label = QLabel(t("match.ready"))
        self.status_label.setWordWrap(True)

        self.analyze_button = QPushButton(t("match.analyze"))
        self.analyze_button.setObjectName("primaryAction")
        self.analyze_button.clicked.connect(
            self.analyze_requested
        )

        layout.addWidget(csv_label, 0, 0)
        layout.addWidget(self.players_path_edit, 0, 1)
        layout.addWidget(browse_button, 0, 2)
        layout.addWidget(load_button, 0, 3)
        layout.addWidget(self.players_loaded_label, 1, 1, 1, 3)
        layout.addWidget(availability_label, 2, 0)
        layout.addWidget(self.availability_combo, 2, 1, 1, 3)
        layout.addWidget(self.availability_warning_label, 3, 1, 1, 3)
        layout.addWidget(opponent_label, 4, 0)
        layout.addWidget(self.opponent_combo, 4, 1, 1, 3)
        layout.addWidget(formation_label, 5, 0)
        layout.addWidget(formation_actions_widget, 5, 1, 1, 3)
        layout.addWidget(self.formations_container, 6, 1, 1, 3)
        layout.addWidget(self.formation_warning_label, 7, 1, 1, 3)
        layout.addWidget(self.status_label, 8, 0, 1, 3)
        layout.addWidget(self.analyze_button, 8, 3)
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

        availability_index = self.availability_combo.findData(
            settings.squad_availability_mode
        )
        self.availability_combo.setCurrentIndex(
            availability_index if availability_index >= 0 else 0
        )
        self._update_availability_warning()

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

    def availability_mode(self):
        return self.availability_combo.currentData() or CURRENT_AVAILABLE

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
            t("match.select_players_csv"),
            self.players_csv_path(),
            "CSV files (*.csv);;All files (*.*)"
        )
        return path

    def set_players_loaded_count(self, count):
        self.players_loaded_label.setText(
            t("match.players_loaded", count=count)
        )

    def set_roster_players(self, players):
        self._roster_players = list(players or [])

    def set_processing(self, is_processing):
        self.analyze_button.setEnabled(
            not is_processing
        )
        self.analyze_button.setText(
            t("match.analyzing") if is_processing else t("match.analyze")
        )

        if is_processing:
            self.show_loading()

    def set_workspace_processing(self, is_processing):
        self.analyze_button.setEnabled(
            not is_processing
        )
        self.analyze_button.setText(
            t("match.updating") if is_processing else t("match.analyze")
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
            t("match.analysis_error_title"),
            message
        )

    def clear_results(self):
        self._clear_results_widgets()
        self._show_empty_results()

    def show_loading(self):
        self._state = "loading"
        self._clear_results_widgets()
        self._show_state_message(
            t("match.loading_title"),
            t("match.loading_message")
        )

    def show_results(self, result, restored=False, workspace_state=None):
        scroll_value = self.scroll_area.verticalScrollBar().value()
        self._state = "success"
        self._last_result = result
        self._last_restored = restored
        self._last_workspace_state = workspace_state
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

        if (
            getattr(result, "availability_warning", "")
            or getattr(result, "unavailable_players_count", 0)
        ):
            self.results_layout.addWidget(
                self._build_availability_panel(result)
            )

        if result.decision_lab is not None:
            self.results_layout.addWidget(
                self._build_decision_lab_panel(
                    result.decision_lab,
                    recommended,
                )
            )

        if getattr(result, "match_intelligence", None) is not None:
            self.results_layout.addWidget(
                self._build_match_intelligence_panel(
                    result.match_intelligence
                )
            )

        if result.change_analysis is not None:
            self.results_layout.addWidget(
                self._build_change_analysis_panel(
                    result.change_analysis
                )
            )

        if result.tactical_advisor:
            self.results_layout.addWidget(
                self._build_tactical_advisor_panel(
                    result.tactical_advisor
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
        self.show_status(t("match.updating_workspace"))

    def show_workspace_analysis_failed(self, message):
        self.show_status(t("match.analysis_failed", message=message))

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
            t("match.formation_board"),
        )
        tabs.addTab(
            self._build_comparison_table(result),
            t("match.comparison"),
        )

        recommended = result.recommended_formation
        if recommended is not None:
            tabs.addTab(
                self._build_lineup_table(recommended),
                t("match.detailed_xi"),
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

            title = QLabel(t("match.board_error_title"))
            title.setObjectName("sectionTitle")
            message = QLabel(
                t("match.board_error_message", error=exc)
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

        badge = QLabel(t("match.recommended"))
        badge.setObjectName("recommendedBadge")
        layout.addWidget(badge, 0, 0)

        title = QLabel(
            f"{formation.formation_name} - {formation.recommended_tactic}"
        )
        title.setObjectName("sectionTitle")
        layout.addWidget(title, 0, 1)

        values = [
            (t("match.tactic_level"), f"{formation.tactic_level:.2f}"),
            (t("match.win"), self._format_percent(formation.win_probability)),
            (t("match.draw"), self._format_percent(formation.draw_probability)),
            (t("match.loss"), self._format_percent(formation.loss_probability)),
            (t("match.possession"), self._format_percent(formation.possession)),
            (t("match.xg"), f"{formation.expected_goals:.2f}"),
            (t("match.opp_xg"), f"{formation.opponent_expected_goals:.2f}"),
        ]

        for index, (label, value) in enumerate(values):
            metric = QLabel(f"{label}  {value}")
            metric.setObjectName("compactMetric")
            layout.addWidget(metric, 0, index + 2)

        layout.setColumnStretch(1, 1)

        return card

    def _build_availability_panel(self, result):
        card = QFrame()
        card.setObjectName("metadataPanel")
        layout = QGridLayout(card)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(4)

        title = QLabel(t("match.availability_panel_title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title, 0, 0)
        layout.addWidget(
            QLabel(
                t(
                    "match.unavailable_players_count",
                    count=getattr(result, "unavailable_players_count", 0),
                )
            ),
            0,
            1,
        )
        warning = getattr(result, "availability_warning", "")
        if warning:
            warning_label = QLabel(warning)
            warning_label.setWordWrap(True)
            layout.addWidget(warning_label, 1, 0, 1, 2)
        return card

    def _build_match_intelligence_panel(self, intelligence):
        card = QFrame()
        card.setObjectName("compactDecisionLab")
        layout = QGridLayout(card)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(6)

        title = QLabel(t("match_intelligence.title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title, 0, 0, 1, 3)

        summary = QLabel(
            t(
                intelligence.summary_key,
                **self._localized_params(intelligence.summary_params),
            )
        )
        summary.setWordWrap(True)
        summary.setObjectName("compactDecisionText")
        layout.addWidget(summary, 1, 0, 1, 3)

        focuses = QWidget()
        focus_layout = QVBoxLayout(focuses)
        focus_layout.setContentsMargins(0, 0, 0, 0)
        focus_layout.setSpacing(2)
        focus_layout.addWidget(
            self._mini_heading(t("match_intelligence.focus.title"))
        )
        for focus in intelligence.tactical_focuses[:3]:
            label = QLabel(
                t(
                    focus.title_key,
                    **self._localized_params(focus.params),
                )
            )
            label.setObjectName("metadataValue")
            focus_layout.addWidget(label)
        layout.addWidget(focuses, 2, 0)

        profile = QWidget()
        profile_layout = QVBoxLayout(profile)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        profile_layout.setSpacing(2)
        profile_layout.addWidget(
            self._mini_heading(t("match_intelligence.profile.title"))
        )
        profile_layout.addWidget(
            QLabel(
                t(
                    "match_intelligence.profile.ours",
                    strongest=t(
                        f"match_intelligence.sector.{intelligence.our_profile.strongest_sector}"
                    ),
                    weakest=t(
                        f"match_intelligence.sector.{intelligence.our_profile.weakest_sector}"
                    ),
                )
            )
        )
        profile_layout.addWidget(
            QLabel(
                t(
                    "match_intelligence.profile.opponent",
                    strongest=t(
                        f"match_intelligence.sector.{intelligence.opponent_profile.strongest_sector}"
                    ),
                    weakest=t(
                        f"match_intelligence.sector.{intelligence.opponent_profile.weakest_sector}"
                    ),
                )
            )
        )
        layout.addWidget(profile, 2, 1)

        highlights = QWidget()
        highlights_layout = QVBoxLayout(highlights)
        highlights_layout.setContentsMargins(0, 0, 0, 0)
        highlights_layout.setSpacing(2)
        highlights_layout.addWidget(
            self._mini_heading(t("match_intelligence.highlights"))
        )
        for item in list(intelligence.opportunities[:1]) + list(intelligence.risks[:1]):
            highlights_layout.addWidget(
                QLabel(
                    t(
                        item.title_key,
                        **self._localized_params(item.params),
                    )
                )
            )
        layout.addWidget(highlights, 2, 2)

        matrix = self._build_matchup_matrix(intelligence.matrix)
        layout.addWidget(matrix, 3, 0, 1, 3)

        for column in range(3):
            layout.setColumnStretch(column, 1)
        return card

    def _build_matchup_matrix(self, matrix):
        table = QTableWidget(6, 5)
        table.setObjectName("comparisonTable")
        table.setHorizontalHeaderLabels(
            [
                t("match_intelligence.matrix.side"),
                t("match_intelligence.matrix.attack"),
                t("match_intelligence.matrix.defense"),
                t("match_intelligence.matrix.diff"),
                t("match_intelligence.matrix.classification"),
            ]
        )
        self._configure_table(table)
        table.setMinimumHeight(210)
        rows = [
            (t("match_intelligence.matrix.our_attack"), item)
            for item in matrix.our_attack_rows
        ] + [
            (t("match_intelligence.matrix.opponent_attack"), item)
            for item in matrix.opponent_attack_rows
        ]

        for row, (side, item) in enumerate(rows[:6]):
            marker = ""
            if item.is_best_route:
                marker = "+"
            elif item.is_worst_route:
                marker = "!"
            values = [
                side,
                t(f"match_intelligence.sector.{item.attack_sector}"),
                t(f"match_intelligence.sector.{item.defense_sector}"),
                f"{item.difference:+.0f}",
                f"{marker} {t(f'match_intelligence.classification.{item.classification.lower()}')}".strip(),
            ]
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))
        return table

    def _build_decision_lab_panel(self, decision_lab, recommended):
        card = QFrame()
        card.setObjectName("compactDecisionLab")
        layout = QGridLayout(card)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(3)

        title = QLabel(t("match.decision_lab"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title, 0, 0, 1, 3)

        confidence = QLabel(
            t(
                "match.recommendation_confidence",
                level=decision_lab.confidence.level,
            )
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
                t("match.play_to_win"),
                self._format_percent(recommended.win_probability),
                reason,
            ),
            (
                t("match.secure_draw"),
                self._format_percent(recommended.draw_probability),
                decision_lab.confidence.explanation,
            ),
            (
                t("match.avoid_defeat"),
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
            (t("match.opponent"), result.opponent_name),
            (t("match.formations"), str(len(result.analyzed_formations))),
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

        title = QLabel(t("match.formation_comparison"))
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
                t("match.formations"),
                t("match.tactic"),
                t("match.win_draw_loss"),
                t("match.possession"),
                t("match.xg"),
                t("match.opp_xg"),
                t("match.win_diff"),
                t("match.xg_diff"),
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

    def _build_change_analysis_panel(self, analysis):
        card = QFrame()
        card.setObjectName("compactDecisionLab")
        layout = QGridLayout(card)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(6)

        title = QLabel(t("change.title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title, 0, 0, 1, 4)

        last_change = QWidget()
        last_layout = QVBoxLayout(last_change)
        last_layout.setContentsMargins(0, 0, 0, 0)
        last_layout.setSpacing(2)
        last_layout.addWidget(self._mini_heading(t("change.last_change")))
        last_layout.addWidget(
            QLabel(
                f"{t('change.incoming_player')}: "
                f"{analysis.last_change.incoming_player}"
            )
        )
        last_layout.addWidget(
            QLabel(
                f"{t('change.outgoing_player')}: "
                f"{analysis.last_change.outgoing_player}"
            )
        )
        last_layout.addWidget(
            QLabel(
                f"{t('change.slot')}: {analysis.last_change.slot}"
            )
        )
        layout.addWidget(last_change, 1, 0)

        fit = QWidget()
        fit_layout = QVBoxLayout(fit)
        fit_layout.setContentsMargins(0, 0, 0, 0)
        fit_layout.setSpacing(2)
        fit_layout.addWidget(self._mini_heading(t("change.position_fit")))
        fit_layout.addWidget(
            QLabel(
                f"{t('change.previous_score')}: "
                f"{analysis.position_fit.previous_player_score:.2f}"
            )
        )
        fit_layout.addWidget(
            QLabel(
                f"{t('change.current_score')}: "
                f"{analysis.position_fit.current_player_score:.2f}"
            )
        )
        fit_layout.addWidget(
            QLabel(
                t(
                    "workspace.in_this_slot",
                    value=self._format_delta_number(
                        analysis.position_fit.difference
                    ),
                )
            )
        )
        layout.addWidget(fit, 1, 1)

        impact = QWidget()
        impact_layout = QVBoxLayout(impact)
        impact_layout.setContentsMargins(0, 0, 0, 0)
        impact_layout.setSpacing(2)
        impact_layout.addWidget(self._mini_heading(t("change.team_impact")))
        for change in analysis.team_impact:
            impact_layout.addWidget(
                QLabel(
                    f"{change.label}: "
                    f"{self._format_change_value(change.old_value, change.value_type)} "
                    f"-> {self._format_change_value(change.new_value, change.value_type)} "
                    f"({self._format_change_delta(change)})"
                )
            )
        layout.addWidget(impact, 1, 2)

        summary = QWidget()
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(2)
        summary_layout.addWidget(self._mini_heading(t("change.summary")))
        if analysis.summary is not None:
            headline = QLabel(t(analysis.summary.title_key))
            headline.setObjectName("metadataValue")
            summary_layout.addWidget(headline)
            detail = QLabel(t(analysis.summary.description_key))
            detail.setWordWrap(True)
            detail.setObjectName("compactDecisionText")
            summary_layout.addWidget(detail)
        layout.addWidget(summary, 1, 3)

        if analysis.sector_changes:
            sector_panel = QWidget()
            sector_layout = QVBoxLayout(sector_panel)
            sector_layout.setContentsMargins(0, 0, 0, 0)
            sector_layout.setSpacing(2)
            sector_layout.addWidget(
                self._mini_heading(t("change.sector_changes"))
            )
            for change in analysis.sector_changes:
                sector_layout.addWidget(
                    QLabel(
                        f"{change.label}: {change.old_value:.0f} -> "
                        f"{change.new_value:.0f} "
                        f"({self._format_delta_number(change.difference)})"
                    )
                )
            layout.addWidget(sector_panel, 2, 0, 1, 4)

        for column in range(4):
            layout.setColumnStretch(column, 1)

        return card

    def _build_tactical_advisor_panel(self, recommendations):
        card = QFrame()
        card.setObjectName("compactDecisionLab")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(6)

        title = QLabel(t("advisor.title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        for recommendation in recommendations[:5]:
            item = QFrame()
            item.setObjectName("metadataPanel")
            item_layout = QGridLayout(item)
            item_layout.setContentsMargins(8, 6, 8, 6)
            item_layout.setHorizontalSpacing(10)
            item_layout.setVerticalSpacing(3)

            impact = QLabel(self._advisor_badge_label(recommendation))
            impact.setObjectName("recommendedBadge")
            item_layout.addWidget(impact, 0, 0)

            heading = QLabel(
                t(
                    recommendation.title_key,
                    **self._localized_params(recommendation.params),
                )
            )
            heading.setObjectName("metadataValue")
            item_layout.addWidget(heading, 0, 1)

            if recommendation.is_action:
                estimate = QLabel(
                    t(
                        "advisor.estimated_win",
                        value=format_win_delta(
                            recommendation.estimated_win_delta
                        ),
                    )
                )
                estimate.setObjectName("compactMetric")
                item_layout.addWidget(estimate, 0, 2)

            meta = QLabel(
                "  |  ".join(
                    [
                        t(recommendation.category_key),
                        t(recommendation.confidence_key),
                    ]
                )
            )
            meta.setObjectName("compactDecisionText")
            item_layout.addWidget(meta, 1, 0)

            if self._advisor_verbosity == "detailed":
                explanation = QLabel(
                    t(
                        recommendation.explanation_key,
                        **self._localized_params(recommendation.params),
                    )
                )
                explanation.setWordWrap(True)
                explanation.setObjectName("compactDecisionText")
                item_layout.addWidget(explanation, 1, 1, 1, 2)

            item_layout.setColumnStretch(1, 1)
            layout.addWidget(item)

        return card

    def _build_lineup_table(self, formation):
        card = QFrame()
        card.setObjectName("resultCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(t("match.recommended_xi"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        table = QTableWidget(
            len(formation.lineup),
            6
        )
        table.setHorizontalHeaderLabels(
            [
                t("match.number"),
                t("match.side"),
                t("match.position"),
                t("match.player"),
                t("match.order"),
                t("match.order_side"),
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
            t("match.empty_title"),
            t("match.empty_message")
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

    def retranslate_ui(self):
        self.set_page_text(
            t("match.title"),
            t("match.subtitle"),
        )
        self.analysis_setup_title.setText(t("match.analysis_setup"))
        self.csv_label.setText(t("match.players_csv"))
        self.players_path_edit.setPlaceholderText(t("match.select_players_csv"))
        self.browse_button.setText(t("match.browse"))
        self.load_button.setText(t("match.load_players"))
        self.opponent_label.setText(t("match.opponent"))
        self.formation_label.setText(t("match.formations"))
        self.select_all_button.setText(t("match.select_all"))
        self.clear_all_button.setText(t("match.clear_all"))
        self.favorites_button.setText(t("match.favorites"))
        self.analyze_button.setText(t("match.analyze"))
        self._sync_analysis_setup_toggle()
        self._update_formation_warning()
        if self._state == "empty":
            self.clear_results()
        elif self._last_result is not None:
            self.show_results(
                self._last_result,
                restored=self._last_restored,
                workspace_state=self._last_workspace_state,
            )

    def set_advisor_verbosity(self, verbosity):
        self._advisor_verbosity = (
            verbosity if verbosity in {"simple", "detailed"} else "detailed"
        )
        if self._last_result is not None and self._state == "success":
            self.show_results(
                self._last_result,
                restored=self._last_restored,
                workspace_state=self._last_workspace_state,
            )

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

    def match_intelligence_rows(self, result):
        intelligence = getattr(result, "match_intelligence", None)
        if intelligence is None:
            return {}
        return {
            "formation": intelligence.formation_name,
            "focuses": [
                focus.code
                for focus in intelligence.tactical_focuses
            ],
            "opportunities": [
                item.code
                for item in intelligence.opportunities
            ],
            "risks": [
                item.code
                for item in intelligence.risks
            ],
            "our_attack_matrix": [
                (
                    item.attack_sector,
                    item.defense_sector,
                    item.classification,
                    item.is_best_route,
                    item.is_worst_route,
                )
                for item in intelligence.matrix.our_attack_rows
            ],
            "opponent_attack_matrix": [
                (
                    item.attack_sector,
                    item.defense_sector,
                    item.classification,
                    item.is_best_route,
                    item.is_worst_route,
                )
                for item in intelligence.matrix.opponent_attack_rows
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

    def _format_change_value(self, value, value_type):
        if value_type == "percent":
            return self._format_percent(value)
        return f"{value:.0f}"

    def _format_change_delta(self, change):
        if change.value_type == "percent":
            return self._format_delta_percent(change.difference)
        return self._format_delta_number(change.difference)

    def _advisor_badge_label(self, recommendation):
        if not recommendation.is_action:
            return t(recommendation.card_type_key)
        return t(f"advisor.impact.{impact_band(recommendation)}")

    def _localized_params(self, params):
        localized = {}
        for key, value in dict(params or {}).items():
            text = str(value)
            if text.startswith("{") and text.endswith("}"):
                localization_key = text[1:-1]
                localized[key] = t(localization_key)
                if localization_key.startswith("advisor.sector."):
                    sector_key = localization_key.rsplit(".", 1)[-1]
                    localized[f"{key}_with_article"] = t(
                        f"advisor.sector_article.{sector_key}"
                    )
                    localized[f"{key}_exposed"] = t(
                        f"advisor.sector_exposed.{sector_key}"
                    )
            else:
                localized[key] = value
        return localized

    @staticmethod
    def _mini_heading(text):
        label = QLabel(text)
        label.setObjectName("metadataValue")
        return label

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
        self._update_availability_warning()

        if not self._applying_settings:
            self.workspace_changed.emit()

    def _update_availability_warning(self):
        if not hasattr(self, "availability_warning_label"):
            return

        if self.availability_mode() == FULL_STRENGTH:
            self.availability_warning_label.setText(
                t("match.availability_full_strength_warning")
            )
        else:
            self.availability_warning_label.setText("")

    def _update_formation_warning(self):
        if not hasattr(self, "formation_warning_label"):
            return

        selected_count = len(self.selected_formations())

        if selected_count > 4:
            self.formation_warning_label.setText(
                t("match.many_formations")
            )
        else:
            self.formation_warning_label.setText("")

    def _sync_analysis_setup_toggle(self):
        if not hasattr(self, "analysis_setup_toggle"):
            return

        if self.analysis_inputs_expanded():
            self.analysis_setup_toggle.setText(t("match.hide_setup"))
            self.analysis_setup_toggle.setArrowType(Qt.DownArrow)
        else:
            self.analysis_setup_toggle.setText(t("match.show_setup"))
            self.analysis_setup_toggle.setArrowType(Qt.RightArrow)
