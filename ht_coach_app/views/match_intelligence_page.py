from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.core.localization import t
from ht_coach_app.views.base_page import BasePage

# HF-02.2, Part 4: below this width the PRE/POST cards stack vertically
# instead of sitting side by side.
_NARROW_LAYOUT_BREAKPOINT = 720


def _card(title_key):
    frame = QFrame()
    frame.setObjectName("workspacePanel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(6)
    title = QLabel(t(title_key))
    title.setObjectName("sectionTitle")
    body = QLabel("")
    body.setWordWrap(True)
    layout.addWidget(title)
    layout.addWidget(body)
    return frame, title, body


class MatchIntelligencePage(BasePage):
    import_requested = Signal()
    refresh_requested = Signal()
    season_filter_changed = Signal(object)
    record_navigation_requested = Signal(str)
    record_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(t("official_match_intelligence.title"), "", parent)

        self.import_button = QPushButton(t("official_match_intelligence.import.action"))
        self.import_button.clicked.connect(self.import_requested)
        self.body_layout.addWidget(self.import_button)

        # Parts 13-14, 20: the record-based history header -- season
        # filter, previous/current/next navigation through whatever
        # that filter selects, and the current record's identity.
        self._build_history_header()

        self.empty_state_label = QLabel(t("official_match_intelligence.no_data"))
        self.empty_state_label.setWordWrap(True)
        self.body_layout.addWidget(self.empty_state_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setSpacing(12)

        # Part 4: PRE and POST side by side, identical structure --
        # a dedicated row widget that reflows to a vertical stack below
        # _NARROW_LAYOUT_BREAKPOINT (see resizeEvent).
        self.pre_frame, _, self.pre_label = _card("official_match_intelligence.section.official_pre")
        self.post_frame, _, self.post_label = _card("official_match_intelligence.section.official_post")
        self._pre_post_row = QHBoxLayout()
        self._pre_post_row.setSpacing(12)
        self._pre_post_row.addWidget(self.pre_frame, 1)
        self._pre_post_row.addWidget(self.post_frame, 1)
        outer.addLayout(self._pre_post_row)

        # Part 5: interpreted sector-by-sector comparison (direction +
        # magnitude, never just raw numbers).
        self.sector_frame, _, self.sector_label = _card(
            "official_match_intelligence.section.sector_analysis"
        )
        outer.addWidget(self.sector_frame)

        # Part 6: deterministic, useful conclusions -- its own card,
        # never conflated with the "not yet available" limitations card.
        self.conclusions_frame, _, self.conclusions_label = _card(
            "official_match_intelligence.section.conclusions"
        )
        outer.addWidget(self.conclusions_frame)

        # Part 7: the internal HT Coach estimate collapses under
        # "Diagnóstico interno" when it adds no comparative value (no
        # numeric delta shown, scales not confirmed compatible) --
        # collapsed by default, expandable for technical inspection.
        self.internal_diagnostic_frame = self._build_internal_diagnostic_card()
        outer.addWidget(self.internal_diagnostic_frame)

        self.future_frame, _, self.future_label = _card(
            "official_match_intelligence.section.not_yet_available"
        )
        outer.addWidget(self.future_frame)

        scroll.setWidget(container)
        self.body_layout.addWidget(scroll)
        self._sections_container = container
        self._sections_container.setVisible(False)

        self.future_label.setText(t("official_match_intelligence.not_yet_available_body"))

    def _build_history_header(self):
        header = QFrame()
        header.setObjectName("workspacePanel")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(t("official_match_intelligence.history.season_label")))
        self.season_filter_combo = QComboBox()
        self.season_filter_combo.addItem(t("official_match_intelligence.history.all_seasons"), None)
        self.season_filter_combo.currentIndexChanged.connect(
            lambda: self.season_filter_changed.emit(self.season_filter_combo.currentData())
        )
        filter_row.addWidget(self.season_filter_combo)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        nav_row = QHBoxLayout()
        self.record_nav_previous_button = QPushButton(
            t("official_match_intelligence.history.previous_record")
        )
        self.record_nav_previous_button.clicked.connect(
            lambda: self.record_navigation_requested.emit("previous")
        )
        self.record_selector_combo = QComboBox()
        self.record_selector_combo.setMinimumWidth(260)
        self.record_selector_combo.activated.connect(
            lambda index: self.record_selected.emit(self.record_selector_combo.itemData(index))
        )
        self.record_nav_next_button = QPushButton(
            t("official_match_intelligence.history.next_record")
        )
        self.record_nav_next_button.clicked.connect(
            lambda: self.record_navigation_requested.emit("next")
        )
        nav_row.addWidget(self.record_nav_previous_button)
        nav_row.addWidget(self.record_selector_combo, 1)
        nav_row.addWidget(self.record_nav_next_button)
        layout.addLayout(nav_row)

        self.record_identity_label = QLabel("")
        self.record_identity_label.setObjectName("recordIdentityLabel")
        self.record_identity_label.setWordWrap(True)
        layout.addWidget(self.record_identity_label)

        self.body_layout.addWidget(header)
        self._history_header = header

    def set_available_seasons(self, seasons):
        current = self.season_filter_combo.currentData()
        self.season_filter_combo.blockSignals(True)
        self.season_filter_combo.clear()
        self.season_filter_combo.addItem(t("official_match_intelligence.history.all_seasons"), None)
        for season_number in seasons:
            self.season_filter_combo.addItem(
                t("official_match_intelligence.history.season_item", number=season_number),
                season_number,
            )
        index = self.season_filter_combo.findData(current)
        self.season_filter_combo.setCurrentIndex(index if index >= 0 else 0)
        self.season_filter_combo.blockSignals(False)

    def set_record_options(self, options, selected_snapshot_id=None):
        self.record_selector_combo.blockSignals(True)
        self.record_selector_combo.clear()
        for snapshot_id, label in options:
            self.record_selector_combo.addItem(label, snapshot_id)
        if selected_snapshot_id is not None:
            index = self.record_selector_combo.findData(selected_snapshot_id)
            if index >= 0:
                self.record_selector_combo.setCurrentIndex(index)
        self.record_selector_combo.blockSignals(False)

    def show_record_navigation_state(self, can_go_previous, can_go_next):
        self.record_nav_previous_button.setEnabled(can_go_previous)
        self.record_nav_next_button.setEnabled(can_go_next)

    def set_record_identity(self, text):
        self.record_identity_label.setText(text)

    def confirm_retrospective_pre(self):
        """Part 17's own dialog, word-for-word: this PRE was generated
        for another Match ID and after the original match -- offer to
        save it as a retrospective simulation instead of silently
        treating it as the real official PRE."""
        from PySide6.QtWidgets import QMessageBox

        box = QMessageBox(self)
        box.setWindowTitle(t("official_match_intelligence.retrospective.dialog_title"))
        box.setText(t("official_match_intelligence.retrospective.dialog_message"))
        back_button = box.addButton(
            t("official_match_intelligence.retrospective.dialog_back"),
            QMessageBox.RejectRole,
        )
        save_button = box.addButton(
            t("official_match_intelligence.retrospective.dialog_save"),
            QMessageBox.AcceptRole,
        )
        box.setDefaultButton(back_button)
        box.exec()
        return box.clickedButton() is save_button

    def _build_internal_diagnostic_card(self):
        frame = QFrame()
        frame.setObjectName("workspacePanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel(t("official_match_intelligence.section.internal_diagnostic"))
        title.setObjectName("sectionTitle")
        header.addWidget(title, 1)
        self.internal_diagnostic_toggle = QToolButton()
        self.internal_diagnostic_toggle.setObjectName("internalDiagnosticToggle")
        self.internal_diagnostic_toggle.setCheckable(True)
        self.internal_diagnostic_toggle.setChecked(False)
        self.internal_diagnostic_toggle.setText(
            t("official_match_intelligence.section.expand")
        )
        self.internal_diagnostic_toggle.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.internal_diagnostic_toggle.clicked.connect(self._toggle_internal_diagnostic)
        header.addWidget(self.internal_diagnostic_toggle)
        layout.addLayout(header)

        self.internal_diagnostic_limitation_label = QLabel("")
        self.internal_diagnostic_limitation_label.setWordWrap(True)
        layout.addWidget(self.internal_diagnostic_limitation_label)

        self.prediction_label = QLabel("")
        self.prediction_label.setWordWrap(True)
        self.prediction_label.setVisible(False)
        layout.addWidget(self.prediction_label)

        return frame

    def _toggle_internal_diagnostic(self):
        expanded = self.internal_diagnostic_toggle.isChecked()
        self.prediction_label.setVisible(expanded)
        self.internal_diagnostic_toggle.setText(
            t("official_match_intelligence.section.collapse")
            if expanded
            else t("official_match_intelligence.section.expand")
        )

    def retranslate_ui(self):
        self.set_page_text(t("official_match_intelligence.title"), "")
        self.import_button.setText(t("official_match_intelligence.import.action"))
        self.empty_state_label.setText(t("official_match_intelligence.no_data"))
        self.future_label.setText(t("official_match_intelligence.not_yet_available_body"))

    def show_empty_state(self):
        self.empty_state_label.setVisible(True)
        self._sections_container.setVisible(False)

    def show_snapshot(self, sections):
        self.empty_state_label.setVisible(False)
        self._sections_container.setVisible(True)
        self.pre_label.setText(sections.get("pre") or t("official_match_intelligence.not_imported"))
        self.post_label.setText(sections.get("post") or t("official_match_intelligence.not_imported"))
        self.sector_label.setText(sections.get("comparison") or "-")
        self.conclusions_label.setText(sections.get("conclusions") or "-")
        self.prediction_label.setText(sections.get("prediction") or "-")
        self.internal_diagnostic_limitation_label.setText(
            sections.get("internal_diagnostic_limitation") or ""
        )

    def showEvent(self, event):
        # Auto-refresh whenever the tab becomes visible again -- no
        # manual refresh needed, since importing PRE/POST anywhere
        # (Match or here) should refresh Match Intelligence
        # automatically per this sprint's requirement.
        super().showEvent(event)
        self.refresh_requested.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_pre_post_layout(self.width())

    def _apply_pre_post_layout(self, available_width):
        stacked = available_width < _NARROW_LAYOUT_BREAKPOINT
        if stacked and self._pre_post_row.direction() != QBoxLayout.TopToBottom:
            self._pre_post_row.setDirection(QBoxLayout.TopToBottom)
        elif not stacked and self._pre_post_row.direction() != QBoxLayout.LeftToRight:
            self._pre_post_row.setDirection(QBoxLayout.LeftToRight)
