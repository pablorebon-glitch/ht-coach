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
from ht_coach_app.controllers.squad_controller import SquadController
from ht_coach_app.core.constants import (
    WINDOW_MINIMUM_HEIGHT,
    WINDOW_MINIMUM_WIDTH,
    WINDOW_TITLE,
)
from ht_coach_app.core.localization import (
    configure_localization,
    localization_service,
    t,
)
from ht_coach_app.core.paths import application_icon_path
from ht_coach_app.persistence.app_settings_repository import (
    AppSettings,
    AppSettingsRepository,
)
from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceRepository,
)
from ht_coach_app.services.match_workspace_service import (
    MatchWorkspaceService,
)
from ht_coach_app.services.opponent_service import OpponentService
from ht_coach_app.services.squad_service import SquadService
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
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
        {"key": "dashboard", "label": lambda: t("nav.dashboard"), "factory": DashboardPage},
        {"key": "squad", "label": lambda: t("nav.squad"), "factory": SquadPage},
        {"key": "opponents", "label": lambda: t("nav.opponents"), "factory": OpponentsPage},
        {"key": "match", "label": lambda: t("nav.match"), "factory": MatchPage},
        {"key": "reports", "label": lambda: t("nav.reports"), "factory": ReportsPage},
        {"key": "settings", "label": lambda: t("nav.settings"), "factory": SettingsPage},
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(
            WINDOW_MINIMUM_WIDTH,
            WINDOW_MINIMUM_HEIGHT
        )
        self._settings_repository = AppSettingsRepository()
        self._settings = self._settings_repository.load()
        configure_localization(self._settings.language)
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
        self.toolbar = QToolBar("Main Toolbar")
        toolbar = self.toolbar
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setToolButtonStyle(
            Qt.ToolButtonTextBesideIcon
        )

        self.refresh_action = QAction(t("app.refresh"), self)
        self.refresh_action.setStatusTip(t("app.refresh_tip"))
        self.refresh_action.triggered.connect(
            self._show_not_implemented_status
        )

        toolbar.addAction(self.refresh_action)
        toolbar.addSeparator()
        self.help_action = toolbar.addAction(
            t("app.help"),
            self._show_not_implemented_status,
        )

        self.addToolBar(
            Qt.TopToolBarArea,
            toolbar
        )

    def _build_status_bar(self):
        self.statusBar().showMessage(t("app.ready"))

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
            t("app.not_implemented"),
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

        if page["key"] == "squad":
            self._controllers.append(
                SquadController(
                    widget,
                    SquadService(),
                    MatchWorkspaceRepository(),
                    self._app_events
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
                    WeeklyTrainingAppService(),
                    self
                )
            )
            widget.set_advisor_verbosity(
                self._settings.advisor_verbosity
            )

        if page["key"] == "settings":
            widget.set_language(self._settings.language)
            widget.set_advisor_verbosity(
                self._settings.advisor_verbosity
            )
            widget.language_changed.connect(
                self._change_language
            )
            widget.advisor_verbosity_changed.connect(
                self._change_advisor_verbosity
            )

        return widget

    def _change_language(self, language):
        self._settings = self._settings_repository.save(
            AppSettings(
                language=language,
                advisor_verbosity=self._settings.advisor_verbosity,
            )
        )
        localization_service().set_language(language)
        self._app_events.language_changed.emit(language)
        self._retranslate_ui()
        self.statusBar().showMessage(t("settings.saved"), 5000)

    def _change_advisor_verbosity(self, verbosity):
        self._settings = self._settings_repository.save(
            AppSettings(
                language=self._settings.language,
                advisor_verbosity=verbosity,
            )
        )
        self._app_events.advisor_verbosity_changed.emit(verbosity)
        for index in range(self.stacked_pages.count()):
            widget = self.stacked_pages.widget(index)
            if hasattr(widget, "set_advisor_verbosity"):
                widget.set_advisor_verbosity(verbosity)
        self.statusBar().showMessage(t("settings.advisor_saved"), 5000)

    def _retranslate_ui(self):
        self.refresh_action.setText(t("app.refresh"))
        self.refresh_action.setStatusTip(t("app.refresh_tip"))
        self.help_action.setText(t("app.help"))
        self.sidebar.retranslate_ui()
        for index in range(self.stacked_pages.count()):
            widget = self.stacked_pages.widget(index)
            if hasattr(widget, "retranslate_ui"):
                widget.retranslate_ui()
