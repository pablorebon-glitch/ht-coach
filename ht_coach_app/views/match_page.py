from PySide6.QtCore import QDate, QEvent, QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from dataclasses import replace

from ht_coach_app.core.localization import t
from ht_coach_app.ui.design_system.collapsible_section import CollapsibleSection
from ht_coach_app.ui.design_system.empty_state import EmptyState
from ht_coach_app.ui.input_behavior import install_page_only_wheel_policy
from ht_coach_app.ui.responsive import (
    restore_splitter_geometry,
    splitter_ratios_from_sizes,
)
from ht_coach_app.ui.design_system.tables import configure_table
from engine.squad_health.availability_service import (
    CURRENT_AVAILABLE,
    FULL_STRENGTH,
)
from engine.advisor.recommendation_engine import (
    format_win_delta,
    impact_band,
)
from engine.ratings import format_rating_value
from ht_coach_app.core.localization import localization_service
from ht_coach_app.services.recent_csv_labels import format_recent_csv_label
from ht_coach_app.reasoning.explanation_formatter import (
    confidence_level_label,
    decision_lab_support_label,
    localized_confidence_explanation,
    localized_decision_reason,
    localized_decision_risk,
    localized_decision_summary,
)
from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.services.match_workspace_service import (
    MATCH_TYPE_CUP,
    MATCH_TYPE_LEAGUE,
)
from ht_coach_app.views.base_page import BasePage
from ht_coach_app.widgets.clickable_combo_box import ClickableComboBox
from ht_coach_app.widgets.formation_board.formation_board import FormationBoard


class MatchDateEdit(QDateEdit):
    _UNSET_DATE = QDate(1900, 1, 1)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._date_is_set = True
        self.setMinimumDate(self._UNSET_DATE)
        self.setSpecialValueText("-")
        self.setCalendarPopup(True)
        self.calendarWidget().installEventFilter(self)
        self.lineEdit().installEventFilter(self)
        self.dateChanged.connect(self._handle_date_changed)

    def setDate(self, date):
        self._date_is_set = date.isValid() and date != self._UNSET_DATE
        super().setDate(date)
        self.sync_calendar_page_to_selected_date()

    def clear_match_date(self):
        self._date_is_set = False
        super().setDate(self._UNSET_DATE)
        self.sync_calendar_page_to_selected_date()

    def match_date_text(self):
        if not self._date_is_set:
            return ""
        return self.date().toString("yyyy-MM-dd")

    def _handle_date_changed(self, date):
        self._date_is_set = date.isValid() and date != self._UNSET_DATE

    def mousePressEvent(self, event):
        self.sync_calendar_page_to_selected_date()
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            QTimer.singleShot(0, self.open_calendar_popup)
        else:
            super().mousePressEvent(event)
            QTimer.singleShot(0, self.sync_calendar_page_to_selected_date)

    def wheelEvent(self, event):
        event.ignore()

    def open_calendar_popup(self):
        self.sync_calendar_page_to_selected_date()
        calendar = self.calendarWidget()
        calendar.setWindowFlag(Qt.WindowType.Popup, True)
        calendar.move(self.mapToGlobal(self.rect().bottomLeft()))
        calendar.show()
        calendar.raise_()
        calendar.setFocus(Qt.FocusReason.MouseFocusReason)

    def eventFilter(self, watched, event):
        if watched is self.lineEdit() and event.type() in {
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonDblClick,
        }:
            if event.button() == Qt.MouseButton.LeftButton:
                event.accept()
                self.setFocus(Qt.FocusReason.MouseFocusReason)
                QTimer.singleShot(0, self.open_calendar_popup)
                return True
        if watched is self.calendarWidget() and event.type() == QEvent.Type.Show:
            self.sync_calendar_page_to_selected_date()
        return super().eventFilter(watched, event)

    def sync_calendar_page_to_selected_date(self):
        date = self.date()
        if date.isValid() and date != self._UNSET_DATE:
            self.calendarWidget().setCurrentPage(date.year(), date.month())


