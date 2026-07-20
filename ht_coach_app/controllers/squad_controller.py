from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceSettings,
)
from ht_coach_app.core.localization import t
from ht_coach_app.services.squad_builder_service import (
    AVAILABILITY_CURRENT,
    AVAILABILITY_FULL_STRENGTH,
    AUTO_FORMATION,
    SquadBuilderService,
)
from ht_coach_app.services.squad_evolution_service import SquadEvolutionService
from ht_coach_app.services.squad_service import SquadValidationError
from ht_coach_app.services.transfer_planner_service import TransferPlannerService
from engine.transfer_planner.models import TransferConstraints


class SquadController:
    def __init__(
        self,
        view,
        service,
        settings_repository,
        app_events=None,
        builder_service=None,
        evolution_service=None,
        transfer_planner_service=None,
    ):
        self._view = view
        self._service = service
        self._builder_service = builder_service or SquadBuilderService()
        self._evolution_service = evolution_service or SquadEvolutionService(
            builder_service=self._builder_service
        )
        self._transfer_planner_service = (
            transfer_planner_service or TransferPlannerService()
        )
        self._settings_repository = settings_repository
        self._app_events = app_events
        self._roster = None
        self._visible_rows = []
        self._ideal_selection = AUTO_FORMATION
        self._availability_mode = AVAILABILITY_CURRENT
        self._planning_horizon = "current"
        self._training_focus = "unknown"
        self._last_full_strength_result = None
        self._last_current_available_result = None
        self._last_evolution_result = None
        self._transfer_constraints = TransferConstraints()

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
        if hasattr(self._view, "ideal_formation_changed"):
            self._view.ideal_formation_changed.connect(
                self._show_ideal_xi
            )
        if hasattr(self._view, "availability_mode_changed"):
            self._view.availability_mode_changed.connect(
                self._change_availability_mode
            )
        if hasattr(self._view, "planning_horizon_changed"):
            self._view.planning_horizon_changed.connect(
                self._change_planning_horizon
            )
        if hasattr(self._view, "training_focus_changed"):
            self._view.training_focus_changed.connect(
                self._change_training_focus
            )
        if hasattr(self._view, "transfer_constraints_changed"):
            self._view.transfer_constraints_changed.connect(
                self._change_transfer_constraints
            )
        if hasattr(self._view, "squad_tab_changed"):
            self._view.squad_tab_changed.connect(
                self._change_squad_tab
            )

    def refresh(self):
        self._view.set_supported_positions(
            self._service.supported_positions()
        )
        if hasattr(self._view, "set_ideal_formation_options"):
            self._view.set_ideal_formation_options(
                self._builder_service.selection_options()
            )
        settings = self._settings_repository.load()
        self._availability_mode = (
            settings.squad_availability_mode
            if settings.squad_availability_mode
            in {AVAILABILITY_CURRENT, AVAILABILITY_FULL_STRENGTH}
            else AVAILABILITY_CURRENT
        )
        if hasattr(self._view, "set_availability_mode"):
            self._view.set_availability_mode(
                self._availability_mode
            )
        self._planning_horizon = self._evolution_service.normalize_horizon(
            getattr(settings, "squad_planning_horizon", "current")
        )
        self._training_focus = self._evolution_service.normalize_training_focus(
            getattr(settings, "squad_training_focus", "unknown")
        )
        if hasattr(self._view, "set_evolution_options"):
            self._view.set_evolution_options(
                self._evolution_service.planning_horizons(),
                self._evolution_service.training_focuses(),
            )
        if hasattr(self._view, "set_planning_horizon"):
            self._view.set_planning_horizon(self._planning_horizon)
        if hasattr(self._view, "set_training_focus"):
            self._view.set_training_focus(self._training_focus)
        self._transfer_constraints = (
            self._transfer_planner_service.constraints_from_settings(settings)
        )
        if hasattr(self._view, "set_transfer_options"):
            self._view.set_transfer_options(
                self._transfer_planner_service.planning_objectives(),
                self._transfer_planner_service.budget_tiers(),
                self._transfer_planner_service.age_strategies(),
                self._transfer_planner_service.training_preferences(),
                self._transfer_planner_service.specialty_preferences(),
            )
        if hasattr(self._view, "set_transfer_constraints"):
            self._view.set_transfer_constraints(self._transfer_constraints)
        self._view.set_csv_path(
            settings.players_csv_path
        )
        if hasattr(self._view, "set_selected_tab"):
            self._view.set_selected_tab(
                getattr(settings, "squad_selected_tab", "ideal")
            )

    def _browse(self):
        path = self._view.choose_players_file()

        if path:
            self._view.set_csv_path(path)
            self._save_roster_path(path)

    def _load(self):
        self._view.show_loading()
        self._evolution_service.clear_cache()
        self._last_full_strength_result = None
        self._last_current_available_result = None
        self._last_evolution_result = None

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
        self._show_ideal_xi(
            self._ideal_selection
        )
        self._show_evolution()

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
            selected_position=filters["selected_position"],
            availability=filters.get("availability", "all")
        )
        self._view.set_players(
            self._visible_rows
        )

    def _show_ideal_xi(self, formation_name=AUTO_FORMATION):
        self._ideal_selection = formation_name or AUTO_FORMATION

        if not hasattr(self._view, "show_ideal_xi"):
            return

        if self._roster is None:
            self._view.show_ideal_empty()
            return

        result = self._builder_service.build(
            self._roster.players,
            self._ideal_selection,
            self._availability_mode,
        )
        if self._availability_mode == AVAILABILITY_CURRENT:
            self._last_current_available_result = result
        elif self._availability_mode == AVAILABILITY_FULL_STRENGTH:
            self._last_full_strength_result = result
        roster_players = (
            self._builder_service.eligible_players(
                self._roster.players,
                self._availability_mode,
            )
            if hasattr(self._builder_service, "eligible_players")
            else self._roster.players
        )
        details_by_name = {
            row.name: self._service.player_detail(
                roster_players,
                row.name,
            )
            for row in self._service.map_players(roster_players)
        }
        self._view.show_ideal_xi(
            result,
            player_details_by_name=details_by_name,
            roster_players=roster_players,
        )
        self._show_evolution()

    def _change_availability_mode(self, mode):
        self._availability_mode = (
            mode
            if mode in {AVAILABILITY_CURRENT, AVAILABILITY_FULL_STRENGTH}
            else AVAILABILITY_CURRENT
        )
        self._save_roster_path(
            self._view.csv_path()
        )
        if hasattr(self._view, "show_status"):
            self._view.show_status(
                t("availability.status_message.updating_availability")
            )
        self._show_ideal_xi(
            self._ideal_selection
        )

    def _change_planning_horizon(self, horizon):
        self._planning_horizon = self._evolution_service.normalize_horizon(
            horizon
        )
        self._save_roster_path(self._view.csv_path())
        self._show_evolution()

    def _change_training_focus(self, training_focus):
        self._training_focus = self._evolution_service.normalize_training_focus(
            training_focus
        )
        self._save_roster_path(self._view.csv_path())
        self._show_evolution()

    def _show_evolution(self):
        if not hasattr(self._view, "show_evolution"):
            return

        if self._roster is None:
            self._view.show_evolution_empty()
            return

        result = self._evolution_service.analyze(
            self._roster.players,
            planning_horizon=self._planning_horizon,
            training_focus=self._training_focus,
            full_strength_result=self._last_full_strength_result,
            current_available_result=self._last_current_available_result,
        )
        self._last_evolution_result = result
        self._view.show_evolution(result)
        self._show_transfer_plan()

    def _change_transfer_constraints(self, constraints):
        self._transfer_constraints = (
            self._transfer_planner_service.normalize_constraints(constraints)
        )
        self._save_roster_path(self._view.csv_path())
        self._show_transfer_plan()

    def _change_squad_tab(self, tab_key):
        settings = self._settings_repository.load()
        self._settings_repository.save(
            MatchWorkspaceSettings(
                players_csv_path=settings.players_csv_path,
                opponent_name=settings.opponent_name,
                selected_formations=settings.selected_formations,
                squad_availability_mode=self._availability_mode,
                squad_training_focus=self._training_focus,
                squad_planning_horizon=self._planning_horizon,
                transfer_planning_objective=(
                    self._transfer_constraints.planning_objective
                ),
                transfer_budget_tier=self._transfer_constraints.budget_tier,
                transfer_age_strategy=(
                    self._transfer_constraints.preferred_age_strategy
                ),
                transfer_training_preference=(
                    self._transfer_constraints.training_compatibility_preference
                ),
                transfer_specialty_preference=(
                    self._transfer_constraints.specialty_preference
                ),
                squad_selected_tab=tab_key or "ideal",
            )
        )

    def _show_transfer_plan(self):
        if not hasattr(self._view, "show_transfer_plan"):
            return
        if self._last_evolution_result is None:
            self._view.show_transfer_plan_empty()
            return
        result = self._transfer_planner_service.build_plan(
            self._last_evolution_result,
            self._transfer_constraints,
        )
        self._view.show_transfer_plan(result)

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
                selected_formations=settings.selected_formations,
                squad_availability_mode=self._availability_mode,
                squad_training_focus=self._training_focus,
                squad_planning_horizon=self._planning_horizon,
                transfer_planning_objective=(
                    self._transfer_constraints.planning_objective
                ),
                transfer_budget_tier=self._transfer_constraints.budget_tier,
                transfer_age_strategy=(
                    self._transfer_constraints.preferred_age_strategy
                ),
                transfer_training_preference=(
                    self._transfer_constraints.training_compatibility_preference
                ),
                transfer_specialty_preference=(
                    self._transfer_constraints.specialty_preference
                ),
                squad_selected_tab=(
                    self._view.selected_tab_key()
                    if hasattr(self._view, "selected_tab_key")
                    else getattr(settings, "squad_selected_tab", "ideal")
                ),
            )
        )
