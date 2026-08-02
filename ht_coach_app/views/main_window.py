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
from ht_coach_app.controllers.saved_matches_controller import SavedMatchesController
from engine.history.repository import HistoricalMatchRepository
from engine.weekly_training.persistence import WeeklyTrainingRepository
from engine.calendar.season_calendar_repository import SeasonCalendarRepository
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
from ht_coach_app.core.paths import application_icon_path, historical_match_snapshots_path, user_data_dir
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
from ht_coach_app.services.official_rating_service import OfficialRatingImportService
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from ht_coach_app.state.app_events import AppEvents
from ht_coach_app.views.dashboard_page import DashboardPage
from ht_coach_app.views.match_page import MatchPage
from ht_coach_app.views.saved_matches_page import SavedMatchesPage
from ht_coach_app.views.club_advisor_page import ClubAdvisorPage
from ht_coach_app.controllers.club_advisor_controller import ClubAdvisorController
from ht_coach_app.views.match_intelligence_page import MatchIntelligencePage
from ht_coach_app.controllers.match_intelligence_controller import MatchIntelligenceController
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
        {
            "key": "match_group",
            "label": lambda: t("nav.match"),
            "children": [
                {"key": "match", "label": lambda: t("nav.new_match"), "factory": MatchPage},
                {"key": "saved_matches", "label": lambda: t("nav.saved_matches"), "factory": SavedMatchesPage},
            ],
        },
        {"key": "match_intelligence", "label": lambda: t("nav.official_match_intelligence"), "factory": MatchIntelligencePage},
        {"key": "club_advisor", "label": lambda: t("nav.club_advisor"), "factory": ClubAdvisorPage},
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

        for page in self.sidebar.leaf_pages():
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

    def _open_saved_match(self, snapshot_id, saved_matches_controller):
        self.sidebar.select_page("saved_matches")
        saved_matches_controller.open_record(snapshot_id)

    def _edit_saved_match(self, snapshot_id):
        self.sidebar.select_page("match")
        if hasattr(self, "_match_controller"):
            self._match_controller.edit_record(snapshot_id)

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
            self._match_controller = MatchController(
                widget,
                service,
                MatchWorkspaceRepository(),
                self._app_events,
                WeeklyTrainingAppService(),
                OfficialRatingImportService(),
                SeasonCalendarRepository(user_data_dir() / "season_calendar.json"),
                self
            )
            self._controllers.append(self._match_controller)
            widget.set_advisor_verbosity(
                self._settings.advisor_verbosity
            )

        if page["key"] == "saved_matches":
            saved_matches_controller = SavedMatchesController(
                widget,
                HistoricalMatchRepository(historical_match_snapshots_path()),
                WeeklyTrainingRepository(user_data_dir() / "weekly_training_planner.json"),
                workspace_repository=MatchWorkspaceRepository(),
                parent=self,
            )
            self._controllers.append(saved_matches_controller)
            if hasattr(self._app_events, "open_saved_match_requested"):
                self._app_events.open_saved_match_requested.connect(
                    lambda snapshot_id: self._open_saved_match(snapshot_id, saved_matches_controller)
                )
            if hasattr(widget, "edit_requested"):
                widget.edit_requested.connect(self._edit_saved_match)

        if page["key"] == "match_intelligence":
            self._controllers.append(
                MatchIntelligenceController(widget, app_events=self._app_events, parent=self)
            )

        if page["key"] == "club_advisor":
            self._controllers.append(
                ClubAdvisorController(
                    widget,
                    SquadService(),
                    MatchWorkspaceRepository(),
                    parent=self
                )
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
            self._wire_season_calendar_settings(widget)

        return widget

    def _wire_season_calendar_settings(self, widget):
        from engine.calendar.season_calendar import SeasonCalendarConfig
        from engine.calendar.season_calendar_repository import SeasonCalendarRepository

        repository = SeasonCalendarRepository(user_data_dir() / "season_calendar.json")
        widget.set_season_calendar_config(repository.load())

        def _save(season_number, start_date_text, total_weeks):
            config = SeasonCalendarConfig(
                season_number=season_number,
                season_start_date=start_date_text,
                total_weeks=total_weeks,
            )
            repository.save(config)
            widget.set_season_calendar_config(config)
            widget.set_season_calendar_status(t("settings.season_calendar.saved"))

        def _recalculate():
            from engine.calendar.season_recalculation import (
                preview_recalculation,
                recalculate_season_weeks,
            )

            config = repository.load()
            if not config.is_configured:
                widget.set_season_calendar_status(
                    t("settings.season_calendar.not_configured")
                )
                return
            history_repository = HistoricalMatchRepository(historical_match_snapshots_path())
            preview = preview_recalculation(history_repository, config)
            if not widget.confirm_recalculation(len(preview)):
                return
            report = recalculate_season_weeks(history_repository, config, force=True)
            widget.set_season_calendar_status(
                t("settings.season_calendar.recalculated", count=report.updated_count)
            )

        widget.season_calendar_save_requested.connect(_save)
        widget.season_calendar_recalculate_requested.connect(_recalculate)

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
