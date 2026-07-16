from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QPushButton


class PlayerCard(QPushButton):
    selected = Signal(str)

    def __init__(self, player, parent=None):
        super().__init__(parent)
        self.player = player
        self.setObjectName("playerCard")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(self._tooltip_text())
        self.clicked.connect(
            lambda: self.selected.emit(self.player.player_id)
        )
        self.refresh()

    def refresh(self):
        order = self.player.order_label
        if self.player.order_side_label:
            order = f"{order} {self.player.order_side_label}"

        self.setText(
            "\n".join(
                [
                    self.player.display_name,
                    self.player.position_abbreviation,
                    order or "Normal",
                ]
            )
        )
        self.setProperty(
            "selected",
            "true" if self.player.is_selected else "false"
        )
        self.setProperty(
            "recommended",
            "true" if self.player.is_recommended else "false"
        )
        self.style().unpolish(self)
        self.style().polish(self)

    def _tooltip_text(self):
        parts = [
            self.player.player_name,
            self.player.position_label,
            self.player.side_label,
            self.player.order_label,
        ]

        if self.player.order_side_label:
            parts.append(
                f"Order side: {self.player.order_side_label}"
            )

        return " | ".join(
            part for part in parts if part
        )
