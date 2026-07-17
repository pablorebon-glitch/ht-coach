from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics
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
        self.setProperty(
            "selected",
            "true" if self.player.is_selected else "false"
        )
        self.setProperty(
            "recommended",
            "true" if self.player.is_recommended else "false"
        )
        self.setProperty(
            "modified",
            "true" if self.player.is_modified else "false"
        )
        self.setProperty(
            "preview",
            "true" if self.player.is_replacement_preview else "false"
        )
        self.style().unpolish(self)
        self.style().polish(self)
        self._update_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_text()

    def _update_text(self):
        order = self.player.order_label
        if self.player.order_side_label:
            order = f"{order} {self.player.order_side_label}"

        available_width = max(1, self.width() - 10)
        metrics = QFontMetrics(self.font())
        display_name = metrics.elidedText(
            self.player.player_name,
            Qt.ElideRight,
            available_width,
        )
        self.setText(
            "\n".join(
                [
                    self._name_line(display_name),
                    self.player.position_abbreviation,
                    order or "Normal",
                ]
            )
        )

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

        if self.player.is_modified:
            parts.append("Workspace replacement")

        return " | ".join(
            part for part in parts if part
        )

    def _name_line(self, display_name):
        if self.player.is_modified:
            return f"* {display_name}"
        return display_name
