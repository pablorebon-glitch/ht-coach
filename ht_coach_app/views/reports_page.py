from PySide6.QtWidgets import QLabel

from ht_coach_app.views.base_page import BasePage


class ReportsPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(
            "Reports",
            "Review and export future recommendations and match summaries.",
            parent
        )
        self.body_layout.addWidget(
            QLabel("Reports will be implemented in a later epic.")
        )

