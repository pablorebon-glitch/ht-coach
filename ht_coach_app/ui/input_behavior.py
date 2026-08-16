from PySide6.QtCore import QObject, QPoint, QPointF, QEvent, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QSlider,
    QTabBar,
    QWidget,
)


class PageOnlyWheelEventFilter(QObject):
    """Keep ordinary mouse-wheel input assigned to page scrolling.

    Closed value controls should not mutate simply because the pointer happens to
    hover over them while the person scrolls a long workspace page. Explicit
    popups and real scroll areas keep their own native wheel handling.
    """

    def eventFilter(self, watched, event):
        if event.type() != QEvent.Type.Wheel:
            return False
        if not isinstance(watched, QWidget):
            return False
        protected = self._protected_value_widget(watched)
        if protected is None:
            return False
        return self._forward_to_scroll_area(protected, event)

    def _protected_value_widget(self, widget):
        current = widget
        while current is not None:
            if isinstance(current, QComboBox):
                view = current.view()
                if view is not None and view.isVisible():
                    return None
                return current
            if isinstance(current, (QTabBar, QAbstractSpinBox, QSlider)):
                return current
            if isinstance(current, QAbstractScrollArea):
                return None
            current = current.parentWidget()
        return None

    def _forward_to_scroll_area(self, widget, event):
        scroll_area = self._target_scroll_area(widget)
        if scroll_area is None:
            event.ignore()
            return True

        viewport = scroll_area.viewport()
        local_pos = viewport.mapFromGlobal(
            event.globalPosition().toPoint()
        )
        forwarded = QWheelEvent(
            QPointF(local_pos),
            event.globalPosition(),
            event.pixelDelta(),
            event.angleDelta(),
            event.buttons(),
            event.modifiers(),
            event.phase(),
            event.inverted(),
            event.source(),
        )
        vertical = scroll_area.verticalScrollBar()
        before_scroll = vertical.value() if vertical is not None else None
        QApplication.sendEvent(viewport, forwarded)
        after_scroll = vertical.value() if vertical is not None else None
        if not forwarded.isAccepted() or after_scroll == before_scroll:
            self._fallback_scroll(scroll_area, event)
        event.accept()
        return True

    def _target_scroll_area(self, widget):
        outer_match_scroll = None
        nearest_scroll = None
        current = widget.parentWidget()
        while current is not None:
            if isinstance(current, QAbstractScrollArea):
                nearest_scroll = nearest_scroll or current
                if current.objectName() == "matchPageScroll":
                    outer_match_scroll = current
                    break
            current = current.parentWidget()
        return outer_match_scroll or nearest_scroll

    def _fallback_scroll(self, scroll_area, event):
        vertical = scroll_area.verticalScrollBar()
        if vertical is None:
            return
        delta = event.angleDelta().y()
        if delta == 0:
            delta = event.pixelDelta().y()
        if delta == 0:
            return
        steps = delta / 120.0
        amount = max(vertical.singleStep(), 20) * steps * 3
        vertical.setValue(
            max(
                vertical.minimum(),
                min(vertical.maximum(), int(vertical.value() - amount)),
            )
        )


def install_page_only_wheel_policy(app=None):
    app = app or QApplication.instance()
    if app is None:
        return None
    existing = getattr(app, "_ht_coach_page_only_wheel_filter", None)
    if existing is not None:
        return existing
    event_filter = PageOnlyWheelEventFilter(app)
    app.installEventFilter(event_filter)
    app._ht_coach_page_only_wheel_filter = event_filter
    return event_filter
