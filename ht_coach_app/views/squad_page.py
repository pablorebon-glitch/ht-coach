from PySide6.QtWidgets import QLabel

from ht_coach_app.views.base_page import BasePage


class SquadPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(
            "Squad",
            "Load and inspect the player squad without changing engine behavior.",
            parent
        )
        self.body_layout.addWidget(
            QLabel("Squad tools will be implemented in a later epic.")
        )

