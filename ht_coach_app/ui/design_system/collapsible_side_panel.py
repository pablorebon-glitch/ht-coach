from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from ht_coach_app.core.localization import t


class CollapsibleSidePanel(QFrame):
    toggled = Signal(str, bool)

    def __init__(
        self,
        title,
        state_key,
        content_widget=None,
        expanded=True,
        collapsed_width=34,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("collapsibleSidePanel")
        self.state_key = state_key
        self._title = title
        self._expanded = bool(expanded)
        self._collapsed_width = int(collapsed_width)
        self._content_widget = None
        self._settings = QSettings("HT Coach", "HT Coach Alpha")
        self._build()
        self.set_content_widget(content_widget or QWidget())
        persisted = self._settings.value(self._settings_key(), None)
        if persisted is not None:
            self._expanded = str(persisted).lower() in {"1", "true", "yes"}
        self.set_expanded(self._expanded, emit=False)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = QFrame()
        self.header.setObjectName("collapsibleSidePanelHeader")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(6, 6, 6, 6)
        header_layout.setSpacing(4)

        self.toggle_button = QToolButton()
        self.toggle_button.setObjectName("collapsibleSidePanelToggle")
        self.toggle_button.setAutoRaise(True)
        self.toggle_button.setFocusPolicy(Qt.StrongFocus)
        self.toggle_button.clicked.connect(self.toggle)
        header_layout.addWidget(self.toggle_button)

        self.title_label = QLabel(self._title)
        self.title_label.setObjectName("formationBoardTitle")
        header_layout.addWidget(self.title_label, 1)
        root.addWidget(self.header)

        self.content_host = QWidget()
        self.content_layout = QVBoxLayout(self.content_host)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        root.addWidget(self.content_host, 1)

    def set_content_widget(self, widget):
        if widget is self._content_widget:
            return
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            old = item.widget()
            if old is not None and old is not widget:
                old.setParent(None)
        self._content_widget = widget
        if widget is not None:
            self.content_layout.addWidget(widget)

    def content_widget(self):
        return self._content_widget

    def set_state_key(self, state_key, default_expanded=True):
        self.state_key = str(state_key or "")
        persisted = self._settings.value(self._settings_key(), None)
        expanded = (
            bool(default_expanded)
            if persisted is None
            else str(persisted).lower() in {"1", "true", "yes"}
        )
        self.set_expanded(expanded, emit=False)

    def is_expanded(self):
        return self._expanded

    def toggle(self):
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded, emit=True):
        expanded = bool(expanded)
        changed = expanded != self._expanded
        self._expanded = expanded
        self.content_host.setVisible(expanded)
        self.title_label.setVisible(expanded)
        self.toggle_button.setArrowType(Qt.RightArrow if not expanded else Qt.LeftArrow)
        action = t("common.collapse_section") if expanded else t("common.expand_section")
        self.toggle_button.setToolTip(f"{action}: {self._title}")
        self.toggle_button.setAccessibleName(f"{action}: {self._title}")
        if expanded:
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
        else:
            self.setMinimumWidth(self._collapsed_width)
            self.setMaximumWidth(self._collapsed_width)
        self._settings.setValue(self._settings_key(), expanded)
        self.updateGeometry()
        self._activate_parent_layouts()
        if emit and changed:
            self.toggled.emit(self.state_key, expanded)

    def retranslate(self, title=None):
        if title is not None:
            self._title = str(title or "")
            self.title_label.setText(self._title)
        self.set_expanded(self._expanded, emit=False)

    def _settings_key(self):
        return f"workspace/side_panel/{self.state_key}"

    def _activate_parent_layouts(self):
        widget = self
        while widget is not None:
            layout = widget.layout()
            if layout is not None:
                layout.invalidate()
                layout.activate()
            widget.updateGeometry()
            widget = widget.parentWidget()
