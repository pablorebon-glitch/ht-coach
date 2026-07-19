from PySide6.QtCore import QObject, Signal

from ht_coach_app.core.localization import t


class NavigationController(QObject):
    page_changed = Signal(str)

    def __init__(
        self,
        stacked_pages,
        status_bar,
        parent=None
    ):
        super().__init__(parent)
        self._stacked_pages = stacked_pages
        self._status_bar = status_bar
        self._page_indexes = {}

    def register_page(
        self,
        key,
        widget
    ):
        self._page_indexes[key] = self._stacked_pages.addWidget(
            widget
        )

    def navigate_to(
        self,
        key
    ):
        if key not in self._page_indexes:
            return

        self._stacked_pages.setCurrentIndex(
            self._page_indexes[key]
        )
        self._status_bar.showMessage(
            t("nav.ready", page=t(f"nav.{key}"))
        )
        self.page_changed.emit(key)
