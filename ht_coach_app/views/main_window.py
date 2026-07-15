from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QToolBar,
    QWidget,
)

from ht_coach_app.controllers.navigation_controller import NavigationController
from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.controllers.opponent_controller import OpponentController
from ht_coach_app.core.constants import (
    WINDOW_MINIMUM_HEIGHT,
    WINDOW_MINIMUM_WIDTH,
    WINDOW_TITLE,
)
from ht_coach_app.core.paths import application_icon_path
from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceRepository,
)
from ht_coach_app.services.match_workspace_service import (
    MatchWorkspaceService,
)
from ht_coach_app.services.opponent_service import OpponentService
from ht_coach_app.state.app_events import AppEvents
from ht_coach_app.views.dashboard_page import DashboardPage
from ht_coach_app.views.match_page import MatchPage
from ht_coach_app.views.opponents_page import OpponentsPage
from ht_coach_app.views.reports_page import ReportsPage
from ht_coach_app.views.settings_page import SettingsPage
from ht_coach_app.views.squad_page import SquadPage
from ht_coach_app.widgets.navigation_sidebar import NavigationSidebar


class MainWindow(QMainWindow):
    PAGES = [
        {"key": "dashboard", "label": "Dashboard", "factory": DashboardPage},
        {"key": "squad", "label": "Squad", "factory": SquadPage},
        {"key": "opponents", "label": "Opponents", "factory": OpponentsPage},
        {"key": "match", "label": "Match", "factory": MatchPage},
        {"key": "reports", "label": "Reports", "factory": ReportsPage},
        {"key": "settings", "label": "Settings", "factory": SettingsPage},
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(
            WINDOW_MINIMUM_WIDTH,
            WINDOW_MINIMUM_HEIGHT
        )
        self._apply_application_icon()
        self._controllers = []
        self._app_events = AppEvents(self)
        self._build_toolbar()
        self._build_status_bar()
        self._build_shell()

    def _apply_application_icon(self):
        icon_path = application_icon_path()
        if icon_path is not None:
            self.setWindowIcon(
                QIcon(str(icon_path))
            )

    def _build_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setToolButtonStyle(
            Qt.ToolButtonTextBesideIcon
        )

        refresh_action = QAction("Refresh", self)
        refresh_action.setStatusTip("Refresh the current workspace view")
        refresh_action.triggered.connect(
            self._show_not_implemented_status
        )

        toolbar.addAction(refresh_action)
        toolbar.addSeparator()
        toolbar.addAction("Help", self._show_not_implemented_status)

        self.addToolBar(
            Qt.TopToolBarArea,
            toolbar
        )

    def _build_status_bar(self):
        self.statusBar().showMessage("Ready")

    def _build_shell(self):
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = NavigationSidebar(self.PAGES)
        root_layout.addWidget(self.sidebar)

        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("color: #d8dde6;")
        root_layout.addWidget(separator)

        self.stacked_pages = QStackedWidget()
        self.stacked_pages.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        root_layout.addWidget(self.stacked_pages, 1)

        self.navigation_controller = NavigationController(
            self.stacked_pages,
            self.statusBar(),
            self
        )

        for page in self.PAGES:
            widget = self._create_page(
                page
            )
            self.navigation_controller.register_page(
                page["key"],
                widget
            )

        self.sidebar.navigation_requested.connect(
            self.navigation_controller.navigate_to
        )
        self.setCentralWidget(root)
        self.sidebar.select_first_page()

    def _show_not_implemented_status(self):
        self.statusBar().showMessage(
            "This shell action will be implemented in a later epic.",
            5000
        )

    def _create_page(self, page):
        widget = page["factory"]()

        if page["key"] == "opponents":
            service = OpponentService(
                OpponentRepository()
            )
            self._controllers.append(
                OpponentController(
                    widget,
                    service,
                    self._app_events,
                    self
                )
            )

        if page["key"] == "match":
            opponent_service = OpponentService(
                OpponentRepository()
            )
            service = MatchWorkspaceService(
                opponent_service
            )
            self._controllers.append(
                MatchController(
                    widget,
                    service,
                    MatchWorkspaceRepository(),
                    self._app_events,
                    self
                )
            )

        return widget
