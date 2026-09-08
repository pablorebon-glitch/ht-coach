from dataclasses import dataclass
import json

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
from ht_coach_app.widgets.formation_board.player_card import WORKSPACE_DRAG_MIME


@dataclass(frozen=True)
class CornerArcGeometry:
    name: str
    anchor: QPointF
    rect: QRectF
    start_angle: int
    span_angle: int


@dataclass(frozen=True)
class PitchGeometry:
    external_bounds: QRectF
    field_rect: QRectF
    top_goal: QRectF
    bottom_goal: QRectF
    penalty_areas: tuple[QRectF, QRectF]
    goal_areas: tuple[QRectF, QRectF]
    center_circle: QRectF
    corner_arcs: tuple[CornerArcGeometry, ...]


class PitchWidget(QWidget):
    player_selected = Signal(str)
    empty_area_clicked = Signal()
    player_dropped = Signal(object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._board = None
        self._slot_widgets = []
        self._slot_widget_by_id = {}
        self._revision = 0
        self.setMinimumSize(280, 430)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)

    def sizeHint(self):
        return QSize(430, 620)

    def set_board(self, board, revision=0):
        self._board = board
        self._revision = revision

        if board is None:
            self._clear_slot_widgets()
            self.update()
            return

        active_slot_ids = set()
        slot_widgets = []
        for slot in board.slots:
            active_slot_ids.add(slot.slot_id)
            widget = self._widget_for_slot(slot)

            widget.show()
            slot_widgets.append((slot, widget))

        for slot_id, widget in tuple(self._slot_widget_by_id.items()):
            if slot_id not in active_slot_ids:
                widget.setParent(None)
                widget.deleteLater()
                del self._slot_widget_by_id[slot_id]

        self._slot_widgets = slot_widgets
        self._position_slot_widgets()
        self.update()

    def pitch_rect(self):
        return self.geometry_model().field_rect

    def geometry_model(self):
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

        field_rect = QRectF(
            available.center().x() - width / 2,
            available.center().y() - height / 2,
            width,
            height,
        )
        return self._build_geometry(field_rect)

    def goal_rects(self):
        geometry = self.geometry_model()
        return (geometry.top_goal, geometry.bottom_goal)

    def corner_arcs(self):
        return self.geometry_model().corner_arcs

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

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(WORKSPACE_DRAG_MIME):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event):
        slot_id = self._slot_id_at(event.position().toPoint())
        if slot_id:
            self._set_drop_target(slot_id)
            event.acceptProposedAction()
            return
        self._set_drop_target("")
        event.ignore()

    def dragLeaveEvent(self, event):
        self._set_drop_target("")
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        slot_id = self._slot_id_at(event.position().toPoint())
        payload = self._payload_from_event(event)
        self._set_drop_target("")
        if slot_id and payload:
            self.player_dropped.emit(payload, slot_id)
            event.acceptProposedAction()
            return
        event.ignore()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        geometry = self.geometry_model()
        rect = geometry.field_rect
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
        painter.drawEllipse(geometry.center_circle)
        painter.setBrush(QColor(PITCH_LINES))
        painter.drawEllipse(rect.center(), line_width * 1.5, line_width * 1.5)
        painter.setBrush(Qt.NoBrush)

        self._draw_end_markings(painter, geometry, top=True)
        self._draw_end_markings(painter, geometry, top=False)
        self._draw_corner_arcs(painter, geometry)

    def _draw_end_markings(self, painter, geometry, top):
        rect = geometry.field_rect
        penalty_area = geometry.penalty_areas[0 if top else 1]
        goal_area = geometry.goal_areas[0 if top else 1]
        spot_y = (
            rect.top() + rect.height() * 0.105
            if top
            else rect.bottom() - rect.height() * 0.105
        )

        painter.drawRect(penalty_area)
        painter.drawRect(goal_area)
        painter.setBrush(QColor(PITCH_LINES))
        painter.drawEllipse(QPointF(rect.center().x(), spot_y), 1.5, 1.5)
        painter.setBrush(Qt.NoBrush)

        goal = geometry.top_goal if top else geometry.bottom_goal
        painter.drawRect(goal)

    def _draw_corner_arcs(self, painter, geometry):
        for arc in geometry.corner_arcs:
            painter.drawArc(
                arc.rect,
                arc.start_angle,
                arc.span_angle,
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
        self._slot_widget_by_id = {}

    def _widget_for_slot(self, slot):
        current = self._slot_widget_by_id.get(slot.slot_id)
        if slot.player is None:
            if current is None or isinstance(current, PlayerCard):
                if current is not None:
                    current.setParent(None)
                    current.deleteLater()
                current = QLabel(slot.position_label, self)
                current.setObjectName("emptySlot")
                current.setAlignment(Qt.AlignCenter)
                self._slot_widget_by_id[slot.slot_id] = current
            else:
                current.setText(slot.position_label)
            current.setToolTip(
                f"Empty {slot.side_label} {slot.position_label} slot"
            )
            return current

        if current is None or not isinstance(current, PlayerCard):
            if current is not None:
                current.setParent(None)
                current.deleteLater()
            current = PlayerCard(slot.player, self)
            current.selected.connect(self.player_selected)
            self._slot_widget_by_id[slot.slot_id] = current
        else:
            current.update_player(slot.player)
        current.set_drag_context(
            self._board.formation_name,
            slot.slot_id,
            self._revision,
        )
        return current

    def _slot_id_at(self, point):
        child = self.childAt(point)
        for slot, widget in self._slot_widgets:
            if widget is child:
                return slot.slot_id
        return ""

    def _set_drop_target(self, slot_id):
        for slot, widget in self._slot_widgets:
            widget.setProperty(
                "dropTarget",
                "true" if slot.slot_id == slot_id else "false",
            )
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    @staticmethod
    def _payload_from_event(event):
        data = event.mimeData().data(WORKSPACE_DRAG_MIME)
        try:
            return json.loads(bytes(data).decode("utf-8"))
        except (TypeError, ValueError, UnicodeDecodeError):
            return {}

    def _build_geometry(self, rect):
        goal_width = rect.width() * 0.26
        goal_left = rect.center().x() - goal_width / 2
        top_goal = QRectF(
            goal_left,
            rect.top() - PITCH_GOAL_DEPTH,
            goal_width,
            PITCH_GOAL_DEPTH,
        )
        bottom_goal = QRectF(
            goal_left,
            rect.bottom(),
            goal_width,
            PITCH_GOAL_DEPTH,
        )
        penalty_width = rect.width() * 0.62
        penalty_height = rect.height() * 0.16
        goal_area_width = rect.width() * 0.30
        goal_area_height = rect.height() * 0.065
        penalty_left = rect.center().x() - penalty_width / 2
        goal_area_left = rect.center().x() - goal_area_width / 2
        top_penalty = QRectF(
            penalty_left,
            rect.top(),
            penalty_width,
            penalty_height,
        )
        bottom_penalty = QRectF(
            penalty_left,
            rect.bottom() - penalty_height,
            penalty_width,
            penalty_height,
        )
        top_goal_area = QRectF(
            goal_area_left,
            rect.top(),
            goal_area_width,
            goal_area_height,
        )
        bottom_goal_area = QRectF(
            goal_area_left,
            rect.bottom() - goal_area_height,
            goal_area_width,
            goal_area_height,
        )
        circle_radius = rect.width() * 0.12
        center_circle = QRectF(
            rect.center().x() - circle_radius,
            rect.center().y() - circle_radius,
            circle_radius * 2,
            circle_radius * 2,
        )
        corner_arcs = self._corner_arcs_for(rect)
        external_bounds = rect.united(top_goal).united(bottom_goal).adjusted(
            -PITCH_OUTER_MARGIN,
            -PITCH_OUTER_MARGIN,
            PITCH_OUTER_MARGIN,
            PITCH_OUTER_MARGIN,
        )
        return PitchGeometry(
            external_bounds=external_bounds,
            field_rect=rect,
            top_goal=top_goal,
            bottom_goal=bottom_goal,
            penalty_areas=(top_penalty, bottom_penalty),
            goal_areas=(top_goal_area, bottom_goal_area),
            center_circle=center_circle,
            corner_arcs=corner_arcs,
        )

    @staticmethod
    def _corner_arcs_for(rect):
        radius = max(5.0, rect.width() * 0.025)
        diameter = radius * 2

        def arc(name, x, y, start):
            return CornerArcGeometry(
                name=name,
                anchor=QPointF(x, y),
                rect=QRectF(
                    x - radius,
                    y - radius,
                    diameter,
                    diameter,
                ),
                start_angle=start * 16,
                span_angle=90 * 16,
            )

        return (
            arc("top_left", rect.left(), rect.top(), 270),
            arc("top_right", rect.right(), rect.top(), 180),
            arc("bottom_left", rect.left(), rect.bottom(), 0),
            arc("bottom_right", rect.right(), rect.bottom(), 90),
        )
