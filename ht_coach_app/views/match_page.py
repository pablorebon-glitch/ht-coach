from PySide6.QtWidgets import QLabel

from ht_coach_app.views.base_page import BasePage


class MatchPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(
            "Match",
            "Prepare match analysis and optimization workflows.",
            parent
        )
        self.body_layout.addWidget(
            QLabel("Match analysis will be implemented in a later epic.")
        )

