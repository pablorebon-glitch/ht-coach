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
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from engine.weekly_training.player_identity import player_training_id
from engine.weekly_training.models import MatchStatus
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
        weekly_training_service=None,
        squad_intelligence_service=None,
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
        self._weekly_training_service = (
            weekly_training_service or WeeklyTrainingAppService()
        )
        self._squad_intelligence_service = squad_intelligence_service
        self._settings_repository = settings_repository
        self._app_events = app_events
        self._roster = None
        self._last_selected_player_name = None
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
        if hasattr(self._view, "training_priority_changed"):
            self._view.training_priority_changed.connect(
                self._change_training_priority
            )
        if hasattr(self._view, "generate_training_plan_requested"):
            self._view.generate_training_plan_requested.connect(
                self._generate_training_plan
            )
        if hasattr(self._view, "record_first_match_requested"):
            self._view.record_first_match_requested.connect(
                self._record_first_training_match
            )
        if hasattr(self._view, "edit_first_match_requested"):
            self._view.edit_first_match_requested.connect(
                self._edit_first_training_match
            )
        if hasattr(self._view, "cancel_first_match_edit_requested"):
            self._view.cancel_first_match_edit_requested.connect(
                self._cancel_first_training_match_edit
            )
        if hasattr(self._view, "replace_first_match_requested"):
            self._view.replace_first_match_requested.connect(
                self._replace_first_training_match
            )
        if hasattr(self._view, "delete_first_match_requested"):
            self._view.delete_first_match_requested.connect(
                self._delete_first_training_match
            )
        if hasattr(self._view, "delete_second_match_requested"):
            self._view.delete_second_match_requested.connect(
                self._delete_second_training_match
            )
        if hasattr(self._view, "use_training_plan_requested"):
            self._view.use_training_plan_requested.connect(
                self._accept_training_plan
            )
        if hasattr(self._view, "week_navigation_requested"):
            self._view.week_navigation_requested.connect(
                self._navigate_week
            )
        if self._app_events is not None:
            self._app_events.weekly_plan_saved.connect(
                self._refresh_weekly_training_after_external_save
            )
        if hasattr(self._view, "training_type_changed"):
            self._view.training_type_changed.connect(
                self._change_active_training_type
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
        if hasattr(self._view, "set_recent_csv_paths"):
            self._view.set_recent_csv_paths(
                settings.recent_players_csv_paths
            )
        if hasattr(self._view, "set_selected_tab"):
            self._view.set_selected_tab(
                getattr(settings, "squad_selected_tab", "ideal")
            )
        if settings.players_csv_path and self._roster is None:
            self._load()

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
        self._visible_rows = self._apply_squad_intelligence_filters(
            self._visible_rows,
            role=filters.get("role", "all"),
            status=filters.get("status", "all"),
            training_fit=filters.get("training_fit", "all"),
        )
        self._view.set_players(
            self._visible_rows
        )

    def _apply_squad_intelligence_filters(self, rows, role="all", status="all", training_fit="all"):
        if role == "all" and status == "all" and training_fit == "all":
            return rows
        if self._squad_intelligence_service is None:
            from ht_coach_app.services.squad_intelligence_service import (
                SquadIntelligenceAppService,
            )

            self._squad_intelligence_service = SquadIntelligenceAppService(
                weekly_training_service=self._weekly_training_service
            )
        try:
            reports = self._squad_intelligence_service.generate_squad_reports(
                self._roster.players
            )
        except Exception:
            return rows
        reports_by_name = {report.player_name: report for report in reports}

        def _matches(row):
            report = reports_by_name.get(row.name)
            if report is None:
                return False
            if role != "all" and report.recommended_role.value != role:
                return False
            if status != "all" and report.management_status.value != status:
                return False
            if training_fit != "all" and report.training_fit.value != training_fit:
                return False
            return True

        return [row for row in rows if _matches(row)]

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
        self._show_weekly_training()

    def _refresh_weekly_training_after_external_save(self):
        """Alpha 0.6.6, Part 8: a lineup saved as First/Second Weekly
        Match from Match must update the Weekly Planner record
        immediately -- not only the next time this tab happens to be
        rebuilt. Cheap to call unconditionally: `_show_weekly_training`
        already no-ops safely when there's no roster loaded yet."""
        self._show_weekly_training()

    def _show_weekly_training(self):
        if not hasattr(self._view, "show_weekly_training"):
            return
        if hasattr(self._view, "set_ht_week_status"):
            from ht_coach_app.services.ht_week_context_provider import current_week_snapshot
            from ht_coach_app.services.ht_week_formatting import format_ht_week_status

            self._view.set_ht_week_status(format_ht_week_status(current_week_snapshot()))
        if self._roster is None:
            self._view.show_weekly_training_empty()
            return
        state = self._weekly_training_service.load_state()
        cycle_id = state.active_week.week_id if state.active_week is not None else ""
        self._view.show_weekly_training(
            state,
            self._weekly_training_service.priority_rows(self._roster.players),
            self._weekly_training_service.coverage(
                self._roster.players,
                cycle_id,
            ),
            self._builder_service.supported_formations(),
        )
        if hasattr(self._view, "show_week_navigation_context"):
            self._navigate_week("current")

    def _navigate_week(self, direction):
        if not hasattr(self._view, "show_week_navigation_context"):
            return
        state = self._weekly_training_service.load_state()
        context = self._weekly_training_service.week_navigation_context(state, direction)
        self._view.show_week_navigation_context(context)

    def _change_active_training_type(self, training_type):
        if self._roster is None:
            return
        current_state = self._weekly_training_service.load_state()
        if current_state.active_training_type == training_type:
            return

        if current_state.priorities:
            if not self._view.confirm_training_type_change():
                self._view.set_active_training_type(current_state.active_training_type)
                return

        eligible_by_position = self._eligible_players_by_position(training_type)
        selections = self._request_training_priority_selections(
            training_type, eligible_by_position
        )
        if selections is None:
            self._view.set_active_training_type(current_state.active_training_type)
            return

        self._weekly_training_service.set_active_training_type(training_type)
        self._apply_wizard_selections(selections)

        self._show_weekly_training()
        if self._last_selected_player_name:
            self._show_squad_intelligence(self._last_selected_player_name)

    def _eligible_players_by_position(self, training_type):
        from engine.analyzers.player_analyzer import PlayerAnalyzer
        from engine.weekly_training.player_identity import player_training_id

        by_position = {}
        for player in self._roster.players:
            best_position, _score = PlayerAnalyzer.best_position(player)
            if not best_position:
                continue
            by_position.setdefault(best_position, []).append(
                (player_training_id(player), player.name)
            )
        return by_position

    def _request_training_priority_selections(self, training_type, eligible_by_position):
        from ht_coach_app.widgets.training_priority_wizard import TrainingPriorityWizard

        return TrainingPriorityWizard.request_selections(
            training_type, eligible_by_position, self._view
        )

    def _apply_wizard_selections(self, selections):
        from engine.weekly_training.models import TrainingPriority
        from engine.weekly_training.player_identity import player_training_id

        effect_to_priority = {
            "FULL": TrainingPriority.REQUIRED_100.value,
            "REDUCED": TrainingPriority.REQUIRED_50.value,
            "VERY_SMALL": TrainingPriority.SECONDARY_PRIORITY.value,
        }
        players_by_id = {
            player_training_id(player): player for player in self._roster.players
        }
        for effect, player_ids in (selections or {}).items():
            priority_value = effect_to_priority.get(effect)
            if priority_value is None:
                continue
            for player_id in player_ids:
                player = players_by_id.get(player_id)
                if player is not None:
                    self._weekly_training_service.save_priority(player, priority_value)

    def _change_training_priority(self, player_id, priority):
        if self._roster is None:
            return
        player = next(
            (
                player for player in self._roster.players
                if player_training_id(player) == player_id
            ),
            None,
        )
        if player is None:
            return
        self._weekly_training_service.save_priority(player, priority)
        self._show_weekly_training()

    def _generate_training_plan(self, formation_name):
        if self._roster is None:
            self._view.show_error(t("planner.load_roster_first"))
            return
        plan = self._weekly_training_service.generate_plan(
            self._roster.players,
            formation_name,
        )
        board = self._weekly_training_service.board_for_plan(plan)
        self._view.show_weekly_training_plan(plan, board, self._roster.players)

    def _record_first_training_match(self):
        if self._roster is None:
            self._view.show_error(t("planner.load_roster_first"))
            return
        if (
            hasattr(self._view, "is_weekly_record_editing")
            and self._view.is_weekly_record_editing()
        ):
            self._save_first_training_match_lineup_changes()
            return
        board = self._view.weekly_training_current_board()
        if board is None:
            self._view.show_error(t("planner.no_plan_to_record"))
            return
        state = self._weekly_training_service.load_state()
        requested_status, confirmed = self._first_match_requested_status(
            state.active_week.first_match_date
        )
        try:
            saved = self._weekly_training_service.record_first_match(
                board,
                roster_players=self._roster.players,
                requested_status=requested_status,
                played_confirmed=confirmed,
            )
        except ValueError as exc:
            self._view.show_error(self._planner_validation_message(exc))
            return
        except Exception:
            self._view.show_error(t("planner.duplicate_first_match"))
            return
        self._show_weekly_training()
        self._view.show_status(self._first_match_save_message(saved))

    def _edit_first_training_match(self, opponent_name, minutes_known):
        if self._roster is None:
            return
        record = self._weekly_training_service.first_match_record()
        if record is None:
            return
        if not opponent_name and not minutes_known:
            board = self._weekly_training_service.board_for_record(record)
            if hasattr(self._view, "show_weekly_record_edit_mode"):
                self._view.show_weekly_record_edit_mode(
                    record,
                    board,
                    self._roster.players,
                )
                self._view.show_status(t("planner.editing_recorded_lineup"))
            return
        requested_status, confirmed = self._first_match_requested_status(
            record.match_date,
            requested_status=record.planned_or_played,
            minutes_known=minutes_known,
        )
        try:
            saved = self._weekly_training_service.update_first_match_metadata(
                opponent_name,
                minutes_known,
                requested_status=requested_status,
                played_confirmed=confirmed,
            )
        except ValueError as exc:
            self._view.show_error(self._planner_validation_message(exc))
            return
        self._show_weekly_training()
        self._view.show_status(self._first_match_save_message(saved))

    def _save_first_training_match_lineup_changes(self):
        board = self._view.weekly_training_current_board()
        if board is None:
            self._view.show_error(t("planner.no_plan_to_record"))
            return
        record = self._weekly_training_service.first_match_record()
        if record is None:
            self._view.show_error(t("planner.no_first_match_record"))
            return
        requested_status, confirmed = self._first_match_requested_status(
            record.match_date,
            requested_status=record.planned_or_played,
            minutes_known=record.minutes_known,
        )
        try:
            self._weekly_training_service.update_first_match_lineup(
                board,
                roster_players=self._roster.players,
                requested_status=requested_status,
                played_confirmed=confirmed,
            )
        except ValueError as exc:
            self._view.show_error(self._planner_validation_message(exc))
            return
        if hasattr(self._view, "exit_weekly_record_edit_mode"):
            self._view.exit_weekly_record_edit_mode()
        self._show_weekly_training()
        self._view.show_status(t("planner.first_match_lineup_changed"))

    def _cancel_first_training_match_edit(self):
        if hasattr(self._view, "exit_weekly_record_edit_mode"):
            self._view.exit_weekly_record_edit_mode()
        self._show_weekly_training()
        self._view.show_status(t("planner.editing_cancelled"))

    def _replace_first_training_match(self):
        if self._roster is None:
            return
        board = self._view.weekly_training_current_board()
        if board is None:
            self._view.show_error(t("planner.no_plan_to_record"))
            return
        state = self._weekly_training_service.load_state()
        requested_status, confirmed = self._first_match_requested_status(
            state.active_week.first_match_date
        )
        try:
            saved = self._weekly_training_service.replace_first_match(
                board,
                roster_players=self._roster.players,
                requested_status=requested_status,
                played_confirmed=confirmed,
            )
        except ValueError as exc:
            self._view.show_error(self._planner_validation_message(exc))
            return
        self._show_weekly_training()
        self._view.show_status(self._first_match_save_message(saved))

    def _delete_first_training_match(self):
        if self._roster is None:
            return
        self._weekly_training_service.delete_first_match()
        self._show_weekly_training()
        self._view.show_status(t("planner.no_first_match_record"))

    def _delete_second_training_match(self):
        if self._roster is None:
            return
        self._weekly_training_service.delete_second_match()
        self._show_weekly_training()
        self._view.show_status(t("planner.no_second_match_record"))

    def _first_match_requested_status(
        self,
        match_date,
        requested_status=MatchStatus.PLAYED,
        minutes_known=False,
    ):
        temporal = self._weekly_training_service.temporal_status(match_date)
        if temporal == "FUTURE":
            if hasattr(self._view, "show_status"):
                self._view.show_status(t("planner.future_match_planned"))
            return MatchStatus.PLANNED, False
        if temporal == "TODAY" and requested_status == MatchStatus.PLAYED:
            confirmed = (
                self._view.confirm_today_first_match_played()
                if hasattr(self._view, "confirm_today_first_match_played")
                else bool(minutes_known)
            )
            return (
                MatchStatus.PLAYED if confirmed else MatchStatus.PLANNED,
                confirmed,
            )
        return requested_status, bool(minutes_known)

    def _planner_validation_message(self, exc):
        code = str(exc)
        return {
            "future_match_cannot_be_played": t("planner.future_match_planned"),
            "today_match_requires_played_confirmation": t(
                "planner.today_match_confirmation_required"
            ),
            "duplicate_match_id": t("planner.duplicate_first_match"),
            "automatic_rules_unavailable": t("planner.automatic_rules_unavailable"),
        }.get(code, t("planner.validation_error"))

    def _first_match_save_message(self, state):
        week_prefix = (
            f"{state.active_week.week_id}:" if state.active_week else ""
        )
        record = next(
            (
                item for item in state.match_records
                if getattr(item.match_role, "value", item.match_role)
                == "FIRST_WEEKLY_MATCH"
                and item.match_id.startswith(week_prefix)
            ),
            None,
        )
        if record is not None and record.planned_or_played == MatchStatus.PLANNED:
            return t("planner.first_match_planned")
        return t("planner.first_match_recorded")

    def _accept_training_plan(self):
        if hasattr(self._view, "accept_weekly_training_plan"):
            self._view.accept_weekly_training_plan()
            self._view.show_status(t("planner.plan_accepted"))

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
        self._last_selected_player_name = player_name
        self._show_squad_intelligence(player_name)

    def _show_squad_intelligence(self, player_name):
        if self._roster is None or not hasattr(self._view, "show_squad_intelligence"):
            return
        player = next(
            (p for p in self._roster.players if p.name == player_name), None
        )
        if player is None:
            self._view.clear_squad_intelligence()
            return
        if self._squad_intelligence_service is None:
            from ht_coach_app.services.squad_intelligence_service import (
                SquadIntelligenceAppService,
            )

            self._squad_intelligence_service = SquadIntelligenceAppService(
                weekly_training_service=self._weekly_training_service
            )
        try:
            report = self._squad_intelligence_service.generate_report(
                player, self._roster.players
            )
        except Exception:
            self._view.clear_squad_intelligence()
            return
        self._view.show_squad_intelligence(report)

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
        path = str(path or "")
        recent = [path] + [
            item for item in settings.recent_players_csv_paths
            if item != path
        ] if path else list(settings.recent_players_csv_paths)
        recent = recent[: self._settings_repository.MAX_RECENT_PLAYERS_CSV]
        self._settings_repository.save(
            MatchWorkspaceSettings(
                players_csv_path=path,
                recent_players_csv_paths=recent,
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
                match_section_states=getattr(
                    settings, "match_section_states", {}
                ),
            )
        )
        if hasattr(self._view, "set_recent_csv_paths"):
            self._view.set_recent_csv_paths(recent)
