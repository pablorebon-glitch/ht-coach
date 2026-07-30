from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.core.localization import t
from ht_coach_app.views.base_page import BasePage


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
        grid = QVBoxLayout(container)
        grid.setSpacing(12)

        self.pre_frame, _, self.pre_label = _card("official_match_intelligence.section.official_pre")
        self.post_frame, _, self.post_label = _card("official_match_intelligence.section.official_post")
        self.sector_frame, _, self.sector_label = _card(
            "official_match_intelligence.section.sector_analysis"
        )
        self.future_frame, _, self.future_label = _card(
            "official_match_intelligence.section.not_yet_available"
        )
        self.prediction_frame, _, self.prediction_label = _card(
            "official_match_intelligence.section.ht_coach_comparison"
        )

        grid.addWidget(self.pre_frame)
        grid.addWidget(self.post_frame)
        grid.addWidget(self.sector_frame)
        grid.addWidget(self.future_frame)
        grid.addWidget(self.prediction_frame)

        scroll.setWidget(container)
        self.body_layout.addWidget(scroll)
        self._sections_container = container
        self._sections_container.setVisible(False)

        self.future_label.setText(t("official_match_intelligence.not_yet_available_body"))

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
        self.future_label.setText(
            sections.get("conclusions")
            or t("official_match_intelligence.not_yet_available_body")
        )
        self.prediction_label.setText(sections.get("prediction") or "-")

    def showEvent(self, event):
        # Auto-refresh whenever the tab becomes visible again -- no
        # manual refresh needed, since importing PRE/POST anywhere
        # (Match or here) should refresh Match Intelligence
        # automatically per this sprint's requirement.
        super().showEvent(event)
        self.refresh_requested.emit()
