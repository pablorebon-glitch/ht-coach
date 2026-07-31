from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal

from ht_coach_app.core.localization import t
from ht_coach_app.views.base_page import BasePage


def _card(title_key, card_key=None, page=None):
    frame = QFrame()
    frame.setObjectName("workspacePanel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(8)
    title = QLabel(t(title_key))
    title.setObjectName("sectionTitle")
    title.setWordWrap(True)
    body = QLabel("")
    body.setWordWrap(True)
    body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    frame.setMinimumHeight(96)
    frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    layout.addWidget(title)
    layout.addWidget(body, 1)

    if card_key and page is not None:
        frame.setCursor(Qt.PointingHandCursor)

        def _handle_click(event, key=card_key):
            page.card_clicked.emit(key)

        frame.mousePressEvent = _handle_click

    return frame, title, body


class ClubAdvisorPage(BasePage):
    generate_requested = Signal()
    season_context_changed = Signal()
    card_clicked = Signal(str)

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
        grid.setAlignment(Qt.AlignTop)

        # 1. Current project status
        self.status_frame, self._status_title, self.status_label = _card(
            "club_advisor.panel.project_status"
        )
        # 2. Season context (compact, editable)
        self.season_context_frame = self._build_season_context_card()
        # 3. Operational priorities
        self.operational_frame, _, self.operational_label = _card(
            "club_advisor.panel.operational_priorities"
        )
        # 4. Strategic priorities
        self.strategic_frame, _, self.strategic_label = _card(
            "club_advisor.panel.strategic_priorities"
        )
        # 5. Promotion readiness
        self.promotion_readiness_frame, _, self.promotion_readiness_label = _card(
            "club_advisor.panel.promotion_readiness"
        )
        # 6. Strengths / 7. Risks
        self.strengths_frame, self._strengths_title, self.strengths_label = _card(
            "club_advisor.panel.strengths", "strengths", self
        )
        self.risks_frame, self._risks_title, self.risks_label = _card(
            "club_advisor.panel.risks", "risks", self
        )
        # existing structural sections, kept as-is
        self.training_frame, self._training_title, self.training_label = _card(
            "club_advisor.panel.section_training", "training", self
        )
        self.squad_frame, self._squad_title, self.squad_label = _card(
            "club_advisor.panel.section_squad", "squad", self
        )
        self.depth_frame, self._depth_title, self.depth_label = _card(
            "club_advisor.panel.depth", "depth", self
        )
        self.warnings_frame, self._warnings_title, self.warnings_label = _card(
            "club_advisor.panel.warnings"
        )
        # 8. Limitations
        self.limitations_frame, self._limitations_title, self.limitations_label = _card(
            "club_advisor.panel.limitations", "limitations", self
        )

        grid.addWidget(self.status_frame, 0, 0)
        grid.addWidget(self.season_context_frame, 0, 1)
        grid.addWidget(self.operational_frame, 1, 0)
        grid.addWidget(self.strategic_frame, 1, 1)
        grid.addWidget(self.promotion_readiness_frame, 2, 0)
        grid.addWidget(self.strengths_frame, 2, 1)
        grid.addWidget(self.risks_frame, 3, 0)
        grid.addWidget(self.training_frame, 3, 1)
        grid.addWidget(self.squad_frame, 4, 0)
        grid.addWidget(self.depth_frame, 4, 1)
        grid.addWidget(self.warnings_frame, 5, 0)
        grid.addWidget(self.limitations_frame, 5, 1)

        scroll.setWidget(container)
        self.body_layout.addWidget(scroll)
        self._sections_container = container
        self._sections_container.setVisible(False)

    def _build_season_context_card(self):
        frame = QFrame()
        frame.setObjectName("workspacePanel")
        frame.setMinimumWidth(260)
        frame.setMinimumHeight(96)
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title = QLabel(t("club_advisor.panel.season_context"))
        title.setObjectName("sectionTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        self.season_phase_combo = QComboBox()
        for value, key in (
            ("unknown", "club_advisor.season_phase.unknown"),
            ("preseason", "club_advisor.season_phase.preseason"),
            ("early_season", "club_advisor.season_phase.early_season"),
            ("mid_season", "club_advisor.season_phase.mid_season"),
            ("late_season", "club_advisor.season_phase.late_season"),
            ("promotion_stage", "club_advisor.season_phase.promotion_stage"),
            ("offseason", "club_advisor.season_phase.offseason"),
        ):
            self.season_phase_combo.addItem(t(key), value)

        self.promotion_objective_combo = QComboBox()
        for value, key in (
            ("welcome_if_natural", "club_advisor.promotion_objective.welcome_if_natural"),
            ("not_a_priority", "club_advisor.promotion_objective.not_a_priority"),
            ("target_this_season", "club_advisor.promotion_objective.target_this_season"),
            ("must_promote", "club_advisor.promotion_objective.must_promote"),
            ("avoid_promotion", "club_advisor.promotion_objective.avoid_promotion"),
            ("unspecified", "club_advisor.promotion_objective.unspecified"),
        ):
            self.promotion_objective_combo.addItem(t(key), value)

        self.competitiveness_combo = QComboBox()
        for value, key in (
            ("unknown", "club_advisor.competitiveness.unknown"),
            ("dominant", "club_advisor.competitiveness.dominant"),
            ("strong", "club_advisor.competitiveness.strong"),
            ("competitive", "club_advisor.competitiveness.competitive"),
            ("under_pressure", "club_advisor.competitiveness.under_pressure"),
            ("outmatched", "club_advisor.competitiveness.outmatched"),
        ):
            self.competitiveness_combo.addItem(t(key), value)

        self.bot_opponents_spin = QSpinBox()
        self.bot_opponents_spin.setRange(0, 20)

        self.recent_signing_checkbox = QCheckBox(t("club_advisor.panel.recent_signing"))

        self.season_notes_edit = QLineEdit()

        layout.addWidget(QLabel(t("club_advisor.panel.season_phase")))
        layout.addWidget(self.season_phase_combo)
        layout.addWidget(QLabel(t("club_advisor.panel.promotion_objective")))
        layout.addWidget(self.promotion_objective_combo)
        layout.addWidget(QLabel(t("club_advisor.panel.competitiveness")))
        layout.addWidget(self.competitiveness_combo)
        layout.addWidget(QLabel(t("club_advisor.panel.bot_opponents")))
        layout.addWidget(self.bot_opponents_spin)
        layout.addWidget(self.recent_signing_checkbox)
        layout.addWidget(QLabel(t("club_advisor.panel.notes")))
        layout.addWidget(self.season_notes_edit)

        save_button = QPushButton(t("club_advisor.panel.save_context"))
        save_button.clicked.connect(self.season_context_changed)
        layout.addWidget(save_button)

        return frame

    def season_context_values(self):
        return {
            "season_phase": self.season_phase_combo.currentData() or "unknown",
            "promotion_objective": self.promotion_objective_combo.currentData()
            or "welcome_if_natural",
            "current_competitiveness": self.competitiveness_combo.currentData() or "unknown",
            "bot_opponent_count": self.bot_opponents_spin.value(),
            "recent_major_signing": self.recent_signing_checkbox.isChecked(),
            "notes": self.season_notes_edit.text(),
        }

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
        self.operational_label.setText(sections.get("operational", ""))
        self.strategic_label.setText(sections.get("strategic", ""))
        self.promotion_readiness_label.setText(sections.get("promotion_readiness", ""))
        self.strengths_label.setText(sections.get("strengths", ""))
        self.risks_label.setText(sections.get("risks", ""))
        self.training_label.setText(sections.get("training", ""))
        self.squad_label.setText(sections.get("squad", ""))
        self.depth_label.setText(sections.get("depth", ""))
        self.warnings_label.setText(sections.get("warnings", ""))
        self.limitations_label.setText(sections.get("limitations", ""))
