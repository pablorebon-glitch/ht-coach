from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QSizePolicy

from ht_coach_app.core.constants import SIDEBAR_WIDTH


class NavigationSidebar(QListWidget):
    navigation_requested = Signal(str)

    def __init__(
        self,
        pages,
        parent=None
    ):
        super().__init__(parent)
        self.setObjectName("navigationList")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Expanding
        )

        for page in pages:
            item = QListWidgetItem(page["label"])
            item.setData(Qt.UserRole, page["key"])
            self.addItem(item)

        self.currentItemChanged.connect(
            self._handle_current_item_changed
        )

    def select_first_page(self):
        if self.count():
            self.setCurrentRow(0)

    def _handle_current_item_changed(
        self,
        current,
        previous
    ):
        if current is None:
            return

        self.navigation_requested.emit(
            current.data(Qt.UserRole)
        )
