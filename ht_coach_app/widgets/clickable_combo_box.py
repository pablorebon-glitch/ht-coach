from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QComboBox


class ClickableComboBox(QComboBox):
    """Combo box whose whole field opens the popup, including editable text."""

    def setEditable(self, editable):
        super().setEditable(editable)
        self._install_line_edit_filter()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.showPopup()

    def eventFilter(self, watched, event):
        if (
            watched is self.lineEdit()
            and event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.showPopup()
        return super().eventFilter(watched, event)

    def _install_line_edit_filter(self):
        line_edit = self.lineEdit()
        if line_edit is not None and getattr(self, "_line_edit_filter", None) is not line_edit:
            line_edit.installEventFilter(self)
            self._line_edit_filter = line_edit
