from PySide6.QtWidgets import QLabel

from ht_coach_app.views.base_page import BasePage


class SettingsPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(
            "Settings",
            "Configure desktop preferences and local application paths.",
            parent
        )
        self.body_layout.addWidget(
            QLabel("Settings will be implemented in a later epic.")
        )