class MatchPage(BasePage):
    browse_players_requested = Signal()
    load_players_requested = Signal()
    analyze_requested = Signal()
    copy_summary_requested = Signal()
    copy_decision_lab_requested = Signal()
    copy_lineup_requested = Signal()
    workspace_recalculate_requested = Signal(object)
    workspace_changed = Signal()
    match_section_toggled = Signal(str, bool)
    save_as_first_match_requested = Signal()
    save_formation_requested = Signal()
    tactic_changed = Signal(str)
    team_attitude_changed = Signal(str)
    match_date_changed = Signal(str)
    save_as_second_match_requested = Signal()
    official_rating_import_requested = Signal(str)

    MATCH_SECTION_DEFAULTS = {
        "decision_lab": False,
        "match_intelligence": False,
        "rating_calibration": False,
        "match_analysis": True,
    }

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
        self._last_workspace_match_type = None
        self._advisor_verbosity = "detailed"
        self._analysis_inputs_collapsed = False
        self._editing_saved_match = False
        self._metadata_dirty = False
        self._analysis_stale = False
        self._match_section_states = dict(self.MATCH_SECTION_DEFAULTS)
        self._match_sections = {}
        self._match_section_body_roots = {}
        self._result_tabs = None
        self._formation_board_widget = None
        self._formation_board_tab_container = None
        self._pre_side_panel = None
        self._pre_status_label = None
        self._tactic_mismatch_label = None
        self._compact_ratings_container = None
        self._geometry_refresh_revision = 0
        install_page_only_wheel_policy()
        self.body_layout.setContentsMargins(16, 12, 16, 12)
        self.body_layout.setSpacing(8)
        self._build_scroll_content()
        self._build_inputs()
        self._build_results()

    def resizeEvent(self, event):
        viewport_state = (
            self._capture_viewport_state()
            if hasattr(self, "scroll_area")
            else None
        )
        super().resizeEvent(event)
        if hasattr(self, "scroll_area"):
            self._schedule_deferred_geometry_refresh(viewport_state)

    def changeEvent(self, event):
        super().changeEvent(event)
        if (
            event.type() == QEvent.Type.WindowStateChange
            and hasattr(self, "scroll_area")
        ):
            self._schedule_deferred_geometry_refresh()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "scroll_area"):
            self._schedule_deferred_geometry_refresh()

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
        self.players_path_edit.setVisible(False)
        self.players_path_edit.textChanged.connect(
            self._emit_workspace_changed
        )

        self.recent_csv_combo = QComboBox()
        self.recent_csv_combo.setMinimumWidth(160)
        self.recent_csv_combo.currentIndexChanged.connect(
            self._on_recent_csv_selected
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
        load_button.setVisible(False)

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
        self.opponent_combo = ClickableComboBox()
        self.opponent_combo.setEditable(True)
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

        match_type_label = QLabel(t("match.match_type"))
        self.match_type_label = match_type_label
        self.match_type_combo = QComboBox()
        self.match_type_combo.addItem(
            t("match.match_type_select"),
            "",
        )
        self.match_type_combo.addItem(
            t("match.match_type_league"),
            MATCH_TYPE_LEAGUE,
        )
        self.match_type_combo.addItem(
            t("match.match_type_cup"),
            MATCH_TYPE_CUP,
        )
        self.match_type_combo.currentIndexChanged.connect(
            self._emit_workspace_changed
        )

        match_date_label = QLabel(t("match.match_date"))
        self.match_date_label = match_date_label
        self.match_date_edit = MatchDateEdit()
        self.match_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.match_date_edit.setDate(self._default_match_qdate())
        self.match_date_edit.dateChanged.connect(
            self._emit_workspace_changed
        )
        self.match_date_edit.dateChanged.connect(
            self._emit_match_date_changed
        )

        self.season_preview_label = QLabel("")
        self.season_preview_label.setWordWrap(True)
        self.season_preview_label.setObjectName("compactDecisionText")

        venue_role_label = QLabel(t("match.venue_role"))
        self.venue_role_label = venue_role_label
        self.venue_role_combo = QComboBox()
        self.venue_role_combo.addItem(t("match.venue_role_home"), "home")
        self.venue_role_combo.addItem(t("match.venue_role_away"), "away")
        self.venue_role_combo.addItem(t("match.venue_role_neutral"), "neutral")
        self.venue_role_combo.addItem(t("match.venue_role_unknown"), "unknown")
        self.venue_role_combo.setCurrentIndex(3)
        self.venue_role_combo.currentIndexChanged.connect(
            self._emit_workspace_changed
        )

        self.training_conflict_label = QLabel("")
        self.training_conflict_label.setWordWrap(True)
        self.training_conflict_label.setProperty(
            "state",
            "warning"
        )
        self.training_conflict_label.setVisible(False)

        self.training_context_label = QLabel("")
        self.training_context_label.setWordWrap(True)
        self.training_context_label.setObjectName("compactDecisionText")
        self.training_context_label.setVisible(False)

        self.metadata_evidence_warning_label = QLabel("")
        self.metadata_evidence_warning_label.setWordWrap(True)
        self.metadata_evidence_warning_label.setProperty(
            "state",
            "warning"
        )
        self.metadata_evidence_warning_label.setVisible(False)

        self.status_label = QLabel(t("match.ready"))
        self.status_label.setWordWrap(True)

        self.analyze_button = QPushButton(t("match.analyze"))
        self.analyze_button.setObjectName("primaryAction")
        self.analyze_button.clicked.connect(
            self.analyze_requested
        )

        self.official_import_button = QPushButton(
            t("match.official_import.action")
        )
        self.official_import_button.clicked.connect(
            self._open_official_import_dialog
        )
        self.save_metadata_button = QPushButton(t("match.save_changes"))
        self.save_metadata_button.clicked.connect(self.save_formation_requested)
        self.save_metadata_button.setVisible(False)

        layout.addWidget(csv_label, 0, 0)
        layout.addWidget(self.recent_csv_combo, 0, 1)
        layout.addWidget(self.players_path_edit, 0, 1)
        layout.addWidget(browse_button, 0, 2)
        layout.addWidget(load_button, 0, 3)
        layout.addWidget(self.players_loaded_label, 1, 1, 1, 3)
        layout.addWidget(availability_label, 2, 0)
        layout.addWidget(self.availability_combo, 2, 1, 1, 3)
        layout.addWidget(self.availability_warning_label, 3, 1, 1, 3)
        layout.addWidget(opponent_label, 4, 0)
        layout.addWidget(self.opponent_combo, 4, 1, 1, 3)
        layout.addWidget(match_type_label, 5, 0)
        layout.addWidget(self.match_type_combo, 5, 1, 1, 3)
        layout.addWidget(venue_role_label, 6, 0)
        layout.addWidget(self.venue_role_combo, 6, 1, 1, 3)
        layout.addWidget(match_date_label, 7, 0)
        layout.addWidget(self.match_date_edit, 7, 1, 1, 3)
        layout.addWidget(self.season_preview_label, 8, 1, 1, 3)
        layout.addWidget(formation_label, 9, 0)
        layout.addWidget(self.formations_container, 9, 1, 1, 3)
        layout.addWidget(formation_actions_widget, 10, 1, 1, 3)
        layout.addWidget(self.formation_warning_label, 11, 1, 1, 3)
        layout.addWidget(self.training_conflict_label, 12, 1, 1, 3)
        layout.addWidget(self.training_context_label, 13, 1, 1, 3)
        layout.addWidget(self.metadata_evidence_warning_label, 14, 1, 1, 3)
        layout.addWidget(self.status_label, 15, 0, 1, 2)
        layout.addWidget(self.save_metadata_button, 15, 2)
        layout.addWidget(self.analyze_button, 15, 3)
        layout.setColumnStretch(1, 1)

        setup_layout.addWidget(self.analysis_inputs_panel)
        self.match_content_layout.addWidget(self.analysis_setup_panel, 0)
        self._sync_analysis_setup_toggle()
        self._update_analyze_button_state()

    @staticmethod
    def _default_match_qdate():
        try:
            from ht_coach_app.services.ht_week_context_provider import get_calendar_service

            current = get_calendar_service().now().date()
            return QDate(current.year, current.month, current.day)
        except Exception:
            return QDate.currentDate()

    def _build_results(self):
        self.results_host = QWidget()
        self.results_layout = QVBoxLayout(
            self.results_host
        )
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(6)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._show_empty_results()
        self.match_content_layout.addWidget(self.results_host, 0)

    def set_opponents(self, opponent_names, selected_name=None):
        current = (
            self.selected_opponent_name()
            if selected_name is None
            else selected_name
        )
        names = list(opponent_names or [])
        saved_snapshot_name = current if current and current not in names else ""
        self.opponent_combo.blockSignals(True)
        self.opponent_combo.clear()
        self.opponent_combo.addItem("", None)

        for name in names:
            self.opponent_combo.addItem(
                name,
                {
                    "opponent_id": name,
                    "opponent_name": name,
                    "source": "OPPONENT_MANAGER",
                },
            )
        if saved_snapshot_name:
            self.opponent_combo.addItem(
                t(
                    "match.saved_opponent_missing_label",
                    opponent=saved_snapshot_name,
                ),
                {
                    "opponent_id": saved_snapshot_name,
                    "opponent_name": saved_snapshot_name,
                    "source": "SAVED_MATCH_SNAPSHOT",
                },
            )

        index = self._find_opponent_index_by_name(current)
        if index >= 0:
            self.opponent_combo.setCurrentIndex(index)
        else:
            self.opponent_combo.setCurrentIndex(0)

        self.opponent_combo.blockSignals(False)

    def _find_opponent_index_by_name(self, opponent_name):
        for index in range(self.opponent_combo.count()):
            data = self.opponent_combo.itemData(index)
            if isinstance(data, dict) and data.get("opponent_name") == opponent_name:
                return index
            if self.opponent_combo.itemText(index) == opponent_name:
                return index
        return -1

    def enter_saved_match_edit_mode(self, title=None):
        self._editing_saved_match = True
        self._metadata_dirty = False
        self.analysis_setup_title.setText(title or t("match.editing_saved_match"))
        self.expand_analysis_inputs()
        self._update_save_action_labels()

    def exit_saved_match_edit_mode(self):
        self._editing_saved_match = False
        self._metadata_dirty = False
        self.analysis_setup_title.setText(t("match.analysis_setup"))
        self.set_metadata_evidence_warning("")
        self._update_save_action_labels()

    def clear_metadata_dirty(self):
        self._metadata_dirty = False
        self._update_save_action_labels()

    def set_metadata_evidence_warning(self, message):
        text = (message or "").strip()
        self.metadata_evidence_warning_label.setText(text)
        self.metadata_evidence_warning_label.setVisible(bool(text))

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
        self._update_analyze_button_state()

    def apply_settings(self, settings):
        self._applying_settings = True
        self.players_path_edit.setText(
            settings.players_csv_path
        )
        if hasattr(self, "recent_csv_combo"):
            self.set_recent_csv_paths(
                getattr(settings, "recent_players_csv_paths", ())
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
        self.set_match_section_states(
            getattr(settings, "match_section_states", {})
        )

        self._applying_settings = False
        self._update_formation_warning()
        self._update_analyze_button_state()

    def players_csv_path(self):
        return self.players_path_edit.text().strip()

    def set_players_csv_path(self, path):
        self.players_path_edit.setText(path)
        filename = path.split("\\")[-1].split("/")[-1] if path else ""
        self.set_source_indicator(filename, "neutral")

    def set_recent_csv_paths(self, paths):
        self.recent_csv_combo.blockSignals(True)
        self.recent_csv_combo.clear()
        if not paths:
            self.recent_csv_combo.addItem(
                t("match.select_players_csv"), ""
            )
        for path in paths or ():
            self.recent_csv_combo.addItem(
                format_recent_csv_label(
                    path, language=localization_service().language
                ),
                path,
            )
        current = self.players_csv_path()
        index = self.recent_csv_combo.findData(current)
        self.recent_csv_combo.setCurrentIndex(index if index >= 0 else 0)
        self.recent_csv_combo.blockSignals(False)

    def _on_recent_csv_selected(self, _index):
        path = self.recent_csv_combo.currentData()
        if not path or path == self.players_csv_path():
            return
        self.set_players_csv_path(path)
        self.load_players_requested.emit()

    def selected_opponent_name(self):
        data = self.opponent_combo.currentData()
        if (
            isinstance(data, dict)
            and self.opponent_combo.currentIndex() >= 0
            and self.opponent_combo.currentText() == self.opponent_combo.itemText(
                self.opponent_combo.currentIndex()
            )
        ):
            return (data.get("opponent_name") or "").strip()
        return self.opponent_combo.currentText().strip()

    def selected_opponent_identity(self):
        data = self.opponent_combo.currentData()
        if (
            isinstance(data, dict)
            and self.opponent_combo.currentIndex() >= 0
            and self.opponent_combo.currentText() == self.opponent_combo.itemText(
                self.opponent_combo.currentIndex()
            )
        ):
            return dict(data)
        name = self.selected_opponent_name()
        if not name:
            return {}
        return {
            "opponent_id": name,
            "opponent_name": name,
            "source": "MANUAL_TEXT",
        }

    def selected_formations(self):
        return [
            name for name, checkbox in self._formation_checks.items()
            if checkbox.isChecked()
        ]

    def availability_mode(self):
        return self.availability_combo.currentData() or CURRENT_AVAILABLE

    def match_type(self):
        return self.match_type_combo.currentData()

    def set_match_type(self, match_type):
        index = self.match_type_combo.findData(match_type)
        if index >= 0:
            self.match_type_combo.setCurrentIndex(index)

    def set_analysis_stale(self, stale, message=""):
        self._analysis_stale = bool(stale)
        self._update_save_action_labels()
        if self._analysis_stale and message:
            self.show_error(message)

    def match_date(self):
        if hasattr(self.match_date_edit, "match_date_text"):
            return self.match_date_edit.match_date_text()
        return self.match_date_edit.date().toString("yyyy-MM-dd")

    def set_match_date(self, iso_date_text):
        if not iso_date_text:
            return
        qdate = QDate.fromString(iso_date_text[:10], "yyyy-MM-dd")
        if qdate.isValid():
            self.match_date_edit.setDate(qdate)

    def clear_match_date(self):
        if hasattr(self.match_date_edit, "clear_match_date"):
            self.match_date_edit.clear_match_date()

    def reset_match_date_for_new_match(self):
        self.match_date_edit.setDate(self._default_match_qdate())

    def _emit_match_date_changed(self, _qdate):
        self.match_date_changed.emit(self.match_date())

    def set_season_preview(self, text):
        """Alpha 0.6.7 HF-02, Part 14: after picking a date, preview
        "Temporada HT 95 · Semana 2" -- or the honest "Temporada HT:
        sin configurar" when no season calendar has been set up yet.
        Never blocks match creation either way."""
        self.season_preview_label.setText(text or "")

    def venue_role(self):
        return self.venue_role_combo.currentData() or "unknown"

    def set_venue_role(self, venue_role):
        index = self.venue_role_combo.findData(venue_role)
        if index >= 0:
            self.venue_role_combo.setCurrentIndex(index)

    def tactic(self):
        board = self._formation_board_widget
        if board is None:
            return ""
        return board.tactic_combo.currentData() or ""

    def set_tactic(self, tactic):
        board = self._formation_board_widget
        if board is None or not tactic:
            return
        index = board.tactic_combo.findData(tactic)
        if index >= 0:
            blocker = QSignalBlocker(board.tactic_combo)
            board.tactic_combo.setCurrentIndex(index)
            del blocker

    def team_attitude(self):
        board = self._formation_board_widget
        if board is None:
            return ""
        return board.team_attitude_combo.currentData() or ""

    def set_team_attitude(self, attitude):
        board = self._formation_board_widget
        if board is None or not attitude:
            return
        index = board.team_attitude_combo.findData(attitude)
        if index >= 0:
            blocker = QSignalBlocker(board.team_attitude_combo)
            board.team_attitude_combo.setCurrentIndex(index)
            del blocker

    def is_workspace_dirty(self):
        """Alpha 0.6.7 HF-03, Part 12: whether the currently open
        formation has unsaved changes."""
        board = self._formation_board_widget
        return self._metadata_dirty or (board is not None and board.is_dirty())

    def is_metadata_dirty(self):
        return self._metadata_dirty

    def current_workspace_state(self):
        board = self._formation_board_widget
        if board is None:
            return None
        return board.workspace_state()

    def set_training_conflict_warning(self, message):
        text = (message or "").strip()
        self.training_conflict_label.setText(text)
        self.training_conflict_label.setVisible(bool(text))

    def set_training_context_summary(self, message, stale=False):
        text = (message or "").strip()
        self.training_context_label.setText(text)
        self.training_context_label.setProperty(
            "state",
            "warning" if stale else "",
        )
        self.training_context_label.style().unpolish(self.training_context_label)
        self.training_context_label.style().polish(self.training_context_label)
        self.training_context_label.setVisible(bool(text))

    def confirm_unsaved_changes(self):
        """Alpha 0.6.7 HF-03, Part 12: when leaving or switching a
        dirty Match workspace, the person must explicitly choose --
        never a silent loss or an implicit transfer of changes onto a
        different record."""
        from PySide6.QtWidgets import QMessageBox

        box = QMessageBox(self)
        box.setWindowTitle(t("match.unsaved_changes.title"))
        box.setText(t("match.unsaved_changes.message"))
        cancel_button = box.addButton(t("match.unsaved_changes.cancel"), QMessageBox.RejectRole)
        discard_button = box.addButton(
            t("match.unsaved_changes.discard"), QMessageBox.DestructiveRole
        )
        save_button = box.addButton(
            t("match.unsaved_changes.save"), QMessageBox.AcceptRole
        )
        box.setDefaultButton(cancel_button)
        box.exec()
        clicked = box.clickedButton()
        if clicked is save_button:
            return "save"
        if clicked is discard_button:
            return "discard"
        return "cancel"

    def confirm_replace_first_match(self, week_start_text="", week_end_text=""):
        """Alpha 0.6.7 HF-02, Part 3: names the *actual* training cycle
        that already has a Match 1 -- never assumes it's the current
        week just because the confirmation happened today."""
        message = (
            t(
                "planner.replace_first_match_confirm_dated",
                start=week_start_text, end=week_end_text,
            )
            if week_start_text and week_end_text
            else t("planner.replace_first_match_confirm")
        )
        return QMessageBox.question(
            self,
            t("planner.replace_first_match"),
            message,
        ) == QMessageBox.Yes

    def confirm_replace_second_match(self, week_start_text="", week_end_text=""):
        message = (
            t(
                "planner.replace_second_match_confirm_dated",
                start=week_start_text, end=week_end_text,
            )
            if week_start_text and week_end_text
            else t("planner.replace_second_match_confirm")
        )
        return QMessageBox.question(
            self,
            t("planner.replace_second_match"),
            message,
        ) == QMessageBox.Yes

    def confirm_save_match_type_mismatch(self, expected_label, actual_label):
        return QMessageBox.question(
            self,
            t("match.save_type_mismatch_title"),
            t(
                "match.save_type_mismatch_confirm",
                expected=expected_label,
                actual=actual_label,
            ),
        ) == QMessageBox.Yes

    def _open_official_import_dialog(self):
        from ht_coach_app.widgets.official_rating_import_dialog import (
            OfficialRatingImportDialog,
        )

        text = OfficialRatingImportDialog.request_text(self)
        if text:
            self.official_rating_import_requested.emit(text)

    def confirm_official_import_replace(self, slot):
        key = (
            "match.official_import.confirm_replace_pre"
            if slot == "pre"
            else "match.official_import.confirm_replace_post"
        )
        return QMessageBox.question(
            self,
            t("match.official_import.confirm_replace_title"),
            t(key),
        ) == QMessageBox.Yes

    def confirm_metadata_evidence_save(self):
        return QMessageBox.question(
            self,
            t("match.metadata_evidence_confirm_title"),
            t("match.metadata_evidence_confirm_message"),
        ) == QMessageBox.Yes

    def confirm_ambiguous_official_import(self, candidate_count):
        QMessageBox.warning(
            self,
            t("match.official_import.error_title"),
            t("match.official_import.error.ambiguous_match"),
        )

    def show_official_import_error(self, message):
        QMessageBox.warning(
            self, t("match.official_import.error_title"), message
        )

    def show_official_import_success(self):
        """Per this sprint's guardrail: Match shows only a simple
        confirmation after a successful official-summary import --
        ratings, metadata, timestamps and comparisons all moved to the
        dedicated Match Intelligence page."""
        QMessageBox.information(
            self,
            t("match.official_import.action"),
            t("match.official_import.success"),
        )

    def show_existing_match_dialog(self):
        """Alpha 0.6.7, Part 5's own dialog, word-for-word."""
        answer = QMessageBox.question(
            self,
            t("match.existing_match.title"),
            t("match.existing_match.message"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return answer == QMessageBox.Yes

    def show_match_conflict_dialog(self, opponent_name, existing_competition, new_competition):
        """Alpha 0.6.7, Part 6's own dialog, word-for-word -- three
        explicit choices, never a silent duplicate."""
        box = QMessageBox(self)
        box.setWindowTitle(t("match.conflict.title"))
        box.setText(
            t(
                "match.conflict.message",
                opponent=opponent_name,
                existing_competition=existing_competition,
                new_competition=new_competition,
            )
        )
        cancel_button = box.addButton(t("match.conflict.cancel"), QMessageBox.RejectRole)
        correct_button = box.addButton(t("match.conflict.correct"), QMessageBox.ActionRole)
        create_button = box.addButton(t("match.conflict.create_new"), QMessageBox.AcceptRole)
        box.setDefaultButton(cancel_button)
        box.exec()
        clicked = box.clickedButton()
        if clicked is correct_button:
            return "correct"
        if clicked is create_button:
            return "create_new"
        return "cancel"

    def reset_new_match_selectors(self):
        """Part 5's "No" behavior: reset rival/type/date selectors to
        blank, never modifying any saved record."""
        if hasattr(self, "opponent_combo"):
            self.opponent_combo.setCurrentIndex(-1)

    def reset_new_match_workspace(self):
        self.exit_saved_match_edit_mode()
        self.reset_new_match_selectors()
        self.reset_match_date_for_new_match()
        if hasattr(self, "set_match_type"):
            self.set_match_type("")
        if hasattr(self, "set_venue_role"):
            self.set_venue_role("unknown")
        self.clear_metadata_dirty()
        self.set_analysis_stale(False)
        self.clear_results()
        self.expand_analysis_inputs()

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
        self._update_analyze_button_state()

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
            (not is_processing) and self._can_analyze()
        )
        self.analyze_button.setText(
            t("match.analyzing") if is_processing else t("match.analyze")
        )

        if is_processing:
            self.show_loading()

    def set_workspace_processing(self, is_processing):
        self.analyze_button.setEnabled(
            (not is_processing) and self._can_analyze()
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
        self._state = "empty"
        self._last_result = None
        self._last_restored = False
        self._last_workspace_state = None
        self._last_workspace_match_type = None
        self._clear_results_widgets()
        self._show_empty_results()

    def show_loading(self):
        self._state = "loading"
        self._clear_results_widgets()
        self._show_state_message(
            t("match.loading_title"),
            t("match.loading_message")
        )
        self._stabilize_match_results_layout()

    def show_results(self, result, restored=False, workspace_state=None):
        result = self._with_stable_recommendation_flags(result)
        viewport_state = self._capture_viewport_state()
        self._state = "success"
        self._last_result = result
        self._last_restored = restored
        self._last_workspace_state = workspace_state
        self._last_workspace_match_type = getattr(result, "match_type", None)
        self.set_analysis_stale(False)
        self._clear_results_widgets()
        self.collapse_analysis_inputs()
        recommended = result.recommended_formation
        sections = self._ensure_match_sections()
        self._update_match_sections(
            result,
            recommended,
            restored,
            workspace_state,
        )
        for key in (
            "decision_lab",
            "match_intelligence",
            "rating_calibration",
            "match_analysis",
        ):
            self.results_layout.addWidget(sections[key])
        self.results_layout.addWidget(
            self._build_result_tabs(
                result,
                restored=restored,
                workspace_state=workspace_state,
            )
        )
        self.results_layout.addStretch(1)
        self._restore_viewport_state(
            viewport_state,
            self._result_tabs,
        )
        self._stabilize_match_results_layout()

    def set_match_section_states(self, states):
        for key, default in self.MATCH_SECTION_DEFAULTS.items():
            if key in dict(states or {}):
                self._match_section_states[key] = bool(states[key])
            else:
                self._match_section_states.setdefault(key, default)
        for key, section in self._match_sections.items():
            section.set_expanded(
                self._match_section_states.get(
                    key,
                    self.MATCH_SECTION_DEFAULTS.get(key, True),
                ),
                emit=False,
            )

    def match_section_states(self):
        return dict(self._match_section_states)

    def _ensure_match_sections(self):
        titles = {
            "decision_lab": t("match.decision_lab"),
            "match_intelligence": t("match_intelligence.title"),
            "rating_calibration": t("sector_rating.title"),
            "match_analysis": t("match.match_analysis"),
        }
        for key, title in titles.items():
            if key in self._match_sections:
                continue
            section = CollapsibleSection(
                title,
                state_key=key,
                expanded=self._match_section_states.get(
                    key,
                    self.MATCH_SECTION_DEFAULTS[key],
                ),
            )
            section.toggled.connect(self._match_section_toggled)
            self._match_sections[key] = section
            if key in {
                "decision_lab",
                "match_intelligence",
                "rating_calibration",
            }:
                section.set_body_widget(
                    self._section_body_root(key)
                )
        return self._match_sections

    def _match_section_toggled(self, key, expanded):
        viewport_state = self._capture_viewport_state()
        self._match_section_states[key] = expanded
        self.match_section_toggled.emit(key, expanded)
        self._stabilize_match_results_layout(viewport_state)

    def _stabilize_match_results_layout(self, viewport_state=None):
        self.results_layout.invalidate()
        self.match_content_layout.invalidate()
        self.results_host.updateGeometry()
        self.match_content.updateGeometry()
        if viewport_state is not None:
            self._restore_viewport_state(
                viewport_state,
                self._result_tabs,
            )

    def _update_match_sections(
        self,
        result,
        recommended,
        restored,
        workspace_state,
    ):
        sections = self._ensure_match_sections()

        self._set_section_body_content(
            "decision_lab",
            self._build_decision_lab_panel(
                result.decision_lab,
                recommended,
            )
            if result.decision_lab is not None
            else self._build_unavailable_panel(
                t("decision_lab.copy.empty")
            )
        )
        sections["decision_lab"].set_summary(
            self._decision_lab_summary(result)
        )

        intelligence = getattr(result, "match_intelligence", None)
        self._set_section_body_content(
            "match_intelligence",
            self._bounded_section_scroll(
                self._build_match_intelligence_panel(
                    intelligence,
                    recommended,
                )
                if intelligence is not None
                else self._build_unavailable_panel(
                    t("common.not_available")
                ),
                "matchIntelligenceBodyScroll",
                minimum_height=220,
                maximum_height=380,
            )
        )
        sections["match_intelligence"].set_summary(
            self._match_intelligence_summary(result)
        )

        self._set_section_body_content(
            "rating_calibration",
            self._bounded_section_scroll(
                self._build_sector_rating_panel(recommended, intelligence)
                if recommended is not None and getattr(
                    recommended,
                    "sector_rating_comparisons",
                    None,
                )
                else self._build_unavailable_panel(
                    t("sector_rating.not_available")
                ),
                "ratingCalibrationBodyScroll",
                minimum_height=170,
                maximum_height=340,
            )
        )
        sections["rating_calibration"].set_summary(
            self._rating_calibration_summary(recommended)
        )

        sections["match_analysis"].set_body_widget(
            self._build_match_analysis_body(
                result,
                recommended,
                restored,
                workspace_state,
            )
        )
        sections["match_analysis"].set_summary(
            self._match_analysis_summary(result)
        )

    def _section_body_root(self, key):
        if key in self._match_section_body_roots:
            return self._match_section_body_roots[key]
        root = QWidget()
        root.setObjectName(f"{key}BodyRoot")
        root.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred,
        )
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._match_section_body_roots[key] = root
        return root

    def _set_section_body_content(self, key, content):
        root = self._section_body_root(key)
        layout = root.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not content:
                widget.setParent(None)
                widget.deleteLater()
        layout.addWidget(content)
        content.show()
        root.show()
        layout.invalidate()
        root.updateGeometry()

    def _bounded_section_scroll(
        self,
        content,
        object_name,
        minimum_height,
        maximum_height,
    ):
        scroll = QScrollArea()
        scroll.setObjectName(object_name)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(minimum_height)
        scroll.setMaximumHeight(maximum_height)
        scroll.setWidget(content)
        return scroll

    def _build_match_analysis_body(
        self,
        result,
        recommended,
        restored,
        workspace_state,
    ):
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._build_analysis_context(result))

        if recommended is not None:
            layout.addWidget(self._build_recommended_summary(recommended))

        if (
            getattr(result, "availability_warning", "")
            or getattr(result, "unavailable_players_count", 0)
        ):
            layout.addWidget(self._build_availability_panel(result))

        if result.change_analysis is not None:
            layout.addWidget(
                self._build_change_analysis_panel(result.change_analysis)
            )

        if result.tactical_advisor:
            layout.addWidget(
                self._build_tactical_advisor_panel(result.tactical_advisor)
            )

        return body

    def _build_unavailable_panel(self, message):
        panel = QFrame()
        panel.setObjectName("metadataPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 7, 10, 7)
        label = QLabel(message)
        label.setObjectName("compactDecisionText")
        label.setWordWrap(True)
        layout.addWidget(label)
        return panel

    def _decision_lab_summary(self, result):
        decision_lab = getattr(result, "decision_lab", None)
        result_recommended = getattr(result, "recommended_formation", None)
        if result_recommended is not None:
            return t(
                "match.section_summary.recommended",
                formation=result_recommended.formation_name,
            )
        if decision_lab is None:
            return t("common.not_available")
        recommended = getattr(decision_lab, "recommended_formation", None)
        formation = getattr(recommended, "formation", "") or ""
        if formation:
            return t("match.section_summary.recommended", formation=formation)
        return localized_decision_summary(decision_lab.summary)

    def _match_intelligence_summary(self, result):
        intelligence = getattr(result, "match_intelligence", None)
        if intelligence is None:
            return t("common.not_available")
        return self._short_text(
            t(
                intelligence.summary_key,
                **self._localized_params(intelligence.summary_params),
            ),
            limit=72,
        )

    def _rating_calibration_summary(self, formation):
        if formation is None or not getattr(
            formation,
            "sector_rating_comparisons",
            None,
        ):
            return t("match.section_summary.calibration_unavailable")
        if self._sector_ratings_comparable(formation):
            return t("match.section_summary.calibration_comparable")
        return t("match.section_summary.calibration_limited")

    def _match_analysis_summary(self, result):
        recommended = getattr(result, "recommended_formation", None)
        if recommended is None:
            return t("match.section_summary.lineup_analyzed")
        return t(
            "match.section_summary.analysis_ready",
            formation=recommended.formation_name,
        )

    def _capture_viewport_state(self):
        result_tabs = self.findChild(QTabWidget, "matchResultTabs")
        current_board = self.findChild(FormationBoard)
        focus_widget = QApplication.focusWidget()
        splitter_sizes = (
            current_board.splitter.sizes()
            if current_board is not None
            else []
        )
        return {
            "vertical_scroll": self.scroll_area.verticalScrollBar().value(),
            "vertical_scroll_ratio": self._scroll_ratio(
                self.scroll_area.verticalScrollBar()
            ),
            "horizontal_scroll": self.scroll_area.horizontalScrollBar().value(),
            "formation_splitter_sizes": splitter_sizes,
            "formation_splitter_ratios": splitter_ratios_from_sizes(
                splitter_sizes
            ),
            "viewport_width": self.scroll_area.viewport().width(),
            "result_tab_index": (
                result_tabs.currentIndex()
                if result_tabs is not None
                else 0
            ),
            "selected_player_id": (
                current_board.current_board().selected_player_id
                if current_board is not None
                and current_board.current_board() is not None
                else ""
            ),
            "focused_object_name": (
                focus_widget.objectName()
                if focus_widget is not None
                else ""
            ),
        }

    def _restore_viewport_state(self, viewport_state, result_tabs):
        if result_tabs is not None:
            index = min(
                max(int(viewport_state.get("result_tab_index", 0)), 0),
                max(result_tabs.count() - 1, 0),
            )
            result_tabs.setCurrentIndex(index)
        current_board = self.findChild(FormationBoard)
        splitter_sizes = viewport_state.get("formation_splitter_sizes") or []
        splitter_ratios = viewport_state.get("formation_splitter_ratios") or []
        source_width = int(viewport_state.get("viewport_width", 0) or 0)
        target_width = self.scroll_area.viewport().width()
        if current_board is not None and splitter_sizes:
            restore_splitter_geometry(
                current_board.splitter,
                splitter_sizes,
                splitter_ratios,
                source_width,
                target_width,
            )

        def restore_scrollbars():
            vertical = self.scroll_area.verticalScrollBar()
            current_target_width = self.scroll_area.viewport().width()
            target = int(viewport_state.get("vertical_scroll", 0))
            if abs(current_target_width - source_width) > 8:
                ratio_target = int(
                    vertical.maximum()
                    * float(viewport_state.get("vertical_scroll_ratio", 0.0))
                )
                target = min(target, ratio_target)
            vertical.setValue(max(0, min(target, vertical.maximum())))
            self.scroll_area.horizontalScrollBar().setValue(
                int(viewport_state.get("horizontal_scroll", 0))
            )
            if current_board is not None and splitter_sizes:
                restore_splitter_geometry(
                    current_board.splitter,
                    splitter_sizes,
                    splitter_ratios,
                    source_width,
                    self.scroll_area.viewport().width(),
                )

        restore_scrollbars()
        QTimer.singleShot(0, restore_scrollbars)
        QTimer.singleShot(25, restore_scrollbars)

    def _schedule_deferred_geometry_refresh(self, viewport_state=None):
        self._geometry_refresh_revision += 1
        revision = self._geometry_refresh_revision
        viewport_state = viewport_state or self._capture_viewport_state()

        def refresh():
            if revision != self._geometry_refresh_revision:
                return
            self._refresh_current_geometry(viewport_state)

        QTimer.singleShot(0, refresh)

    def _refresh_current_geometry(self, viewport_state):
        if self._state != "success":
            return
        self.results_layout.invalidate()
        for section in self._match_sections.values():
            if section.is_expanded():
                body = section.body_widget()
                if body is not None and body.layout() is not None:
                    body.layout().invalidate()
                section.updateGeometry()
        self.match_content_layout.invalidate()
        self.results_host.updateGeometry()
        self.match_content.updateGeometry()
        self._restore_viewport_state(
            viewport_state,
            self._result_tabs,
        )

    @staticmethod
    def _scroll_ratio(scrollbar):
        maximum = scrollbar.maximum()
        if maximum <= 0:
            return 0.0
        return scrollbar.value() / maximum

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
        tabs = self._result_tabs
        if tabs is None:
            tabs = QTabWidget()
            tabs.setObjectName("matchResultTabs")
            tabs.setDocumentMode(True)
            tabs.setMinimumHeight(420)
            self._result_tabs = tabs

        self._set_result_tab(
            tabs,
            0,
            self._build_formation_board_tab(
                result,
                restored,
                workspace_state=workspace_state,
            ),
            t("match.formation_board"),
        )
        self._set_result_tab(
            tabs,
            1,
            self._build_comparison_table(result),
            t("match.comparison"),
        )

        recommended = result.recommended_formation
        if recommended is not None:
            self._set_result_tab(
                tabs,
                2,
                self._build_lineup_table(recommended),
                t("match.detailed_xi"),
            )
        while tabs.count() > (3 if recommended is not None else 2):
            widget = tabs.widget(tabs.count() - 1)
            tabs.removeTab(tabs.count() - 1)
            if widget is not None:
                widget.setParent(None)

        return tabs

    def _set_result_tab(self, tabs, index, widget, label):
        if index < tabs.count() and tabs.widget(index) is widget:
            tabs.setTabText(index, label)
            return

        if index < tabs.count():
            old_widget = tabs.widget(index)
            tabs.removeTab(index)
            if old_widget is not None and old_widget is not widget:
                old_widget.setParent(None)
            tabs.insertTab(index, widget, label)
            return

        tabs.addTab(widget, label)

    def _build_pre_side_panel(self):
        """Alpha 0.6.7, Parts 10-12: the import action and PRE status
        live right beside the pitch, visually associated with the
        lineup being prepared for Hattrick -- not buried in the setup
        form above."""
        panel = QFrame()
        panel.setObjectName("preSidePanel")
        panel.setMaximumWidth(240)
        panel.setMinimumWidth(200)
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        layout.addWidget(self.official_import_button)

        self._pre_status_label = QLabel(t("match.pre_status.missing"))
        self._pre_status_label.setObjectName("preStatusWarningLabel")
        self._pre_status_label.setProperty("semanticStatus", "danger")
        self._pre_status_label.setWordWrap(True)
        layout.addWidget(self._pre_status_label)

        self._compact_ratings_container = QVBoxLayout()
        self._compact_ratings_container.setSpacing(4)
        layout.addLayout(self._compact_ratings_container)

        self._tactic_mismatch_label = QLabel("")
        self._tactic_mismatch_label.setObjectName("tacticMismatchWarning")
        self._tactic_mismatch_label.setProperty("semanticStatus", "warning")
        self._tactic_mismatch_label.setWordWrap(True)
        self._tactic_mismatch_label.setVisible(False)
        layout.addWidget(self._tactic_mismatch_label)

        layout.addStretch(1)
        self._pre_side_panel = panel
        return panel

    def set_pre_status(self, is_loaded):
        """Part 10-11: red warning before PRE exists, a normal-styled
        confirmation once it's been imported for this record."""
        if self._pre_status_label is None:
            return
        if is_loaded:
            self._pre_status_label.setText(t("match.pre_status.loaded"))
            self._pre_status_label.setProperty("semanticStatus", "success")
        else:
            self._pre_status_label.setText(t("match.pre_status.missing"))
            self._pre_status_label.setProperty("semanticStatus", "danger")
        self._pre_status_label.style().unpolish(self._pre_status_label)
        self._pre_status_label.style().polish(self._pre_status_label)

    def set_tactic_mismatch(self, current_tactic_label="", pre_tactic_label=""):
        """Alpha 0.6.7 HF-03, Part 10: a concise warning near
        Calificaciones when the current plan's tactic differs from
        Official PRE's own tactic -- passing empty strings hides it
        (no mismatch, or no PRE to compare against yet)."""
        if self._tactic_mismatch_label is None:
            return
        if not current_tactic_label or not pre_tactic_label or current_tactic_label == pre_tactic_label:
            self._tactic_mismatch_label.setVisible(False)
            self._tactic_mismatch_label.setText("")
            return
        self._tactic_mismatch_label.setText(
            t("match.tactic_mismatch.warning") + "\n"
            + t("match.tactic_mismatch.current_plan", tactic=current_tactic_label) + "\n"
            + t("match.tactic_mismatch.official_pre", tactic=pre_tactic_label)
        )
        self._tactic_mismatch_label.setVisible(True)

    def show_compact_official_ratings(self, ratings):
        """Alpha 0.6.7 HF-02, Part 15: a compact, Hattrick-inspired
        panel titled "Calificaciones" -- never "PRE oficial" (that
        wording lives in the separate status line beside it, Part 16).
        Uses a spatial grid (defense row / midfield / attack row, each
        with left-center-right columns) so *position* communicates the
        sector -- never verbose "Izquierda:"/"Central:"/"Derecha:"
        labels. `ratings` is a dict of already-formatted display
        strings: left_defense, central_defense, right_defense,
        midfield, left_attack, central_attack, right_attack, tactic,
        tactic_level, formation (optional), team_attitude (optional).
        """
        if self._compact_ratings_container is None:
            return
        while self._compact_ratings_container.count():
            item = self._compact_ratings_container.takeAt(0)
            widget = item.widget()
            layout_item = item.layout()
            if widget is not None:
                widget.setParent(None)
            elif layout_item is not None:
                while layout_item.count():
                    sub_item = layout_item.takeAt(0)
                    sub_widget = sub_item.widget()
                    if sub_widget is not None:
                        sub_widget.setParent(None)

        if not ratings:
            title = QLabel(t("match.compact_ratings.title"))
            title.setObjectName("sectionTitle")
            self._compact_ratings_container.addWidget(title)
            empty_label = QLabel(t("match.compact_ratings.not_loaded"))
            empty_label.setObjectName("compactDecisionText")
            self._compact_ratings_container.addWidget(empty_label)
            return

        title = QLabel(t("match.compact_ratings.title"))
        title.setObjectName("sectionTitle")
        self._compact_ratings_container.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(4)

        def _cell(value):
            label = QLabel(str(value) if value not in (None, "") else "-")
            label.setObjectName("compactRatingsValue")
            label.setAlignment(Qt.AlignCenter)
            return label

        # Row 0: defense (left, central, right) -- position alone
        # conveys the sector, matching the pitch's own left-to-right
        # orientation.
        grid.addWidget(_cell(ratings.get("left_defense")), 0, 0)
        grid.addWidget(_cell(ratings.get("central_defense")), 0, 1)
        grid.addWidget(_cell(ratings.get("right_defense")), 0, 2)
        # Row 1: midfield, centered across all three columns.
        grid.addWidget(_cell(ratings.get("midfield")), 1, 0, 1, 3)
        # Row 2: attack (left, central, right).
        grid.addWidget(_cell(ratings.get("left_attack")), 2, 0)
        grid.addWidget(_cell(ratings.get("central_attack")), 2, 1)
        grid.addWidget(_cell(ratings.get("right_attack")), 2, 2)
        for column in range(3):
            grid.setColumnStretch(column, 1)
        self._compact_ratings_container.addLayout(grid)

        if ratings.get("tactic"):
            tactic_label = QLabel(
                f"{t('match.compact_ratings.tactic')}: {ratings['tactic']}"
            )
            tactic_label.setWordWrap(True)
            self._compact_ratings_container.addWidget(tactic_label)
        if ratings.get("tactic_level"):
            level_label = QLabel(
                f"{t('match.compact_ratings.tactic_level')}: {ratings['tactic_level']}"
            )
            self._compact_ratings_container.addWidget(level_label)
        if ratings.get("formation"):
            formation_label = QLabel(
                f"{t('match.compact_ratings.formation')}: {ratings['formation']}"
            )
            self._compact_ratings_container.addWidget(formation_label)
        if ratings.get("team_attitude"):
            attitude_label = QLabel(
                f"{t('match.compact_ratings.team_attitude')}: {ratings['team_attitude']}"
            )
            self._compact_ratings_container.addWidget(attitude_label)

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
            board = self._formation_board_widget
            if board is None:
                board = FormationBoard()
                board.set_state_namespace("match")
                board.recalculate_requested.connect(
                    self.workspace_recalculate_requested.emit
                )
                board.workspace_modified.connect(
                    self.workspace_recalculate_requested.emit
                )
                board.set_save_as_first_match_visible(True)
                board.save_as_first_match_requested.connect(
                    self.save_as_first_match_requested
                )
                board.set_save_as_second_match_visible(True)
                board.save_as_second_match_requested.connect(
                    self.save_as_second_match_requested
                )
                board.save_formation_requested.connect(
                    self.save_formation_requested
                )
                self._update_save_action_labels()
                board.tactic_changed.connect(
                    self.tactic_changed
                )
                board.team_attitude_changed.connect(
                    self.team_attitude_changed
                )
                self._formation_board_widget = board
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
                preserve_input_orders=True,
                default_tactic=(
                    getattr(recommended, "recommended_tactic", "") if recommended else ""
                ),
            )
            self._update_save_action_labels()

            container = self._formation_board_tab_container
            if container is None:
                container = QWidget()
                container_layout = QHBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setSpacing(10)
                container_layout.addWidget(board, 1)
                container_layout.addWidget(self._build_pre_side_panel())
                self._formation_board_tab_container = container
            return container
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

    def _build_sector_rating_panel(self, formation, intelligence=None):
        card = QFrame()
        card.setObjectName("compactDecisionLab")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(6)

        title = QLabel(t("sector_rating.title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        note = QLabel(t("sector_rating.scale_note"))
        note.setWordWrap(True)
        note.setObjectName("compactDecisionText")
        layout.addWidget(note)

        comparable = self._sector_ratings_comparable(formation)
        column_labels = [
            t("sector_rating.matchup"),
            t("sector_rating.our_rating"),
            t("sector_rating.opponent_rating"),
        ]
        if comparable:
            column_labels.append(t("sector_rating.difference"))
        column_labels.append(t("sector_rating.assessment"))

        table = QTableWidget(
            len(formation.sector_rating_comparisons),
            len(column_labels),
        )
        table.setObjectName("comparisonTable")
        table.setHorizontalHeaderLabels(column_labels)
        self._configure_table(table)
        table.setMinimumHeight(
            82 + 26 * max(1, len(formation.sector_rating_comparisons))
        )

        for row, comparison in enumerate(formation.sector_rating_comparisons):
            values = [
                t(f"sector_rating.matchup_key.{comparison.matchup_key}"),
                self._sector_rating_text(
                    comparison.our_value,
                    comparison.our_scale,
                ),
                self._sector_rating_text(
                    comparison.opponent_value,
                    comparison.opponent_scale,
                ),
            ]
            if comparable:
                values.append(self._sector_difference_text(comparison))
            values.append(t(f"sector_rating.advantage.{comparison.advantage}"))
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))

        layout.addWidget(table)

        # Alpha 0.6.6, Part 6: the matchup matrix (formerly duplicated
        # in the main Match Intelligence section) lives here now --
        # technical calibration detail stays accessible in this
        # diagnostic section, just not repeated in the tactical
        # narrative above it.
        matrix = getattr(intelligence, "matrix", None) if intelligence is not None else None
        has_matrix_rows = matrix is not None and (
            matrix.our_attack_rows or matrix.opponent_attack_rows
        )
        if has_matrix_rows:
            matrix_title = QLabel(t("match_intelligence.matrix.title"))
            matrix_title.setObjectName("sectionTitle")
            layout.addWidget(matrix_title)
            layout.addWidget(
                self._build_matchup_matrix(matrix, comparable)
            )

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

    def _build_match_intelligence_panel(self, intelligence, formation=None):
        comparable = self._sector_ratings_comparable(formation)
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

        content_row = 2
        if not comparable:
            scale_note = QLabel(t("match_intelligence.scale_limitation"))
            scale_note.setWordWrap(True)
            scale_note.setObjectName("compactDecisionText")
            layout.addWidget(scale_note, content_row, 0, 1, 3)
            content_row += 1

        focuses = QWidget()
        focus_layout = QVBoxLayout(focuses)
        focus_layout.setContentsMargins(0, 0, 0, 0)
        focus_layout.setSpacing(2)
        focus_layout.addWidget(
            self._mini_heading(t("match_intelligence.focus.title"))
        )
        for focus in self._visible_match_intelligence_focuses(
            intelligence,
            comparable,
        )[:3]:
            label = QLabel(
                t(
                    focus.title_key,
                    **self._localized_params(focus.params),
                )
            )
            label.setObjectName("metadataValue")
            focus_layout.addWidget(label)
        layout.addWidget(focuses, content_row, 0)

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
        layout.addWidget(profile, content_row, 1)

        highlights = QWidget()
        highlights_layout = QVBoxLayout(highlights)
        highlights_layout.setContentsMargins(0, 0, 0, 0)
        highlights_layout.setSpacing(2)
        highlights_layout.addWidget(
            self._mini_heading(t("match_intelligence.highlights"))
        )
        for item in self._visible_match_intelligence_items(
            intelligence,
            comparable,
        )[:2]:
            highlights_layout.addWidget(
                QLabel(
                    t(
                        item.title_key,
                        **self._localized_params(item.params),
                    )
                )
            )
        layout.addWidget(highlights, content_row, 2)

        # Alpha 0.6.6, Part 6: the raw matchup matrix table used to be
        # duplicated here -- it's now shown once, in the technical/
        # diagnostic "rating_calibration" section
        # (`_build_sector_rating_panel`), which already covers this
        # same numeric detail. The main Match Intelligence section
        # keeps only the qualitative highlights above (tactical
        # objective, key advantages/risks) -- never the number-heavy
        # comparison table.

        for column in range(3):
            layout.setColumnStretch(column, 1)
        return card

    def _build_matchup_matrix(self, matrix, comparable=True):
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
            if comparable and item.is_best_route:
                marker = "+"
            elif comparable and item.is_worst_route:
                marker = "!"
            classification = (
                f"{marker} {t(f'match_intelligence.classification.{item.classification.lower()}')}".strip()
                if comparable
                else t("match_intelligence.not_comparable")
            )
            values = [
                side,
                t(f"match_intelligence.sector.{item.attack_sector}"),
                t(f"match_intelligence.sector.{item.defense_sector}"),
                (
                    f"{item.difference:+.0f}"
                    if comparable
                    else t("sector_rating.not_comparable")
                ),
                classification,
            ]
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))
        return table

    def _visible_match_intelligence_focuses(self, intelligence, comparable):
        if comparable:
            return list(intelligence.tactical_focuses)
        return [
            focus for focus in intelligence.tactical_focuses
            if focus.code == "midfield_battle"
        ]

    def _visible_match_intelligence_items(self, intelligence, comparable):
        items = list(intelligence.opportunities) + list(intelligence.risks)
        if comparable:
            return items
        return [
            item for item in items
            if "difference" not in dict(item.params or {})
        ]

    def _sector_ratings_comparable(self, formation):
        comparisons = getattr(
            formation,
            "sector_rating_comparisons",
            None,
        )
        if not comparisons:
            return True
        # Alpha 0.6.6, Part 5: "comparable" on each individual
        # SectorComparison also requires both values to be present --
        # correct for that field's own purpose, but too strict here.
        # Optional secondary sectors (indirect set pieces) frequently
        # have no data at all, which is a data-availability question,
        # not a scale-compatibility one. This check is specifically
        # about whether the scales genuinely disagree, so it only
        # looks at comparisons that actually have both values.
        with_data = [
            comparison for comparison in comparisons
            if comparison.our_value is not None and comparison.opponent_value is not None
        ]
        if not with_data:
            return True
        return all(
            comparison.our_scale == comparison.opponent_scale
            for comparison in with_data
        )

    def _build_decision_lab_panel(self, decision_lab, recommended):
        card = QFrame()
        card.setObjectName("compactDecisionLab")
        layout = QGridLayout(card)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(3)

        confidence = QLabel(
            t(
                "match.recommendation_confidence",
                level=confidence_level_label(decision_lab.confidence.level),
            )
        )
        confidence.setObjectName("recommendedBadge")
        layout.addWidget(confidence, 0, 0)

        support = QLabel(
            decision_lab_support_label(decision_lab.confidence_score)
        )
        support.setObjectName("compactDecisionText")
        layout.addWidget(support, 0, 1)
        layout.setColumnStretch(2, 1)

        if recommended is None:
            headline = QLabel(localized_decision_summary(decision_lab.summary))
            headline.setWordWrap(True)
            layout.addWidget(headline, 1, 0, 1, 5)
            return card

        reason = (
            localized_decision_reason(decision_lab.reasons[0])[1]
            if decision_lab.reasons
            else localized_decision_summary(decision_lab.summary)
        )
        risk = (
            localized_decision_risk(decision_lab.risks[0])[1]
            if decision_lab.risks
            else localized_decision_summary(decision_lab.summary)
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
                localized_confidence_explanation(decision_lab.confidence),
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
            is_recommended = self._is_recommended_formation(result, formation)
            row_values = [
                "*" if is_recommended else "",
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
                if is_recommended:
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
        configure_table(table)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(
            QAbstractItemView.NoSelection
        )
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(EmptyState(title, message))
        self.results_layout.addWidget(panel)
        self.results_layout.addStretch(1)

    def retranslate_ui(self):
        self.set_page_text(
            t("match.title"),
            t("match.subtitle"),
        )
        self.analysis_setup_title.setText(
            t("match.editing_saved_match")
            if self._editing_saved_match
            else t("match.analysis_setup")
        )
        self.csv_label.setText(t("match.players_csv"))
        self.players_path_edit.setPlaceholderText(t("match.select_players_csv"))
        self.browse_button.setText(t("match.browse"))
        self.load_button.setText(t("match.load_players"))
        self.save_metadata_button.setText(t("match.save_changes"))
        self.opponent_label.setText(t("match.opponent"))
        self.formation_label.setText(t("match.formations"))
        self.select_all_button.setText(t("match.select_all"))
        self.clear_all_button.setText(t("match.clear_all"))
        self.favorites_button.setText(t("match.favorites"))
        self.analyze_button.setText(t("match.analyze"))
        self.match_type_label.setText(t("match.match_type"))
        self.match_type_combo.setItemText(0, t("match.match_type_select"))
        self.match_type_combo.setItemText(1, t("match.match_type_league"))
        self.match_type_combo.setItemText(2, t("match.match_type_cup"))
        self.match_date_label.setText(t("match.match_date"))
        self.venue_role_label.setText(t("match.venue_role"))
        self._update_save_action_labels()
        self._sync_analysis_setup_toggle()
        self._update_formation_warning()
        self._retranslate_match_sections()
        if self._state == "empty":
            self.clear_results()
        elif self._last_result is not None:
            self.show_results(
                self._last_result,
                restored=self._last_restored,
                workspace_state=self._last_workspace_state,
            )

    def _retranslate_match_sections(self):
        if not self._match_sections:
            return
        titles = {
            "decision_lab": t("match.decision_lab"),
            "match_intelligence": t("match_intelligence.title"),
            "rating_calibration": t("sector_rating.title"),
            "match_analysis": t("match.match_analysis"),
        }
        summaries = {}
        if self._last_result is not None:
            recommended = self._last_result.recommended_formation
            summaries = {
                "decision_lab": self._decision_lab_summary(self._last_result),
                "match_intelligence": self._match_intelligence_summary(self._last_result),
                "rating_calibration": self._rating_calibration_summary(recommended),
                "match_analysis": self._match_analysis_summary(self._last_result),
            }
        for key, section in self._match_sections.items():
            section.retranslate(
                titles.get(key),
                summaries.get(key, section.summary()),
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
            if self._is_recommended_formation(result, formation)
        ]

    def comparison_rows(self, result):
        return [
            {
                "formation": formation.formation_name,
                "recommended": self._is_recommended_formation(result, formation),
                "win_delta": formation.win_probability_delta,
                "xg_delta": formation.expected_goals_delta,
            }
            for formation in result.formations
        ]

    def decision_lab_rows(self, result):
        if result.decision_lab is None:
            return {}
        recommended = getattr(result, "recommended_formation", None)

        return {
            "formation": (
                recommended.formation_name
                if recommended is not None
                else result.decision_lab.recommended_formation.formation
            ),
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
        formation = getattr(result, "recommended_formation", None)
        return {
            "formation": intelligence.formation_name,
            "ratings_comparable": self._sector_ratings_comparable(
                formation
            ),
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

    @staticmethod
    def _stable_recommendation_id(result):
        explicit_id = str(getattr(result, "recommendation_id", "") or "").strip()
        if explicit_id:
            return explicit_id
        recommended = getattr(result, "recommended_formation", None)
        return getattr(recommended, "formation_name", "")

    def _is_recommended_formation(self, result, formation):
        recommendation_id = self._stable_recommendation_id(result)
        if recommendation_id:
            return formation.formation_name == recommendation_id
        return bool(getattr(formation, "is_recommended", False))

    def _with_stable_recommendation_flags(self, result):
        formations = list(getattr(result, "formations", ()) or ())
        if not formations:
            return result
        recommendation_id = self._stable_recommendation_id(result)
        if not recommendation_id:
            return result
        updated = [
            replace(
                formation,
                is_recommended=(formation.formation_name == recommendation_id),
            )
            for formation in formations
        ]
        return replace(
            result,
            formations=updated,
            recommendation_id=recommendation_id,
        )

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

    def _sector_rating_text(self, value, scale):
        text = format_rating_value(
            value,
            scale,
            language=localization_service().language,
        )
        if not text:
            return t("sector_rating.not_available")
        return t(
            f"sector_rating.scale.{scale}",
            value=text,
        )

    def _sector_difference_text(self, comparison):
        if not comparison.comparable or comparison.difference is None:
            return t("sector_rating.not_comparable")
        return self._format_delta_number(comparison.difference)

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
        previous_match_type = getattr(self, "_last_workspace_match_type", None)
        self._update_formation_warning()
        self._update_availability_warning()
        self._update_analyze_button_state()

        if not self._applying_settings:
            if self._editing_saved_match:
                self._metadata_dirty = True
            self._update_save_action_labels()
            if (
                self._last_result is not None
                and previous_match_type is not None
                and self.match_type() != previous_match_type
            ):
                self.set_analysis_stale(
                    True,
                    t("match.analysis_stale_match_type"),
                )
            self.workspace_changed.emit()
        self._last_workspace_match_type = self.match_type()

    def _can_analyze(self):
        return bool(
            self.players_csv_path()
            and self.selected_opponent_name()
            and self.match_type()
            and self.selected_formations()
        )

    def _update_analyze_button_state(self):
        if hasattr(self, "analyze_button"):
            self.analyze_button.setEnabled(self._can_analyze())

    def _update_save_action_labels(self):
        board = getattr(self, "_formation_board_widget", None)
        if board is not None:
            board.save_as_first_match_button.setText(t("match.save_as_first_match"))
            board.save_as_second_match_button.setText(t("match.save_as_second_match"))
        if self._editing_saved_match:
            if board is not None:
                board.save_formation_button.setText(t("match.save_changes"))
            self.save_metadata_button.setText(t("match.save_changes"))
        else:
            if board is not None:
                board.save_formation_button.setText(t("match.save_formation"))
            self.save_metadata_button.setText(t("match.save_changes"))
        reason = self._save_action_disabled_reason()
        metadata_save_visible = (
            self._editing_saved_match
            and self._metadata_dirty
            and (
                board is None
                or getattr(self, "_last_result", None) is None
                or not getattr(getattr(self, "_last_result", None), "formations", None)
                or not board.is_dirty()
            )
        )
        self.save_metadata_button.setVisible(metadata_save_visible)
        self.save_metadata_button.setEnabled(not reason)
        self.save_metadata_button.setToolTip(reason)
        if board is not None and hasattr(board, "set_save_action_validation"):
            board.set_save_action_validation(not reason, reason)

    def _save_action_disabled_reason(self):
        if self._editing_saved_match and self._metadata_dirty:
            if not self.selected_opponent_name():
                return t("match.save_disabled_no_opponent")
            if not self.match_type():
                return t("match.save_disabled_no_match_type")
            if not self.match_date():
                return t("match.save_disabled_no_match_date")
            return ""
        if self._analysis_stale:
            return t("match.analysis_stale_match_type")
        result = getattr(self, "_last_result", None)
        if result is None or not getattr(result, "formations", None):
            return t("match.save_disabled_no_analysis")
        recommended = getattr(result, "recommended_formation", None)
        if recommended is None or not getattr(recommended, "lineup", None):
            return t("match.save_disabled_no_lineup")
        if not self.selected_opponent_name():
            return t("match.save_disabled_no_opponent")
        if not self.match_type():
            return t("match.save_disabled_no_match_type")
        if not self.match_date():
            return t("match.save_disabled_no_match_date")
        return ""

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
