from PySide6.QtWidgets import QLabel

from ht_coach_app.views.base_page import BasePage


class DashboardPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(
            "Dashboard",
            "Workspace overview for roster, opponent, and latest recommendation.",
            parent
        )
        self.body_layout.addWidget(
            QLabel("Dashboard content will be implemented in a later epic.")
        )

