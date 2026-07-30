from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Signal

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


class ClubAdvisorPage(BasePage):
    generate_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(
            t("club_advisor.panel.title"),
            "",
            parent,
        )

        self.generate_button = QPushButton(t("club_advisor.panel.generate"))
        self.generate_button.clicked.connect(self.generate_requested)
        self.body_layout.addWidget(self.generate_button)

        self.empty_state_label = QLabel(t("club_advisor.panel.no_roster"))
        self.empty_state_label.setWordWrap(True)
        self.body_layout.addWidget(self.empty_state_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(12)

        self.status_frame, self._status_title, self.status_label = _card(
            "club_advisor.panel.project_status"
        )
        self.priorities_frame, self._priorities_title, self.priorities_label = _card(
            "club_advisor.panel.priorities"
        )
        self.strengths_frame, self._strengths_title, self.strengths_label = _card(
            "club_advisor.panel.strengths"
        )
        self.risks_frame, self._risks_title, self.risks_label = _card(
            "club_advisor.panel.risks"
        )
        self.training_frame, self._training_title, self.training_label = _card(
            "club_advisor.panel.section_training"
        )
        self.squad_frame, self._squad_title, self.squad_label = _card(
            "club_advisor.panel.section_squad"
        )
        self.depth_frame, self._depth_title, self.depth_label = _card(
            "club_advisor.panel.depth"
        )
        self.warnings_frame, self._warnings_title, self.warnings_label = _card(
            "club_advisor.panel.warnings"
        )
        self.limitations_frame, self._limitations_title, self.limitations_label = _card(
            "club_advisor.panel.limitations"
        )

        grid.addWidget(self.status_frame, 0, 0)
        grid.addWidget(self.priorities_frame, 0, 1)
        grid.addWidget(self.strengths_frame, 1, 0)
        grid.addWidget(self.risks_frame, 1, 1)
        grid.addWidget(self.training_frame, 2, 0)
        grid.addWidget(self.squad_frame, 2, 1)
        grid.addWidget(self.depth_frame, 3, 0)
        grid.addWidget(self.warnings_frame, 3, 1)
        grid.addWidget(self.limitations_frame, 4, 0, 1, 2)

        scroll.setWidget(container)
        self.body_layout.addWidget(scroll)
        self._sections_container = container
        self._sections_container.setVisible(False)

    def retranslate_ui(self):
        self.set_page_text(t("club_advisor.panel.title"), "")
        self.generate_button.setText(t("club_advisor.panel.generate"))
        self.empty_state_label.setText(t("club_advisor.panel.no_roster"))

    def show_empty_state(self):
        self.empty_state_label.setVisible(True)
        self._sections_container.setVisible(False)

    def show_report(self, sections):
        """`sections` is a dict of section-key -> plain text, already
        formatted by the controller/formatting layer."""
        self.empty_state_label.setVisible(False)
        self._sections_container.setVisible(True)
        self.status_label.setText(sections.get("status", ""))
        self.priorities_label.setText(sections.get("priorities", ""))
        self.strengths_label.setText(sections.get("strengths", ""))
        self.risks_label.setText(sections.get("risks", ""))
        self.training_label.setText(sections.get("training", ""))
        self.squad_label.setText(sections.get("squad", ""))
        self.depth_label.setText(sections.get("depth", ""))
        self.warnings_label.setText(sections.get("warnings", ""))
        self.limitations_label.setText(sections.get("limitations", ""))
