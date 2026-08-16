from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QSizePolicy

from ht_coach_app.core.constants import SIDEBAR_WIDTH

_ROLE_KEY = Qt.UserRole
_ROLE_IS_GROUP = Qt.UserRole + 1
_ROLE_PARENT_KEY = Qt.UserRole + 2

_CHILD_INDENT = "    "


class NavigationSidebar(QListWidget):
    """Alpha 0.6.7, Part 3: adds expandable submenu support (e.g.
    "Partido" -> "Nuevo partido" / "Partidos guardados") on top of the
    existing flat navigation list -- every plain (non-group) page keeps
    working exactly as before. A page dict may include a `"children"`
    list of the same `{"key", "label", "factory"}` shape; its parent
    item then toggles those children's visibility instead of
    navigating anywhere itself."""

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

        self._pages = list(pages)
        self._expanded_groups = set()
        self._rebuild_items()

        self.currentItemChanged.connect(
            self._handle_current_item_changed
        )
        self.itemClicked.connect(self._handle_item_clicked)

    def _rebuild_items(self):
        self.blockSignals(True)
        self.clear()
        for page in self._pages:
            children = page.get("children")
            if children:
                item = QListWidgetItem(self._group_label(page))
                item.setData(_ROLE_KEY, page["key"])
                item.setData(_ROLE_IS_GROUP, True)
                self.addItem(item)
                if page["key"] in self._expanded_groups:
                    for child in children:
                        child_item = QListWidgetItem(_CHILD_INDENT + child["label"]())
                        child_item.setData(_ROLE_KEY, child["key"])
                        child_item.setData(_ROLE_IS_GROUP, False)
                        child_item.setData(_ROLE_PARENT_KEY, page["key"])
                        self.addItem(child_item)
            else:
                item = QListWidgetItem(page["label"]())
                item.setData(_ROLE_KEY, page["key"])
                item.setData(_ROLE_IS_GROUP, False)
                self.addItem(item)
        self.blockSignals(False)

    def _group_label(self, page):
        marker = "▾" if page["key"] in self._expanded_groups else "▸"
        return f"{marker} {page['label']()}"

    def leaf_pages(self):
        """Every page that can actually be navigated to -- flattens
        group children in, skips group headers themselves."""
        flattened = []
        for page in self._pages:
            children = page.get("children")
            if children:
                flattened.extend(children)
            else:
                flattened.append(page)
        return flattened

    def select_first_page(self):
        leaves = self.leaf_pages()
        if not leaves:
            return
        self.select_page(leaves[0]["key"])

    def select_page(self, key):
        """Navigates directly to a leaf page by key, expanding its
        parent group first if needed."""
        for page in self._pages:
            children = page.get("children")
            if children and any(child["key"] == key for child in children):
                if page["key"] not in self._expanded_groups:
                    self._expanded_groups.add(page["key"])
                    self._rebuild_items()
                break
        for row in range(self.count()):
            item = self.item(row)
            if item.data(_ROLE_KEY) == key:
                self.setCurrentRow(row)
                return

    def retranslate_ui(self):
        current_item = self.currentItem()
        current_key = current_item.data(_ROLE_KEY) if current_item is not None else None
        self._rebuild_items()
        if current_key is not None:
            for row in range(self.count()):
                item = self.item(row)
                if item.data(_ROLE_KEY) == current_key:
                    self.blockSignals(True)
                    self.setCurrentRow(row)
                    self.blockSignals(False)
                    break

    def _handle_item_clicked(self, item):
        if item.data(_ROLE_IS_GROUP):
            current_item = self.currentItem()
            current_key = current_item.data(_ROLE_KEY) if current_item is not None else None
            key = item.data(_ROLE_KEY)
            if key in self._expanded_groups:
                self._expanded_groups.discard(key)
            else:
                self._expanded_groups.add(key)
            self._rebuild_items()
            if current_key is not None:
                for row in range(self.count()):
                    row_item = self.item(row)
                    if row_item.data(_ROLE_KEY) == current_key:
                        self.blockSignals(True)
                        self.setCurrentRow(row)
                        self.blockSignals(False)
                        break

    def _handle_current_item_changed(
        self,
        current,
        previous
    ):
        if current is None:
            return
        if current.data(_ROLE_IS_GROUP):
            return

        self.navigation_requested.emit(
            current.data(_ROLE_KEY)
        )
