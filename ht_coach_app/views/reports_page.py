from PySide6.QtWidgets import QLabel

from ht_coach_app.core.localization import t
from ht_coach_app.views.base_page import BasePage


class ReportsPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(
            t("reports.title"),
            t("reports.subtitle"),
            parent
        )
        self.placeholder_label = QLabel(t("reports.placeholder"))
        self.body_layout.addWidget(self.placeholder_label)

    def retranslate_ui(self):
        self.set_page_text(
            t("reports.title"),
            t("reports.subtitle"),
        )
        self.placeholder_label.setText(t("reports.placeholder"))
