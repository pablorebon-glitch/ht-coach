from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceSettings,
)
from ht_coach_app.services.squad_service import SquadValidationError


class SquadController:
    def __init__(
        self,
        view,
        service,
        settings_repository,
        app_events=None
    ):
        self._view = view
        self._service = service
        self._settings_repository = settings_repository
        self._app_events = app_events
        self._roster = None
        self._visible_rows = []

        self._connect_view()
        self.refresh()

    def _connect_view(self):
        self._view.browse_requested.connect(
            self._browse
        )
        self._view.load_requested.connect(
            self._load
        )
        self._view.reload_requested.connect(
            self._load
        )
        self._view.filters_changed.connect(
            self._apply_filters
        )
        self._view.export_requested.connect(
            self._export
        )
        self._view.player_selected.connect(
            self._show_player_detail
        )

    def refresh(self):
        self._view.set_supported_positions(
            self._service.supported_positions()
        )
        settings = self._settings_repository.load()
        self._view.set_csv_path(
            settings.players_csv_path
        )

    def _browse(self):
        path = self._view.choose_players_file()

        if path:
            self._view.set_csv_path(path)
            self._save_roster_path(path)

    def _load(self):
        self._view.show_loading()

        try:
            self._roster = self._service.load_roster(
                self._view.csv_path()
            )
        except SquadValidationError as exc:
            self._view.show_error(str(exc))
            return

        self._save_roster_path(
            self._roster.source_path
        )
        self._view.set_specialties(
            self._roster.specialties
        )
        self._apply_filters()
        self._view.set_loaded_count(
            self._roster.player_count
        )
        self._view.show_status(
            f"Loaded {self._roster.player_count} players."
        )

        if self._app_events is not None:
            self._app_events.roster_changed.emit(
                self._roster.source_path,
                self._roster.player_count
            )

    def _apply_filters(self):
        if self._roster is None:
            self._visible_rows = []
            self._view.set_players([])
            return

        filters = self._view.filter_values()
        rows = self._service.map_players(
            self._roster.players,
            filters["selected_position"]
        )
        self._visible_rows = self._service.filter_rows(
            rows,
            search_text=filters["search_text"],
            minimum_form=filters["minimum_form"],
            minimum_stamina=filters["minimum_stamina"],
            speciality=filters["speciality"],
            selected_position=filters["selected_position"]
        )
        self._view.set_players(
            self._visible_rows
        )

    def _show_player_detail(self, player_name):
        if self._roster is None:
            self._view.clear_detail()
            return

        detail = self._service.player_detail(
            self._roster.players,
            player_name
        )

        if detail is None:
            self._view.clear_detail()
            return

        self._view.show_player_detail(
            detail
        )

    def _export(self):
        if not self._visible_rows:
            self._view.show_error(
                "Load players before exporting."
            )
            return

        path = self._view.choose_export_file()

        if not path:
            return

        exported_path = self._service.export_rows_to_csv(
            self._visible_rows,
            path
        )
        self._view.show_status(
            f"Exported visible players to {exported_path}"
        )

    def _save_roster_path(self, path):
        settings = self._settings_repository.load()
        self._settings_repository.save(
            MatchWorkspaceSettings(
                players_csv_path=str(path),
                opponent_name=settings.opponent_name,
                selected_formations=settings.selected_formations
            )
        )
