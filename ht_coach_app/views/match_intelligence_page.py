from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
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

    def __init__(self, parent=None):
        super().__init__(t("official_match_intelligence.title"), "", parent)

        self.import_button = QPushButton(t("official_match_intelligence.import.action"))
        self.import_button.clicked.connect(self.import_requested)
        self.body_layout.addWidget(self.import_button)

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
