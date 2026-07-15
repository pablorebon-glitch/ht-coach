from PySide6.QtWidgets import QLabel

from ht_coach_app.views.base_page import BasePage


class OpponentsPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(
            "Opponents",
            "Manage saved opponents and scouting data.",
            parent
        )
        self.body_layout.addWidget(
            QLabel("Opponent management will be implemented in a later epic.")
        )

