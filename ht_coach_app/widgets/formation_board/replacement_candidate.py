import json

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QApplication, QPushButton

from ht_coach_app.widgets.formation_board.player_card import WORKSPACE_DRAG_MIME


class ReplacementCandidateButton(QPushButton):
    def __init__(self, candidate, formation_name, revision, parent=None):
        super().__init__(
            f"{candidate.player_name}  |  "
            f"Score {candidate.score:.2f}  "
            f"({candidate.score_difference:+.2f})",
            parent,
        )
        self.candidate = candidate
        self._drag_start_position = None
        self._payload = {
            "source_type": "candidate",
            "player_id": candidate.player_id,
            "formation_name": formation_name,
            "revision": revision,
        }

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

        mime = QMimeData()
        mime.setData(
            WORKSPACE_DRAG_MIME,
            json.dumps(self._payload).encode("utf-8"),
        )
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)
