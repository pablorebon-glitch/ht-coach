import json

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag, QFontMetrics
from PySide6.QtWidgets import QApplication, QPushButton


WORKSPACE_DRAG_MIME = "application/x-ht-coach-workspace-player"


class PlayerCard(QPushButton):
    selected = Signal(str)

    def __init__(self, player, parent=None):
        super().__init__(parent)
        self.player = player
        self._drag_start_position = None
        self._drag_context = {}
        self.setObjectName("playerCard")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(self._tooltip_text())
        self.clicked.connect(
            lambda: self.selected.emit(self.player.player_id)
        )
        self.refresh()

    def set_drag_context(self, formation_name, slot_id, revision):
        self._drag_context = {
            "source_type": "lineup",
            "player_id": self.player.player_id,
            "source_slot_id": slot_id,
            "formation_name": formation_name,
            "revision": revision,
        }

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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(event)
            return
        if self._drag_start_position is None:
            super().mouseMoveEvent(event)
            return
        distance = (
            event.position().toPoint() - self._drag_start_position
        ).manhattanLength()
        if distance < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        self._start_drag()

    def _start_drag(self):
        if not self._drag_context:
            return

        mime = QMimeData()
        mime.setData(
            WORKSPACE_DRAG_MIME,
            json.dumps(self._drag_context).encode("utf-8"),
        )
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)

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
