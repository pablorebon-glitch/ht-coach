from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel, QWidget

from ht_coach_app.widgets.formation_board.formation_board_styles import (
    PITCH_BACKGROUND,
    PITCH_BACKGROUND_ALT,
    PITCH_LINES,
)
from ht_coach_app.widgets.formation_board.player_card import PlayerCard


class PitchWidget(QWidget):
    player_selected = Signal(str)
    empty_area_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._board = None
        self._slot_widgets = []
        self.setMinimumSize(420, 620)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_board(self, board):
        self._board = board
        self._clear_slot_widgets()

        if board is None:
            self.update()
            return

        for slot in board.slots:
            if slot.player is None:
                widget = QLabel(slot.position_label, self)
                widget.setObjectName("emptySlot")
                widget.setAlignment(Qt.AlignCenter)
                widget.setToolTip(
                    f"Empty {slot.side_label} {slot.position_label} slot"
                )
            else:
                widget = PlayerCard(slot.player, self)
                widget.selected.connect(
                    self.player_selected
                )

            widget.show()
            self._slot_widgets.append(
                (slot, widget)
            )

        self._position_slot_widgets()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_slot_widgets()

    def mousePressEvent(self, event):
        child = self.childAt(event.position().toPoint())
        if child is None or child is self:
            self.empty_area_clicked.emit()

        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.empty_area_clicked.emit()
            event.accept()
            return

        super().keyPressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self._pitch_rect()
        painter.fillRect(rect, QColor(PITCH_BACKGROUND))

        stripe_height = rect.height() / 8
        painter.fillRect(
            QRectF(rect.left(), rect.top(), rect.width(), stripe_height),
            QColor(PITCH_BACKGROUND_ALT),
        )
        painter.fillRect(
            QRectF(
                rect.left(),
                rect.top() + stripe_height * 4,
                rect.width(),
                stripe_height,
            ),
            QColor(PITCH_BACKGROUND_ALT),
        )

        pen = QPen(QColor(PITCH_LINES), 2)
        painter.setPen(pen)
        painter.drawRect(rect)

        halfway_y = rect.top() + rect.height() * 0.50
        painter.drawLine(
            rect.left(),
            halfway_y,
            rect.right(),
            halfway_y,
        )
        painter.drawEllipse(
            rect.center(),
            rect.width() * 0.12,
            rect.width() * 0.12,
        )

        self._draw_penalty_area(painter, rect, top=True)
        self._draw_penalty_area(painter, rect, top=False)

    def _draw_penalty_area(self, painter, rect, top):
        area_width = rect.width() * 0.56
        area_height = rect.height() * 0.16
        goal_width = rect.width() * 0.28
        goal_height = rect.height() * 0.06
        left = rect.center().x() - area_width / 2
        goal_left = rect.center().x() - goal_width / 2

        if top:
            area_top = rect.top()
            goal_top = rect.top()
        else:
            area_top = rect.bottom() - area_height
            goal_top = rect.bottom() - goal_height

        painter.drawRect(
            QRectF(left, area_top, area_width, area_height)
        )
        painter.drawRect(
            QRectF(goal_left, goal_top, goal_width, goal_height)
        )

    def _pitch_rect(self):
        margin = 12
        return QRectF(
            margin,
            margin,
            max(1, self.width() - margin * 2),
            max(1, self.height() - margin * 2),
        )

    def _position_slot_widgets(self):
        rect = self._pitch_rect()
        card_width = min(132, max(92, int(rect.width() * 0.23)))
        card_height = 64

        for slot, widget in self._slot_widgets:
            x = rect.left() + rect.width() * slot.normalized_x
            y = rect.top() + rect.height() * slot.normalized_y
            widget.setGeometry(
                int(x - card_width / 2),
                int(y - card_height / 2),
                card_width,
                card_height,
            )

    def _clear_slot_widgets(self):
        for _, widget in self._slot_widgets:
            widget.setParent(None)
            widget.deleteLater()

        self._slot_widgets = []
