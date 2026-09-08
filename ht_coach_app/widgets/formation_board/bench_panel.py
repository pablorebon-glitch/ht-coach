import json

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.core.localization import t
from ht_coach_app.widgets.formation_board.player_card import WORKSPACE_DRAG_MIME


class BenchPlayerCard(QPushButton):
    selected = Signal(str)
    preview_requested = Signal(str)
    starter_dropped = Signal(object, str)

    def __init__(self, player, formation_name, revision, parent=None):
        super().__init__(parent)
        self.player = player
        self._drag_start_position = None
        self._payload = {
            "source_type": "bench",
            "player_id": player.player_id,
            "formation_name": formation_name,
            "revision": revision,
        }
        self.setObjectName("benchPlayerCard")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptDrops(True)
        self.setToolTip(self._tooltip_text())
        self.clicked.connect(lambda: self.selected.emit(player.player_id))
        self._refresh()

    def _refresh(self):
        self.setProperty(
            "selected",
            "true" if self.player.is_selected else "false",
        )
        self.setProperty(
            "preview",
            "true" if self.player.is_incoming_preview else "false",
        )
        score = f"{self.player.score:.2f}"
        lines = [
            self.player.player_name,
            f"{self.player.best_position_abbreviation}  "
            f"{t('bench.score', score=score)}",
        ]
        if self.player.compatibility_label:
            lines.append(self.player.compatibility_label)
        self.setText("\n".join(lines))

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.preview_requested.emit(self.player.player_id)
            event.accept()
            return
        super().keyPressEvent(event)

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

    def dragEnterEvent(self, event):
        payload = self._payload_from_event(event)
        if payload.get("source_type") == "lineup":
            self.setProperty("dropTarget", "true")
            self.style().unpolish(self)
            self.style().polish(self)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._clear_drop_target()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        payload = self._payload_from_event(event)
        self._clear_drop_target()
        if payload.get("source_type") == "lineup":
            self.starter_dropped.emit(payload, self.player.player_id)
            event.acceptProposedAction()
            return
        event.ignore()

    def _clear_drop_target(self):
        self.setProperty("dropTarget", "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def _tooltip_text(self):
        parts = [
            self.player.player_name,
            self.player.best_position_label,
            t("bench.score", score=f"{self.player.score:.2f}"),
            self.player.compatibility_label,
        ]
        return " | ".join(part for part in parts if part)

    @staticmethod
    def _payload_from_event(event):
        data = event.mimeData().data(WORKSPACE_DRAG_MIME)
        try:
            return json.loads(bytes(data).decode("utf-8"))
        except (TypeError, ValueError, UnicodeDecodeError):
            return {}


class BenchPanel(QFrame):
    player_selected = Signal(str)
    preview_requested = Signal(str)
    starter_dropped_on_player = Signal(object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("benchPanel")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(t("bench.title"))
        self.title_label.setObjectName("formationBoardTitle")
        self.count_label = QLabel("")
        self.count_label.setObjectName("formationBoardMeta")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.count_label)
        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("benchScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll, 1)

    def set_players(self, players, formation_name, revision, state_message=""):
        self._clear()
        if state_message:
            self.count_label.setText("")
            message = QLabel(state_message)
            message.setWordWrap(True)
            message.setObjectName("playerInspectorMeta")
            self.content_layout.addWidget(message)
            self.content_layout.addStretch(1)
            return

        self.count_label.setText(t("bench.players", count=len(players)))
        if not players:
            message = QLabel(t("bench.empty"))
            message.setWordWrap(True)
            message.setObjectName("playerInspectorMeta")
            self.content_layout.addWidget(message)
            self.content_layout.addStretch(1)
            return

        for player in players:
            card = BenchPlayerCard(
                player,
                formation_name,
                revision,
                self.content,
            )
            card.selected.connect(self.player_selected)
            card.preview_requested.connect(self.preview_requested)
            card.starter_dropped.connect(self.starter_dropped_on_player)
            self.content_layout.addWidget(card)
        self.content_layout.addStretch(1)

    def _clear(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
