from PySide6.QtWidgets import QFrame, QVBoxLayout

from ht_coach_app.ui.design_system import spacing


class Card(QFrame):
    def __init__(self, variant="default", selected=False, parent=None):
        super().__init__(parent)
        self.setObjectName("dsCard")
        self.setProperty("variant", variant)
        self.setProperty("selected", "true" if selected else "false")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(*spacing.PANEL_MARGINS)
        self.layout.setSpacing(spacing.SM)

    def set_selected(self, selected):
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)
