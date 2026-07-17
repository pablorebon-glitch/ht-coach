from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

from ht_coach_app.widgets.formation_board.formation_board_styles import (
    PITCH_BACKGROUND,
    PITCH_BACKGROUND_ALT,
    PITCH_LINES,
)
from ht_coach_app.widgets.formation_board.layout_metrics import (
    PITCH_ASPECT_RATIO,
    PITCH_GOAL_DEPTH,
    PITCH_OUTER_MARGIN,
    PLAYER_CARD_LINE_GAP_RATIO,
    PLAYER_CARD_MAX_HEIGHT,
    PLAYER_CARD_MAX_WIDTH,
    PLAYER_CARD_MIN_HEIGHT,
    PLAYER_CARD_MIN_WIDTH,
)
from ht_coach_app.widgets.formation_board.player_card import PlayerCard


class PitchWidget(QWidget):
    player_selected = Signal(str)
    empty_area_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._board = None
        self._slot_widgets = []
        self.setMinimumSize(260, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)

    def sizeHint(self):
        return QSize(420, 600)

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
                widget.selected.connect(self.player_selected)

            widget.show()
            self._slot_widgets.append((slot, widget))

        self._position_slot_widgets()
        self.update()

    def pitch_rect(self):
        available = QRectF(
            PITCH_OUTER_MARGIN + PITCH_GOAL_DEPTH,
            PITCH_OUTER_MARGIN + PITCH_GOAL_DEPTH,
            max(1, self.width() - 2 * (PITCH_OUTER_MARGIN + PITCH_GOAL_DEPTH)),
            max(1, self.height() - 2 * (PITCH_OUTER_MARGIN + PITCH_GOAL_DEPTH)),
        )
        available_ratio = available.width() / max(1.0, available.height())

        if available_ratio > PITCH_ASPECT_RATIO:
            height = available.height()
            width = height * PITCH_ASPECT_RATIO
        else:
            width = available.width()
            height = width / PITCH_ASPECT_RATIO

        return QRectF(
            available.center().x() - width / 2,
            available.center().y() - height / 2,
            width,
            height,
        )

    def goal_rects(self):
        rect = self.pitch_rect()
        goal_width = rect.width() * 0.26
        left = rect.center().x() - goal_width / 2
        return (
            QRectF(left, rect.top() - PITCH_GOAL_DEPTH, goal_width, PITCH_GOAL_DEPTH),
            QRectF(left, rect.bottom(), goal_width, PITCH_GOAL_DEPTH),
        )

    def card_geometries(self):
        return tuple(widget.geometry() for _, widget in self._slot_widgets)

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

        rect = self.pitch_rect()
        painter.fillRect(rect, QColor(PITCH_BACKGROUND))

        stripe_height = rect.height() / 8
        for stripe in range(0, 8, 2):
            painter.fillRect(
                QRectF(
                    rect.left(),
                    rect.top() + stripe_height * stripe,
                    rect.width(),
                    stripe_height,
                ),
                QColor(PITCH_BACKGROUND_ALT),
            )

        line_width = max(1.0, min(2.0, rect.width() / 260))
        painter.setPen(QPen(QColor(PITCH_LINES), line_width))
        painter.drawRect(rect)

        halfway_y = rect.center().y()
        painter.drawLine(rect.left(), halfway_y, rect.right(), halfway_y)
        circle_radius = rect.width() * 0.12
        painter.drawEllipse(rect.center(), circle_radius, circle_radius)
        painter.setBrush(QColor(PITCH_LINES))
        painter.drawEllipse(rect.center(), line_width * 1.5, line_width * 1.5)
        painter.setBrush(Qt.NoBrush)

        self._draw_end_markings(painter, rect, top=True)
        self._draw_end_markings(painter, rect, top=False)
        self._draw_corner_arcs(painter, rect)

    def _draw_end_markings(self, painter, rect, top):
        penalty_width = rect.width() * 0.62
        penalty_height = rect.height() * 0.16
        goal_area_width = rect.width() * 0.30
        goal_area_height = rect.height() * 0.065
        penalty_left = rect.center().x() - penalty_width / 2
        goal_area_left = rect.center().x() - goal_area_width / 2

        if top:
            penalty_top = rect.top()
            goal_area_top = rect.top()
            spot_y = rect.top() + rect.height() * 0.105
        else:
            penalty_top = rect.bottom() - penalty_height
            goal_area_top = rect.bottom() - goal_area_height
            spot_y = rect.bottom() - rect.height() * 0.105

        painter.drawRect(QRectF(penalty_left, penalty_top, penalty_width, penalty_height))
        painter.drawRect(
            QRectF(goal_area_left, goal_area_top, goal_area_width, goal_area_height)
        )
        painter.setBrush(QColor(PITCH_LINES))
        painter.drawEllipse(QPointF(rect.center().x(), spot_y), 1.5, 1.5)
        painter.setBrush(Qt.NoBrush)

        goal = self.goal_rects()[0 if top else 1]
        painter.drawRect(goal)

    def _draw_corner_arcs(self, painter, rect):
        diameter = max(8.0, rect.width() * 0.04)
        corners = (
            (rect.left(), rect.top(), 0),
            (rect.right() - diameter, rect.top(), 90 * 16),
            (rect.left(), rect.bottom() - diameter, 270 * 16),
            (rect.right() - diameter, rect.bottom() - diameter, 180 * 16),
        )
        for left, top, start_angle in corners:
            painter.drawArc(
                QRectF(left, top, diameter, diameter),
                start_angle,
                90 * 16,
            )

    def _position_slot_widgets(self):
        rect = self.pitch_rect()
        card_width, card_height = self._card_size(rect)

        for slot, widget in self._slot_widgets:
            x = rect.left() + rect.width() * slot.normalized_x
            y = rect.top() + rect.height() * slot.normalized_y
            left = max(rect.left(), min(x - card_width / 2, rect.right() - card_width))
            top = max(rect.top(), min(y - card_height / 2, rect.bottom() - card_height))
            widget.setGeometry(int(left), int(top), card_width, card_height)

    def _card_size(self, rect):
        minimum_gap = self._minimum_line_gap(rect)
        width_from_pitch = int(rect.width() * 0.22)
        width_from_gap = int(minimum_gap * PLAYER_CARD_LINE_GAP_RATIO)
        card_width = max(
            PLAYER_CARD_MIN_WIDTH,
            min(PLAYER_CARD_MAX_WIDTH, width_from_pitch, width_from_gap),
        )
        card_height = max(
            PLAYER_CARD_MIN_HEIGHT,
            min(PLAYER_CARD_MAX_HEIGHT, int(card_width * 0.72)),
        )
        return card_width, card_height

    def _minimum_line_gap(self, rect):
        if self._board is None:
            return rect.width()

        gaps = []
        lines = {}
        for slot in self._board.slots:
            lines.setdefault(slot.line, []).append(slot.normalized_x)

        for positions in lines.values():
            positions.sort()
            gaps.extend(
                rect.width() * (right - left)
                for left, right in zip(positions, positions[1:])
            )

        return min(gaps) if gaps else rect.width() * 0.5

    def _clear_slot_widgets(self):
        for _, widget in self._slot_widgets:
            widget.setParent(None)
            widget.deleteLater()

        self._slot_widgets = []
