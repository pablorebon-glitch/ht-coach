from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.core.localization import t


class CollapsibleHeaderButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("collapsibleSectionHeader")
        self.setFlat(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def keyPressEvent(self, event):
        if event.key() in {Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space}:
            self.click()
            event.accept()
            return
        super().keyPressEvent(event)


class CollapsibleArrowLabel(QLabel):
    def __init__(self, section, parent=None):
        super().__init__(parent)
        self._section = section
        self.setObjectName("collapsibleArrow")
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        self._section.toggle()
        event.accept()


class CollapsibleSection(QFrame):
    toggled = Signal(str, bool)

    def __init__(
        self,
        title,
        body_widget=None,
        state_key="",
        expanded=True,
        summary="",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("collapsibleSection")
        self.state_key = state_key
        self._title = title
        self._summary = summary
        self._expanded = bool(expanded)
        self._body_widget = None
        self._build()
        self.set_body_widget(body_widget or QWidget())
        self.set_expanded(self._expanded, emit=False)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header_button = CollapsibleHeaderButton()
        self.header_button.clicked.connect(self.toggle)
        header_layout = QHBoxLayout(self.header_button)
        header_layout.setContentsMargins(10, 7, 10, 7)
        header_layout.setSpacing(8)

        self.arrow_label = CollapsibleArrowLabel(self)
        header_layout.addWidget(self.arrow_label)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)
        self.title_label = QLabel(self._title)
        self.title_label.setObjectName("sectionTitle")
        text_layout.addWidget(self.title_label)

        self.summary_label = QLabel(self._summary)
        self.summary_label.setObjectName("sectionSubtitle")
        self.summary_label.setWordWrap(True)
        text_layout.addWidget(self.summary_label)

        header_layout.addLayout(text_layout, 1)
        root.addWidget(self.header_button)

        self.body_host = QWidget()
        self.body_layout = QVBoxLayout(self.body_host)
        self.body_layout.setContentsMargins(10, 0, 10, 10)
        self.body_layout.setSpacing(6)
        root.addWidget(self.body_host)

    def toggle(self):
        self.set_expanded(not self._expanded)

    def is_expanded(self):
        return self._expanded

    def set_expanded(self, expanded, emit=True):
        expanded = bool(expanded)
        changed = expanded != self._expanded
        self._expanded = expanded
        self.body_host.setVisible(expanded)
        self.arrow_label.setText("v" if expanded else ">")
        self.header_button.setAccessibleName(self._accessible_name())
        self.header_button.setToolTip(
            t("common.collapse_section")
            if expanded
            else t("common.expand_section")
        )
        self.header_button.setProperty("expanded", expanded)
        self.header_button.style().unpolish(self.header_button)
        self.header_button.style().polish(self.header_button)
        if emit and changed:
            self.toggled.emit(self.state_key, expanded)

    def set_title(self, title):
        self._title = str(title or "")
        self.title_label.setText(self._title)
        self.header_button.setAccessibleName(self._accessible_name())

    def set_summary(self, summary):
        self._summary = str(summary or "")
        self.summary_label.setText(self._summary)
        self.summary_label.setVisible(bool(self._summary))
        self.header_button.setAccessibleName(self._accessible_name())

    def set_body_widget(self, widget):
        if widget is self._body_widget:
            return
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            old = item.widget()
            if old is not None and old is not widget:
                old.setParent(None)
        self._body_widget = widget
        if widget is not None:
            self.body_layout.addWidget(widget)

    def body_widget(self):
        return self._body_widget

    def summary(self):
        return self._summary

    def retranslate(self, title=None, summary=None):
        if title is not None:
            self.set_title(title)
        if summary is not None:
            self.set_summary(summary)
        self.set_expanded(self._expanded, emit=False)

    def _accessible_name(self):
        action = (
            t("common.collapse_section")
            if self._expanded
            else t("common.expand_section")
        )
        summary = f" - {self._summary}" if self._summary else ""
        return f"{action}: {self._title}{summary}"
