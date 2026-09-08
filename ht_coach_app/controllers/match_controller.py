from PySide6.QtCore import QObject, QThread, QTimer

from dataclasses import dataclass, replace
import os
from uuid import uuid4

from engine.squad_health.availability_service import CURRENT_AVAILABLE
from ht_coach_app.change_analysis.service import ChangeAnalysisService
from ht_coach_app.core.localization import t
from ht_coach_app.core.paths import application_paths
from ht_coach_app.core.portable import portable_roster_copy
from ht_coach_app.diagnostics.runtime_integrity_trace import RuntimeIntegrityTracer
from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceSettings,
)
from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.services.match_workspace_service import (
    ANALYSIS_OWNER_NEW_MATCH_DRAFT,
    ANALYSIS_OWNER_SAVED_MATCH,
    MATCH_TYPE_CUP,
    MATCH_TYPE_FRIENDLY,
    MATCH_TYPE_LEAGUE,
    MatchWorkspaceValidationError,
    format_decision_lab,
    format_match_summary,
    format_recommended_lineup,
)
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from ht_coach_app.workers.match_analysis_worker import (
    MatchAnalysisWorker,
)


WORKSPACE_MODE_NEW_MATCH = "NEW_MATCH"
WORKSPACE_MODE_EDIT_SAVED_MATCH = "EDIT_SAVED_MATCH"


@dataclass(frozen=True)
class MatchWorkspaceMetadata:
    opponent_id: str = ""
    opponent_name: str = ""
    competition_type: str = ""
    venue_role: str = "unknown"
    scheduled_date: str = ""
    season_number: int | None = None
    competitive_week: int | None = None
    training_cycle_id: str = ""


@dataclass(frozen=True)
class SaveActiveMatchResult:
    match_record_id: str = ""
    revision: str = ""
    outcome: str = ""
    success: bool = False
    error: str = ""


class MatchController(QObject):
    def __init__(
        self,
        view,
        service,
        settings_repository,
        app_events=None,
        weekly_training_service=None,
        official_rating_service=None,
        season_calendar_repository=None,
        parent=None
    ):
        super().__init__(parent)
        self._view = view
        self._service = service
        self._settings_repository = settings_repository
        self._app_events = app_events
        self._weekly_training_service = (
            weekly_training_service or WeeklyTrainingAppService()
        )
        self._official_rating_service = official_rating_service
        self._season_calendar_repository = season_calendar_repository
        self._formation_board_mapper = FormationBoardMapper()
        self._change_analysis_service = ChangeAnalysisService()
        self._editing_snapshot_id = None
        self._workspace_mode = WORKSPACE_MODE_NEW_MATCH
        self._new_match_draft_id = self._make_new_match_draft_id()
        self._active_match_record_id = ""
        self._thread = None
        self._worker = None
        self._roster_players = []
        self._pending_workspace_state = None
        self._pending_training_context = None
        self._queued_workspace_state = None
        self._latest_workspace_revision = None
        self._runtime_trace = RuntimeIntegrityTracer()
        self._last_traced_board_formation = ""
        self._last_traced_recommended_formation = ""
        self._workspace_recalc_timer = QTimer(self)
        self._workspace_recalc_timer.setSingleShot(True)
        self._workspace_recalc_timer.setInterval(300)
        self._workspace_recalc_timer.timeout.connect(
            self._start_queued_workspace_recalculation
        )

        self._connect_view()
        self._connect_app_events()
        self.refresh()

    def _connect_view(self):
        self._view.browse_players_requested.connect(
            self._browse_players
        )
        self._view.load_players_requested.connect(
            self._load_players
        )
        self._view.analyze_requested.connect(
            self._analyze
        )
        self._view.copy_summary_requested.connect(
            self._copy_summary
        )
        self._view.copy_decision_lab_requested.connect(
            self._copy_decision_lab
        )
        self._view.copy_lineup_requested.connect(
            self._copy_lineup
        )
        if hasattr(self._view, "save_as_first_match_requested"):
            self._view.save_as_first_match_requested.connect(
                self._save_as_first_match
            )
        if hasattr(self._view, "save_as_second_match_requested"):
            self._view.save_as_second_match_requested.connect(
                self._save_as_second_match
            )
        if hasattr(self._view, "save_formation_requested"):
            self._view.save_formation_requested.connect(
                self._save_formation
            )
        if hasattr(self._view, "official_rating_import_requested"):
            self._view.official_rating_import_requested.connect(
                self._import_official_ratings
            )
        if hasattr(self._view, "workspace_recalculate_requested"):
            self._view.workspace_recalculate_requested.connect(
                self._recalculate_workspace
            )
        if hasattr(self._view, "match_date_changed"):
            self._view.match_date_changed.connect(
                self._update_season_preview
            )
            self._update_season_preview(self._current_match_date())
        self._view.workspace_changed.connect(
            self._handle_workspace_changed
        )
        if hasattr(self._view, "match_section_toggled"):
            self._view.match_section_toggled.connect(
                lambda _key, _expanded: self._save_current_settings()
            )

    def _connect_app_events(self):
        if self._app_events is not None:
            self._app_events.opponents_changed.connect(
                self._sync_opponents
            )
            self._app_events.roster_changed.connect(
                self._sync_roster
            )
            self._app_events.official_ratings_changed.connect(
                self._handle_official_ratings_changed_event
            )
            if hasattr(self._app_events, "weekly_plan_saved"):
                self._app_events.weekly_plan_saved.connect(
                    self._handle_weekly_plan_saved_event
                )

    def _handle_official_ratings_changed_event(self, changed_snapshot_id):
        self._trace_runtime_integrity(
            "MATCH_RECORDS_CHANGED",
            caller="_handle_official_ratings_changed_event",
            reason=f"official_ratings_changed:{changed_snapshot_id}",
        )
        self._handle_external_official_ratings_changed(changed_snapshot_id)

    def _handle_weekly_plan_saved_event(self):
        self._trace_runtime_integrity(
            "WEEKLY_PLANNER_CHANGED",
            caller="_handle_weekly_plan_saved_event",
            reason="weekly_plan_saved",
        )
        self._handle_weekly_plan_saved_for_match_context()

    def _trace_runtime_integrity(self, event_name, result=None, **extra):
        if not self._runtime_trace.enabled:
            return
        board_state = None
        try:
            if hasattr(self._view, "current_workspace_state"):
                board_state = self._view.current_workspace_state()
        except Exception:
            board_state = None
        board = getattr(board_state, "current_board", None)
        record = None
        try:
            record = self._current_workspace_record()
        except Exception:
            record = None
        last_result = None
        try:
            last_result = self._settings_repository.load_last_result()
        except Exception:
            last_result = None
        try:
            match_date = self._current_match_date()
        except Exception:
            match_date = ""
        cycle_id = ""
        if match_date:
            try:
                cycle_id = self._weekly_training_service.cycle_id_for_match_date(match_date)
            except Exception:
                cycle_id = ""
        cycle_id = (
            cycle_id
            or getattr(result, "training_cycle_id", "")
            or getattr(last_result, "training_cycle_id", "")
            or getattr(record, "training_cycle_id", "")
            or ""
        )

        weekly_record = self._linked_weekly_trace_record(
            getattr(record, "snapshot_id", "") if record is not None else "",
            cycle_id,
        )
        board_formation = getattr(board, "formation_name", "")
        recommended_formation = self._result_recommended_formation(result)
        saved_formation = self._saved_record_formation(record)
        weekly_formation = getattr(weekly_record, "formation", "")
        payload = {
            "active_match_record_id": self._active_match_record_id,
            "editing_snapshot_id": self._editing_snapshot_id,
            "workspace_mode": self._workspace_mode,
            "cycle_id": cycle_id,
            "weekly_revision": self._safe_weekly_revision(cycle_id),
            "board_formation": board_formation,
            "workspace_formation": getattr(board_state, "current_formation_name", ""),
            "saved_formation": saved_formation,
            "recommended_formation": recommended_formation,
            "analysis_result_formation": recommended_formation,
            "recommendation_id": getattr(result, "recommendation_id", ""),
            "recommendation_revision": getattr(
                result, "recommendation_revision", ""
            ),
            "manual_lineup_revision": getattr(
                result, "manual_lineup_revision", ""
            ),
            "competition_type": self._current_competition_type(
                getattr(result, "match_type", ""),
                show_error=False,
            ),
            "selection_policy": getattr(result, "selection_policy", ""),
            "rotation_summary": getattr(result, "rotation_summary", {}),
            "weekly_formation": weekly_formation,
            "weekly_match_formation": weekly_formation,
            "weekly_match_id": getattr(weekly_record, "match_id", ""),
            "weekly_linked_match_record_id": getattr(
                weekly_record, "linked_match_record_id", ""
            ),
            "last_result_formation": self._result_recommended_formation(last_result),
            "training_state": self._trace_training_state(cycle_id, result=result),
        }
        payload.update(extra)
        self._runtime_trace.emit(
            event_name,
            **payload,
        )
        self._trace_runtime_transitions(event_name, payload)

    def _trace_runtime_transitions(self, source_event, payload):
        board_formation = payload.get("board_formation", "")
        if board_formation:
            previous = self._last_traced_board_formation
            if previous and previous != board_formation:
                self._runtime_trace.emit(
                    "FORMATION_TRANSITION",
                    **payload,
                    from_formation=previous,
                    to_formation=board_formation,
                    source_event=source_event,
                )
            self._last_traced_board_formation = board_formation

        recommended_formation = payload.get("recommended_formation", "")
        if recommended_formation:
            previous = self._last_traced_recommended_formation
            if previous and previous != recommended_formation:
                self._runtime_trace.emit(
                    "RECOMMENDATION_TRANSITION",
                    **payload,
                    from_formation=previous,
                    to_formation=recommended_formation,
                    source_event=source_event,
                )
                if not self._recommendation_transition_allowed(
                    source_event,
                    payload,
                ):
                    self._runtime_trace.emit(
                        "ILLEGAL_RECOMMENDATION_MUTATION",
                        **payload,
                        old_id=previous,
                        new_id=recommended_formation,
                        source_event=source_event,
                    )
            self._last_traced_recommended_formation = recommended_formation
        if (
            source_event in {"RECOMMENDATION_RENDERED", "FORMATION_BOARD_REBUILT"}
            and board_formation
            and recommended_formation
            and board_formation == recommended_formation
        ):
            self._runtime_trace.emit(
                "RECOMMENDATION_APPLIED",
                **payload,
                source_event=source_event,
            )

    @staticmethod
    def _recommendation_transition_allowed(source_event, payload):
        return (
            source_event == "ANALYSIS_RESULT_RECEIVED"
            and payload.get("reason") == "primary_analysis"
        )

    def _safe_weekly_revision(self, cycle_id):
        if not cycle_id:
            return ""
        try:
            return self._weekly_training_service.weekly_cycle_revision(cycle_id)
        except Exception as exc:
            return f"error:{type(exc).__name__}"

    @staticmethod
    def _saved_record_formation(record):
        if record is None:
            return ""
        setup = getattr(record, "tactical_setup", None)
        return getattr(setup, "formation", "") or ""

    @staticmethod
    def _result_recommended_formation(result):
        recommended = getattr(result, "recommended_formation", None)
        return getattr(recommended, "formation_name", "") if recommended is not None else ""

    def _linked_weekly_trace_record(self, snapshot_id, cycle_id):
        try:
            state = self._weekly_training_service.load_state()
            records = tuple(getattr(state, "match_records", ()) or ())
            linked = [
                record for record in records
                if getattr(record, "linked_match_record_id", "") == snapshot_id
            ]
            if cycle_id:
                in_cycle = [
                    record for record in linked
                    if self._weekly_training_service._cycle_id_for_match_record(record)
                    == cycle_id
                ]
                if in_cycle:
                    return in_cycle[-1]
            if linked:
                return linked[-1]
        except Exception:
            return None
        return None

    def _trace_training_state(self, cycle_id, result=None):
        if not cycle_id:
            return {}
        target_name = os.environ.get(
            "HT_COACH_RUNTIME_TRACE_PLAYER",
            "Michael Rushton",
        )
        player = next(
            (
                item for item in self._roster_players
                if getattr(item, "name", "").casefold() == target_name.casefold()
            ),
            None,
        )
        state = None
        try:
            state = self._weekly_training_service.load_state()
        except Exception:
            state = None
        raw_priorities = []
        if state is not None:
            for key, record in getattr(state, "priorities", {}).items():
                if target_name.casefold() in str(key).casefold() or (
                    target_name.casefold()
                    in getattr(record, "player_name", "").casefold()
                ):
                    raw_priorities.append(
                        {
                            "stored_key": key,
                            "player_id": getattr(record, "player_id", ""),
                            "priority": getattr(
                                getattr(record, "priority", ""), "value", ""
                            ),
                        }
                    )
        if player is None:
            return {
                "player_name": target_name,
                "raw_priorities": raw_priorities,
                "training_priority_players": self._trace_training_priority_players(
                    cycle_id,
                    result,
                ),
            }
        try:
            from engine.weekly_training.player_identity import player_training_id

            player_id = player_training_id(player)
            requirement = self._weekly_training_service.explain_training_requirement(
                player_id,
                cycle_id,
                self._roster_players,
            )
            explanation = self._weekly_training_service.explain_weekly_player_state(
                player_id,
                cycle_id,
                self._roster_players,
            )
        except Exception as exc:
            return {
                "player_name": target_name,
                "raw_priorities": raw_priorities,
                "error": f"{type(exc).__name__}: {exc}",
            }
        selected_trace = self._trace_selected_player_state(target_name, result)
        return {
            "player_name": target_name,
            "player_id": player_id,
            "configured_priority": requirement.get("configured_priority", ""),
            "normalized_priority": requirement.get("configured_priority", ""),
            "required_slot_class": requirement.get("required_slot_class", ""),
            "current_week_actual_training": requirement.get(
                "current_week_actual_training", ()
            ),
            "plan_satisfied": requirement.get("plan_satisfied", False),
            "coverage": requirement.get("coverage_so_far", ""),
            "coverage_effective_minutes": requirement.get(
                "coverage_effective_minutes", ""
            ),
            "remaining_effective_minutes": requirement.get(
                "remaining_effective_minutes", ""
            ),
            "effective_optimizer_priority": requirement.get(
                "effective_optimizer_priority", ""
            ),
            "priority_source": requirement.get("reason", ""),
            "priority_revision": requirement.get("source_revision", ""),
            "match_1": explanation.get("match_1", ()),
            "match_2": explanation.get("match_2", ()),
            "other_cycles": explanation.get("other_cycles", ()),
            "selected_position": selected_trace.get("selected_position", ""),
            "selected_side": selected_trace.get("selected_side", ""),
            "selected_order": selected_trace.get("selected_order", ""),
            "selected_order_side": selected_trace.get("selected_order_side", ""),
            "candidate_position": selected_trace.get("selected_position", ""),
            "candidate_slot_class": selected_trace.get("candidate_slot_class", ""),
            "candidate_valid_for_priority": (
                selected_trace.get("candidate_slot_class", "")
                == requirement.get("required_slot_class", "")
                if requirement.get("required_slot_class", "")
                else ""
            ),
            "selected_formation": selected_trace.get("selected_formation", ""),
            "training_contribution_to_objective": selected_trace.get(
                "training_contribution_to_objective", ""
            ),
            "tactical_contribution_to_objective": selected_trace.get(
                "tactical_contribution_to_objective", ""
            ),
            "objective_trace_available": selected_trace.get(
                "objective_trace_available", False
            ),
            "raw_priorities": raw_priorities,
            "training_priority_players": self._trace_training_priority_players(
                cycle_id,
                result,
            ),
        }

    def _trace_training_priority_players(self, cycle_id, result=None):
        if not cycle_id:
            return ()
        try:
            from engine.weekly_training.models import TrainingPriority
            from engine.weekly_training.player_identity import player_training_id
            from engine.weekly_training.coverage import TARGET_MINUTES
        except Exception:
            return ()
        try:
            rows = self._weekly_training_service.priority_rows(self._roster_players)
            required_ids = self._weekly_training_service.required_player_ids_for_match(
                cycle_id
            )
            slot_classes = (
                self._weekly_training_service.required_player_training_slot_classes(
                    cycle_id,
                    self._roster_players,
                )
            )
        except Exception as exc:
            return ({"error": f"{type(exc).__name__}: {exc}"},)

        selected_names = set()
        selected_by_name = {}
        rotation_summary = getattr(result, "rotation_summary", {}) or {}
        match_1_ids = set(rotation_summary.get("match_1_player_ids", ()) or ())
        required_repeat_ids = set(
            rotation_summary.get("required_repeat_player_ids", ()) or ()
        )
        unnecessary_repeat_ids = set(
            rotation_summary.get("unnecessary_repeat_player_ids", ()) or ()
        )
        unused_selected_ids = set(
            rotation_summary.get("unused_selected_player_ids", ()) or ()
        )
        formation = getattr(result, "recommended_formation", None)
        if formation is not None:
            for player in getattr(formation, "lineup", ()) or ():
                name = getattr(player, "player_name", "")
                selected_names.add(name.casefold())
                selected_by_name[name.casefold()] = player

        traces = []
        for row in rows:
            priority = getattr(row.priority, "value", row.priority)
            if priority == TrainingPriority.NO_PRIORITY.value:
                continue
            player_id = row.player_id
            try:
                requirement = self._weekly_training_service.explain_training_requirement(
                    player_id,
                    cycle_id,
                    self._roster_players,
                )
            except Exception:
                requirement = {}
            required_slot_class = (
                requirement.get("required_slot_class", "")
                or slot_classes.get(player_id, "")
            )
            selected_player = selected_by_name.get(row.player_name.casefold())
            selected = selected_player is not None
            eligible = str(row.availability).casefold() == "available"
            played_match_1 = player_id in match_1_ids
            target = TARGET_MINUTES.get(row.priority, 0)
            remaining = requirement.get("required_remaining_exposure", "")
            already_covered = (
                priority in {
                    TrainingPriority.REQUIRED_100.value,
                    TrainingPriority.REQUIRED_50.value,
                }
                and player_id not in required_ids
            )
            candidate_slots = self._trace_candidate_slots_for_required_class(
                required_slot_class
            )
            if selected:
                rejection_reason = ""
                if player_id in unused_selected_ids:
                    rotation_class = "SELECTED_UNUSED_PLAYER"
                elif player_id in required_repeat_ids:
                    rotation_class = "SELECTED_REQUIRED_TRAINING_REPEAT"
                elif player_id in unnecessary_repeat_ids:
                    rotation_class = "SELECTED_LEGALITY_REQUIRED_REPEAT"
                else:
                    rotation_class = "SELECTED"
            elif not eligible:
                rejection_reason = "unavailable"
                rotation_class = "REJECTED_INJURED"
            elif already_covered:
                rejection_reason = "already_covered_by_match_1_or_saved_coverage"
                rotation_class = "REJECTED_UNNECESSARY_REPEAT"
            elif required_slot_class and not candidate_slots:
                rejection_reason = "no_matching_training_slot_in_selected_formations"
                rotation_class = "REJECTED_TRAINING_SLOT_MISMATCH"
            elif priority in {
                TrainingPriority.REQUIRED_100.value,
                TrainingPriority.REQUIRED_50.value,
            }:
                rejection_reason = "not_selected_despite_remaining_requirement"
                rotation_class = "REJECTED_TRAINING_SLOT_MISMATCH"
            else:
                rejection_reason = "not_required_for_optimizer"
                rotation_class = "REJECTED"
            traces.append(
                {
                    "player_id": player_id,
                    "player_name": row.player_name,
                    "priority": priority,
                    "required_slot_class": required_slot_class,
                    "eligible": eligible,
                    "played_match_1": played_match_1,
                    "availability": row.availability,
                    "already_covered_by_match_1": already_covered,
                    "target_exposure": str(target),
                    "remaining_required": remaining,
                    "candidate_slots": candidate_slots,
                    "selected": selected,
                    "selected_position": (
                        getattr(selected_player, "position", "") if selected else ""
                    ),
                    "rejection_reason": rejection_reason,
                    "rotation_class": rotation_class,
                    "effective_optimizer_priority": requirement.get(
                        "effective_optimizer_priority",
                        "",
                    ),
                }
            )
        return tuple(traces)

    def _trace_candidate_slots_for_required_class(self, required_slot_class):
        if not required_slot_class:
            return ()
        try:
            from models.formations import FORMATION_BY_NAME
            from models.position import Position
        except Exception:
            return ()
        rules = self._weekly_training_service.active_training_rules()
        slots = []
        for formation_name in (
            self._view.selected_formations()
            if hasattr(self._view, "selected_formations")
            else ()
        ):
            formation = FORMATION_BY_NAME.get(formation_name)
            if formation is None:
                continue
            for position, amount in formation.positions.items():
                position_value = getattr(position, "value", position)
                try:
                    slot_class = rules.slot_class_for_position(Position(position_value))
                except Exception:
                    continue
                if getattr(slot_class, "value", slot_class) == required_slot_class:
                    slots.append(
                        {
                            "formation": formation_name,
                            "position": str(position_value),
                            "count": int(amount),
                        }
                    )
        return tuple(slots)

    def _trace_selected_player_state(self, target_name, result):
        if result is None:
            return {}
        formation = getattr(result, "recommended_formation", None)
        if formation is None:
            return {}
        player = next(
            (
                lineup_player
                for lineup_player in getattr(formation, "lineup", ()) or ()
                if getattr(lineup_player, "player_name", "").casefold()
                == target_name.casefold()
            ),
            None,
        )
        if player is None:
            return {
                "selected_formation": getattr(formation, "formation_name", ""),
                "objective_trace_available": bool(
                    getattr(formation, "objective_trace", None)
                ),
            }
        objective_trace = getattr(formation, "objective_trace", {}) or {}
        components = objective_trace.get("components", {})
        final_score = components.get("final_objective_score", "")
        training_score = components.get("training_component", "")
        tactical_score = ""
        try:
            tactical_score = float(final_score) - float(training_score or 0.0)
        except (TypeError, ValueError):
            tactical_score = final_score
        return {
            "selected_formation": getattr(formation, "formation_name", ""),
            "selected_position": getattr(player, "position", ""),
            "selected_side": getattr(player, "side", ""),
            "selected_order": getattr(player, "order", ""),
            "selected_order_side": getattr(player, "order_side", ""),
            "candidate_slot_class": self._slot_class_label_for_position(
                getattr(player, "position", "")
            ),
            "training_contribution_to_objective": training_score,
            "tactical_contribution_to_objective": tactical_score,
            "objective_trace_available": bool(objective_trace),
        }

    def _slot_class_label_for_position(self, position):
        try:
            from ht_coach_app.core.position_formatting import normalize_position_key
            from models.position import Position

            rules = self._weekly_training_service.active_training_rules()
            slot_class = rules.slot_class_for_position(
                Position(normalize_position_key(position))
            )
            return getattr(slot_class, "value", str(slot_class or ""))
        except Exception:
            return ""

    def _handle_external_official_ratings_changed(self, changed_snapshot_id):
        """Alpha 0.6.7 HF-03, Part 17: a signal carrying match-scoped
        data must include the record ID, and receivers must ignore
        events for other records. This event can come from Official
        Intelligence importing evidence for a *completely different*
        match than whatever's open in this workspace -- refreshing
        with that unrelated snapshot's data would itself be a
        state-isolation bug, not a fix for one. Only refreshes when
        the changed record actually belongs to what's currently open
        here; otherwise the event is silently ignored, exactly as
        required."""
        current = self._current_workspace_record()
        if current is None or not changed_snapshot_id:
            return
        if current.snapshot_id != changed_snapshot_id:
            return
        self._refresh_after_official_import(changed_snapshot_id)

    def refresh(self):
        self._refresh_opponents()
        self._view.set_supported_formations(
            self._service.supported_formations(),
            favorite_formations=self._service.default_formations()
        )
        self._view.apply_settings(
            self._settings_repository.load()
        )
        self._load_current_roster_for_inspector(show_errors=False)
        last_result = self._current_workspace_result()

        if last_result is not None:
            self._show_training_context_from_result(last_result)
            self._view.show_results(
                last_result,
                restored=True
            )
            self._trace_runtime_integrity(
                "WORKSPACE_RESTORED",
                result=last_result,
                caller="refresh",
                reason="last_result",
            )
        elif hasattr(self._view, "clear_results"):
            self._view.clear_results()

    def start_new_match(self):
        if (
            hasattr(self._view, "is_workspace_dirty")
            and self._view.is_workspace_dirty()
        ):
            self._save_recovery_snapshot_if_dirty()
            if hasattr(self._view, "confirm_unsaved_changes"):
                choice = self._view.confirm_unsaved_changes()
                if choice == "cancel":
                    return False
                if choice == "save":
                    self._save_formation()

        self._workspace_mode = WORKSPACE_MODE_NEW_MATCH
        self._editing_snapshot_id = None
        self._active_match_record_id = ""
        self._new_match_draft_id = self._make_new_match_draft_id()
        self._pending_workspace_state = None
        self._queued_workspace_state = None
        self._latest_workspace_revision = None
        if hasattr(self._view, "reset_new_match_workspace"):
            self._view.reset_new_match_workspace()
        else:
            if hasattr(self._view, "exit_saved_match_edit_mode"):
                self._view.exit_saved_match_edit_mode()
            if hasattr(self._view, "reset_new_match_selectors"):
                self._view.reset_new_match_selectors()
            if hasattr(self._view, "clear_results"):
                self._view.clear_results()
        self._update_app_context(
            active_match_record_id="",
            opponent_name="",
            official_match_id="",
            current_action="new_match",
        )
        return True

    def _refresh_opponents(self, selected_name=None):
        opponents = self._service.list_opponents()
        self._view.set_opponents(
            [opponent.name for opponent in opponents],
            selected_name=selected_name
        )

    def _sync_opponents(
        self,
        action,
        previous_name,
        current_name
    ):
        selected_name = self._view.selected_opponent_name()

        if action == "updated" and selected_name == previous_name:
            selected_name = current_name
        elif action == "deleted" and selected_name == previous_name:
            selected_name = ""

        self._refresh_opponents(
            selected_name=selected_name
        )
        self._save_current_settings()

    def _sync_roster(self, players_csv_path, player_count):
        self._view.set_players_csv_path(
            players_csv_path
        )
        self._view.set_players_loaded_count(
            player_count
        )
        self._load_current_roster_for_inspector(show_errors=False, update_count=False)
        self._view.show_status(
            f"Roster updated from Squad: {player_count} players."
        )
        self._save_current_settings()

    def _browse_players(self):
        path = self._view.choose_players_file()

        if path:
            portable_path = portable_roster_copy(path)
            self._view.set_players_csv_path(portable_path)
            self._save_current_settings()
            self._load_players()

    def _load_players(self):
        try:
            players = self._service.load_players(
                self._resolved_players_csv_path(),
                availability_mode=self._availability_mode(),
            )
        except Exception as exc:
            self._view.show_error(
                str(exc)
            )
            return

        self._roster_players = players
        self._set_view_roster_players(players)
        self._view.set_players_loaded_count(
            len(players)
        )
        self._view.show_status(
            f"Loaded {len(players)} players."
        )
        self._save_current_settings()

    def _should_stop_for_existing_or_conflicting_match(self):
        """Alpha 0.6.7, Part 5-6: before starting a brand-new analysis,
        check whether an equivalent Match Record already exists (Part
        5) or a likely duplicate does (Part 6, e.g. the same opponent
        saved as both Liga and Copa in the same week). Returns True
        when the caller must stop (a dialog was shown and the flow is
        handled from here), False to let the normal analysis proceed.
        """
        repository = self._history_repository()
        if repository is None:
            return False
        if not hasattr(self._view, "show_existing_match_dialog") and not hasattr(
            self._view, "show_match_conflict_dialog"
        ):
            return False

        from datetime import date

        from engine.history.match_lookup import find_existing_or_conflicting_record

        opponent_name = self._view.selected_opponent_name()
        if not opponent_name:
            return False
        match_type = self._current_match_type()
        if match_type is None:
            return True
        competition_type = str(match_type).lower()
        match_date = (
            self._view.match_date()
            if hasattr(self._view, "match_date") and self._view.match_date()
            else date.today().isoformat()
        )

        result = find_existing_or_conflicting_record(
            repository, opponent_name, competition_type, match_date=match_date,
        )

        if result.kind == "exact" and hasattr(self._view, "show_existing_match_dialog"):
            if result.record.snapshot_id == self._editing_snapshot_id:
                # Already editing this exact record -- re-analyzing it
                # is expected, not a duplicate-detection case.
                return False
            wants_existing = self._view.show_existing_match_dialog()
            if wants_existing:
                self._open_existing_record_in_saved_matches(result.record)
            else:
                if hasattr(self._view, "reset_new_match_selectors"):
                    self._view.reset_new_match_selectors()
            return True

        if result.kind == "conflict" and hasattr(self._view, "show_match_conflict_dialog"):
            choice = self._view.show_match_conflict_dialog(
                opponent_name,
                self._competition_label(result.record.match_context.competition_type),
                self._competition_label(competition_type),
            )
            if choice == "correct":
                self._correct_existing_record_competition_type(result.record, competition_type)
                self._open_existing_record_in_saved_matches(result.record)
                return True
            if choice == "create_new":
                return False
            return True

        return False

    def _save_failure_result(self, action, exc):
        import traceback

        detail = f"{type(exc).__name__}: {exc}"
        self._record_app_event(action, self._active_match_record_id, "error", detail)
        self._record_app_event(
            f"{action}_traceback",
            self._active_match_record_id,
            "error",
            traceback.format_exc(),
        )
        if hasattr(self._view, "show_error"):
            self._view.show_error(t("match.save_workspace_error", reason=detail))
        return SaveActiveMatchResult(success=False, error=detail)

    def _save_active_match_workspace(
        self,
        result,
        action="save_active_match_workspace",
        emit_events=True,
        refresh_weekly_link=False,
    ):
        repository = self._history_repository()
        if repository is None:
            raise RuntimeError("history repository unavailable")
        if self._workspace_mode == WORKSPACE_MODE_EDIT_SAVED_MATCH:
            self._require_active_saved_match_record_id(action)
        if result is None or not getattr(result, "formations", None):
            raise RuntimeError(t("match.save_as_first_match_no_result"))
        result = self._result_with_active_workspace_lineup(result)
        if not self._confirm_match_type_for_save(result):
            return SaveActiveMatchResult(success=False, error=t("match.analysis_stale_match_type"))

        current_record = self._current_workspace_record()
        metadata = self._current_workspace_metadata(
            result=result,
            fallback_record=current_record,
        )
        if not self._validate_metadata_for_save(metadata):
            return SaveActiveMatchResult(success=False, error="invalid metadata")

        if getattr(result, "opponent_name", "") != metadata.opponent_name:
            result = replace(result, opponent_name=metadata.opponent_name)

        created = False
        record = current_record
        if record is None:
            from engine.history.provisional_record import find_or_create_provisional_record

            before = {
                existing.snapshot_id
                for existing in repository.list_all()
            }
            record = find_or_create_provisional_record(
                repository,
                opponent_name=metadata.opponent_name,
                match_date=metadata.scheduled_date,
                competition_type=metadata.competition_type,
                season_number=metadata.season_number,
                season_week=metadata.competitive_week,
                training_cycle_id=metadata.training_cycle_id,
                home_away=metadata.venue_role,
            )
            created = record.snapshot_id not in before

        record = self._save_metadata_to_canonical_record(record.snapshot_id, metadata)
        record = self._save_lineup_to_canonical_record(record.snapshot_id, result)
        self._trace_runtime_integrity(
            "HISTORICAL_MATCH_SAVED",
            result=result,
            caller="_save_active_match_workspace",
            reason=action,
            saved_match_record_id=record.snapshot_id,
            saved_record_formation=self._saved_record_formation(record),
            created=created,
        )

        self._workspace_mode = WORKSPACE_MODE_EDIT_SAVED_MATCH
        self._editing_snapshot_id = record.snapshot_id
        self._active_match_record_id = record.snapshot_id

        result = replace(result, opponent_name=metadata.opponent_name)
        result = self._stamp_result_owner(result)
        self._settings_repository.save_last_result(result)

        if hasattr(self._view, "enter_saved_match_edit_mode"):
            self._view.enter_saved_match_edit_mode(t("match.editing_saved_match"))
        if hasattr(self._view, "clear_metadata_dirty"):
            self._view.clear_metadata_dirty()
        board = getattr(self._view, "_formation_board_widget", None)
        if board is not None and hasattr(board, "mark_clean"):
            board.mark_clean()

        if refresh_weekly_link:
            self._refresh_linked_weekly_lineup(record.snapshot_id, result)
        self._discard_recovery_snapshot(record.snapshot_id)
        self._record_app_event(action, record.snapshot_id)
        self._update_app_context(
            active_match_record_id=record.snapshot_id,
            opponent_name=metadata.opponent_name,
            current_action=action,
        )

        if (
            emit_events
            and self._app_events is not None
            and hasattr(self._app_events, "match_records_changed")
        ):
            self._trace_runtime_integrity(
                "MATCH_RECORDS_CHANGED",
                result=result,
                caller="_save_active_match_workspace",
                reason=record.snapshot_id,
            )
            self._app_events.match_records_changed.emit(record.snapshot_id)

        persisted = repository.get(record.snapshot_id)
        if persisted is None:
            raise RuntimeError(f"saved match record not found: {record.snapshot_id}")
        self._assert_saved_metadata_matches_workspace(metadata, persisted)

        return SaveActiveMatchResult(
            match_record_id=record.snapshot_id,
            revision=persisted.updated_at,
            outcome="created" if created else "updated",
            success=True,
        )

    def _try_save_active_match_workspace(self, result, action, **kwargs):
        try:
            return self._save_active_match_workspace(result, action=action, **kwargs)
        except Exception as exc:
            return self._save_failure_result(action, exc)

    @staticmethod
    def _assert_saved_metadata_matches_workspace(metadata, record):
        persisted_type = getattr(
            record.match_context.competition_type,
            "value",
            record.match_context.competition_type,
        )
        persisted_venue = getattr(
            record.match_context.home_away,
            "value",
            record.match_context.home_away,
        )
        checks = {
            "opponent_id": (
                record.match_context.opponent.opponent_id or record.match_context.opponent.opponent_name,
                metadata.opponent_id or metadata.opponent_name,
            ),
            "opponent_name": (
                record.match_context.opponent.opponent_name,
                metadata.opponent_name,
            ),
            "competition_type": (str(persisted_type).lower(), metadata.competition_type),
            "venue_role": (str(persisted_venue).lower(), metadata.venue_role),
            "scheduled_date": (record.match_context.match_date, metadata.scheduled_date),
            "season_number": (record.ht_season_number, metadata.season_number),
            "competitive_week": (record.ht_season_week, metadata.competitive_week),
            "training_cycle_id": (record.training_cycle_id, metadata.training_cycle_id),
        }
        mismatches = [
            f"{field}: persisted={persisted!r} workspace={expected!r}"
            for field, (persisted, expected) in checks.items()
            if persisted != expected
        ]
        if mismatches:
            raise RuntimeError(
                "saved match metadata invariant failed: " + "; ".join(mismatches)
            )

    def _linked_canonical_record_id(self, result):
        """Alpha 0.6.7, Part 19: the canonical Match Record this saved
        weekly lineup belongs to. If we're already editing a specific
        record, that's it -- no lookup needed. Otherwise, finds or
        creates the provisional record for this exact match (reusing
        Part 11's own creation flow), so saving from Match never
        creates a second, disconnected weekly-only identity."""
        saved = self._try_save_active_match_workspace(
            result,
            "link_canonical_match_record",
            emit_events=True,
        )
        return saved.match_record_id if saved.success else ""

    def _history_repository(self):
        service = getattr(self, "_official_rating_service", None)
        return getattr(service, "_repository", None) if service is not None else None

    def _current_workspace_metadata(self, result=None, fallback_record=None):
        opponent_identity = (
            self._view.selected_opponent_identity()
            if hasattr(self._view, "selected_opponent_identity")
            else {}
        )
        opponent_name = (
            opponent_identity.get("opponent_name")
            or (
                self._view.selected_opponent_name()
                if hasattr(self._view, "selected_opponent_name")
                else ""
            )
            or getattr(result, "opponent_name", "")
            or (
                fallback_record.match_context.opponent.opponent_name
                if fallback_record is not None
                else ""
            )
        )
        from ht_coach_app.services.match_display_formatter import (
            extract_opponent_name_from_match_identity,
        )

        opponent_name = extract_opponent_name_from_match_identity(opponent_name)
        opponent_id = (
            opponent_identity.get("opponent_id")
            or opponent_name
            or (
                fallback_record.match_context.opponent.opponent_id
                if fallback_record is not None
                else ""
            )
        )
        match_date = self._current_match_date() or (
            fallback_record.match_context.match_date
            if fallback_record is not None
            else ""
        )
        competition_type = self._current_competition_type(
            fallback=(
                fallback_record.match_context.competition_type
                if fallback_record is not None
                else ""
            ),
            show_error=False,
        )
        venue_role = (
            self._view.venue_role()
            if hasattr(self._view, "venue_role")
            else (
                fallback_record.match_context.home_away
                if fallback_record is not None
                else "unknown"
            )
        )
        venue_role = getattr(venue_role, "value", venue_role) or "unknown"
        season_week = self._resolve_season_week(match_date) if match_date else None
        return MatchWorkspaceMetadata(
            opponent_id=opponent_id,
            opponent_name=opponent_name,
            competition_type=competition_type,
            venue_role=str(venue_role).lower(),
            scheduled_date=match_date,
            season_number=(
                season_week.season_number
                if season_week is not None and season_week.is_known
                else (
                    fallback_record.ht_season_number
                    if fallback_record is not None
                    else None
                )
            ),
            competitive_week=(
                season_week.season_week
                if season_week is not None and season_week.is_known
                else (
                    fallback_record.ht_season_week
                    if fallback_record is not None
                    else None
                )
            ),
            training_cycle_id=(
                self._training_cycle_id_for_match_date(match_date)
                if match_date
                else (
                    fallback_record.training_cycle_id
                    if fallback_record is not None
                    else ""
                )
            ),
        )

    def _validate_metadata_for_save(self, metadata):
        if not metadata.opponent_name:
            self._view.show_error(t("match.save_as_first_match_no_result"))
            return False
        if metadata.competition_type not in {"league", "cup", "friendly"}:
            self._view.show_error(t("match.invalid_match_type"))
            return False
        if metadata.venue_role not in {"home", "away", "neutral", "unknown"}:
            self._view.show_error(t("match.venue_role_required"))
            return False
        if not metadata.scheduled_date:
            self._view.show_error(t("match.save_as_weekly_missing_match_date"))
            return False
        return True

    @staticmethod
    def _competition_label(competition_type):
        from ht_coach_app.core.localization import t

        value = getattr(competition_type, "value", competition_type)
        return t(f"official_match_intelligence.history.competition.{str(value).lower()}")

    def _open_existing_record_in_saved_matches(self, record):
        if self._app_events is not None and hasattr(
            self._app_events, "open_saved_match_requested"
        ):
            self._app_events.open_saved_match_requested.emit(record.snapshot_id)

    def _correct_existing_record_competition_type(self, record, competition_type):
        repository = self._history_repository()
        if repository is None:
            return
        from engine.history.models import MatchContext

        updated_context = MatchContext(
            official_match_id=record.match_context.official_match_id,
            match_date=record.match_context.match_date,
            kickoff_time=record.match_context.kickoff_time,
            season=record.match_context.season,
            round=record.match_context.round,
            competition_type=competition_type,
            match_type=record.match_context.match_type,
            home_away=record.match_context.home_away,
            team_type=record.match_context.team_type,
            opponent=record.match_context.opponent,
            venue=record.match_context.venue,
            snapshot_stage=record.match_context.snapshot_stage,
        )
        repository.save(record.with_updates(match_context=updated_context))

    def _reconcile_saved_opponent_reference(self, record):
        repository = self._history_repository()
        if repository is None or record.match_context.opponent is None:
            return record
        from ht_coach_app.services.match_display_formatter import (
            extract_opponent_name_from_match_identity,
        )

        current_reference = record.match_context.opponent
        cleaned_name = extract_opponent_name_from_match_identity(
            current_reference.opponent_name
        )
        if not cleaned_name:
            return record
        managed_matches = [
            opponent for opponent in self._service.list_opponents()
            if opponent.name == cleaned_name
        ]
        if len(managed_matches) > 1:
            return record
        opponent_id = (
            managed_matches[0].name
            if len(managed_matches) == 1
            else (current_reference.opponent_id or cleaned_name)
        )
        if (
            current_reference.opponent_name == cleaned_name
            and current_reference.opponent_id == opponent_id
        ):
            return record

        from engine.history.models import MatchContext

        updated_context = MatchContext(
            official_match_id=record.match_context.official_match_id,
            match_date=record.match_context.match_date,
            kickoff_time=record.match_context.kickoff_time,
            season=record.match_context.season,
            round=record.match_context.round,
            competition_type=record.match_context.competition_type,
            match_type=record.match_context.match_type,
            home_away=record.match_context.home_away,
            team_type=record.match_context.team_type,
            opponent=replace(
                current_reference,
                opponent_id=opponent_id,
                opponent_name=cleaned_name,
            ),
            venue=record.match_context.venue,
            snapshot_stage=record.match_context.snapshot_stage,
        )
        return repository.save(record.with_updates(match_context=updated_context))

    def edit_record(self, snapshot_id):
        """Alpha 0.6.7, Part 8: opens the same Match analysis workspace
        used for a new analysis, pre-populated with whatever the saved
        record has (opponent, competition type, date). Any change from
        here on updates the *same* canonical record --
        `_editing_snapshot_id` is checked by the duplicate-detection
        flow so re-analyzing this exact match never triggers "an
        analysis for this already exists" against itself.

        Alpha 0.6.7 HF-03, Part 12: switching away from a dirty
        workspace never silently loses or transfers changes -- the
        person explicitly chooses to save, discard, or stay."""
        if snapshot_id == self._editing_snapshot_id:
            # Already open; re-opening the same record is not a
            # "switch" and never needs a prompt.
            return
        if hasattr(self._view, "is_workspace_dirty") and self._view.is_workspace_dirty():
            if not hasattr(self._view, "confirm_unsaved_changes"):
                return
            self._save_recovery_snapshot_if_dirty()
            choice = self._view.confirm_unsaved_changes()
            if choice == "cancel":
                return
            if choice == "save":
                self._save_formation()

        repository = self._history_repository()
        if repository is None:
            return
        record = repository.get(snapshot_id)
        if record is None:
            return
        record = self._reconcile_saved_opponent_reference(record)

        self._workspace_mode = WORKSPACE_MODE_EDIT_SAVED_MATCH
        self._editing_snapshot_id = snapshot_id
        self._active_match_record_id = snapshot_id
        self._pending_workspace_state = None
        self._queued_workspace_state = None
        self._latest_workspace_revision = None
        if hasattr(self._view, "clear_results"):
            self._view.clear_results()
        self._record_app_event("switch_record", snapshot_id)
        self._trace_runtime_integrity(
            "MATCH_OPENED",
            caller="edit_record",
            reason=snapshot_id,
        )
        self._update_app_context(
            active_match_record_id=snapshot_id,
            opponent_name=record.match_context.opponent.opponent_name,
            official_match_id=record.match_context.official_match_id,
            current_action="edit_record",
        )

        opponent_name = record.match_context.opponent.opponent_name
        if opponent_name:
            self._refresh_opponents(selected_name=opponent_name)

        if hasattr(self._view, "set_match_type"):
            competition_value = getattr(
                record.match_context.competition_type,
                "value",
                record.match_context.competition_type,
            )
            competition_value = str(competition_value or "").lower()
            if competition_value == "cup":
                match_type = MATCH_TYPE_CUP
            elif competition_value == "league":
                match_type = MATCH_TYPE_LEAGUE
            elif competition_value == "friendly":
                match_type = MATCH_TYPE_FRIENDLY
            else:
                match_type = ""
            self._view.set_match_type(match_type)

        if record.match_context.match_date:
            if hasattr(self._view, "set_match_date"):
                self._view.set_match_date(record.match_context.match_date)
        elif hasattr(self._view, "clear_match_date"):
            self._view.clear_match_date()

        if hasattr(self._view, "set_venue_role"):
            venue_value = getattr(
                record.match_context.home_away, "value", record.match_context.home_away
            )
            self._view.set_venue_role(venue_value or "unknown")

        if hasattr(self._view, "enter_saved_match_edit_mode"):
            self._view.enter_saved_match_edit_mode(
                t("match.editing_saved_match")
            )
        self._update_season_preview(record.match_context.match_date)
        self._update_metadata_evidence_warning()
        self._restore_saved_roster(record)
        self._restore_full_workspace_if_available(record, opponent_name)

    def _handle_workspace_changed(self):
        self._save_current_settings()
        self._update_metadata_evidence_warning()
        self._trace_runtime_integrity(
            "FORMATION_BOARD_CHANGED",
            caller="_handle_workspace_changed",
            reason="workspace_changed",
        )

    def _update_metadata_evidence_warning(self):
        if not hasattr(self._view, "set_metadata_evidence_warning"):
            return
        record = self._current_workspace_record()
        if record is None or not (record.official_pre or record.official_post):
            self._view.set_metadata_evidence_warning("")
            return
        if self._metadata_differs_from_record(record):
            self._view.set_metadata_evidence_warning(
                t("match.metadata_official_evidence_warning")
            )
        else:
            self._view.set_metadata_evidence_warning("")

    def _metadata_differs_from_record(self, record):
        current_opponent = (
            self._view.selected_opponent_name()
            if hasattr(self._view, "selected_opponent_name")
            else ""
        )
        current_date = self._current_match_date() or ""
        current_match_type = self._current_match_type(show_error=False)
        current_type = str(current_match_type or "").lower()
        record_type = str(
            getattr(
                record.match_context.competition_type,
                "value",
                record.match_context.competition_type,
            )
            or ""
        ).lower()
        return (
            current_opponent != (record.match_context.opponent.opponent_name or "")
            or current_date != (record.match_context.match_date or "")
            or current_type != record_type
            or (
                (
                    self._view.venue_role()
                    if hasattr(self._view, "venue_role")
                    else "unknown"
                )
                != str(
                    getattr(
                        record.match_context.home_away,
                        "value",
                        record.match_context.home_away,
                    )
                    or "unknown"
                ).lower()
            )
        )

    def _restore_full_workspace_if_available(self, record, opponent_name):
        """Alpha 0.6.7, Part 8's remaining piece. `HistoricalMatchSnapshot`
        is a thin, denormalized history record -- it was never meant to
        carry a full re-analyzable workspace (boards, ratings,
        optimizer output). The only place that full state actually
        lives is `MatchWorkspaceRepository`'s single "last analyzed
        result" slot, which isn't keyed per canonical record. Best
        effort: if that cached result happens to be for the same
        opponent as the record being edited (the common case right
        after saving), restore it in full; otherwise, tell the user a
        fresh analysis is needed rather than silently showing nothing
        or stale data from an unrelated match."""
        restored_result = self._result_from_saved_record(record)
        restored_from_weekly_link = False
        if restored_result is None:
            restored_result = self._result_from_linked_weekly_record(record)
            restored_from_weekly_link = restored_result is not None
        if restored_result is not None:
            self._pending_workspace_state = None
            self._settings_repository.save_last_result(restored_result)
            self._show_training_context_from_result(restored_result)
            self._view.show_results(restored_result, restored=True)
            self._trace_runtime_integrity(
                "WORKSPACE_RESTORED",
                result=restored_result,
                caller="_restore_full_workspace_if_available",
                reason="saved_record",
            )
            self._restore_tactical_controls_from_record(record)
            self._update_pre_status_and_ratings_panel()
            if hasattr(self._view, "show_status"):
                self._view.show_status(
                    t("match.saved_formation_restored")
                    if record.lineup or restored_from_weekly_link
                    else t("match.historical_lineup_missing")
                )
            return

        last_result = self._settings_repository.load_last_result()
        matches_this_record = self._analysis_result_belongs_to_saved_record(
            last_result,
            record.snapshot_id,
        )
        if matches_this_record:
            self._pending_workspace_state = None
            self._show_training_context_from_result(last_result)
            self._view.show_results(last_result, restored=True)
            self._trace_runtime_integrity(
                "WORKSPACE_RESTORED",
                result=last_result,
                caller="_restore_full_workspace_if_available",
                reason="last_result_same_owner",
            )
            self._restore_tactical_controls_from_record(record)
            self._update_pre_status_and_ratings_panel()
            return

        reconstruction_result = self._empty_historical_reconstruction_result(record)
        if reconstruction_result is not None:
            self._pending_workspace_state = None
            self._settings_repository.save_last_result(reconstruction_result)
            self._show_training_context_from_result(reconstruction_result)
            self._view.show_results(reconstruction_result, restored=True)
            self._restore_tactical_controls_from_record(record)
            self._update_pre_status_and_ratings_panel()
            if hasattr(self._view, "show_status"):
                self._view.show_status(t("match.historical_lineup_missing"))
            return

        if hasattr(self._view, "show_status"):
            self._view.show_status(
                t("match.historical_lineup_missing")
            )

    def _restore_saved_roster(self, record):
        csv_path = getattr(record.provenance, "roster_source", "") or ""
        if not csv_path:
            return
        if hasattr(self._view, "set_players_csv_path"):
            self._view.set_players_csv_path(csv_path)
        settings = self._settings_repository.remember_players_csv_path(csv_path)
        if hasattr(self._view, "set_recent_csv_paths"):
            self._view.set_recent_csv_paths(settings.recent_players_csv_paths)
        try:
            players = self._service.load_players(
                csv_path,
                availability_mode=self._availability_mode(),
            )
        except Exception as exc:
            self._roster_players = []
            self._set_view_roster_players([])
            if hasattr(self._view, "set_players_loaded_count"):
                self._view.set_players_loaded_count(0)
            if hasattr(self._view, "show_error"):
                self._view.show_error(
                    t("match.saved_csv_unavailable", reason=str(exc))
                )
            return
        self._roster_players = players
        self._set_view_roster_players(players)
        if hasattr(self._view, "set_players_loaded_count"):
            self._view.set_players_loaded_count(len(players))

    def _result_from_saved_record(self, record):
        if not record.tactical_setup.formation:
            return None
        from pathlib import Path

        from ht_coach_app.services.match_workspace_service import (
            FormationAnalysisResult,
            LineupPlayerResult,
            MatchAnalysisResult,
            TeamRatingsResult,
        )

        competition_value = getattr(
            record.match_context.competition_type,
            "value",
            record.match_context.competition_type,
        )
        match_type = (
            MATCH_TYPE_CUP
            if str(competition_value).lower() == "cup"
            else (
                MATCH_TYPE_LEAGUE
                if str(competition_value).lower() == "league"
                else ""
            )
        )
        lineup = [
            LineupPlayerResult(
                number=entry.number or index + 1,
                position=entry.position,
                side=entry.side,
                order=entry.individual_order,
                order_side=entry.order_side,
                player_name=entry.player_name,
            )
            for index, entry in enumerate(record.lineup)
        ]
        formation = FormationAnalysisResult(
            formation_name=record.tactical_setup.formation,
            recommended_tactic=record.tactical_setup.selected_tactic or "Normal",
            tactic_level=float(record.tactical_setup.tactic_level or 0.0),
            win_probability=0.0,
            draw_probability=0.0,
            loss_probability=0.0,
            possession=0.0,
            expected_goals=0.0,
            opponent_expected_goals=0.0,
            is_recommended=True,
            team_ratings=TeamRatingsResult(),
            lineup=lineup,
        )
        csv_path = getattr(record.provenance, "roster_source", "") or ""
        return MatchAnalysisResult(
            player_count=len(self._roster_players) if self._roster_players else len(lineup),
            opponent_name=record.match_context.opponent.opponent_name,
            formations=[formation],
            players_csv_filename=Path(csv_path).name if csv_path else "",
            analyzed_formations=[record.tactical_setup.formation],
            completed_at=record.updated_at,
            match_type=match_type,
            analysis_owner_type=ANALYSIS_OWNER_SAVED_MATCH,
            analysis_owner_id=record.snapshot_id,
            recommendation_id=record.tactical_setup.formation,
        )

    def _result_from_linked_weekly_record(self, record):
        linked = None
        if self._weekly_training_service is not None:
            state = self._weekly_training_service.load_state()
            linked = next(
                (
                    item
                    for item in getattr(state, "match_records", ()) or ()
                    if item.linked_match_record_id == record.snapshot_id
                ),
                None,
            )
        if linked is None or not linked.formation:
            return None

        from pathlib import Path

        from ht_coach_app.services.match_workspace_service import (
            FormationAnalysisResult,
            LineupPlayerResult,
            MatchAnalysisResult,
            TeamRatingsResult,
        )

        lineup = [
            LineupPlayerResult(
                number=index + 1,
                position=entry.position,
                side=entry.side,
                order=entry.order,
                order_side=entry.order_side,
                player_name=entry.player_name,
            )
            for index, entry in enumerate(linked.lineup)
        ]
        formation = FormationAnalysisResult(
            formation_name=linked.formation,
            recommended_tactic=record.tactical_setup.selected_tactic or "Normal",
            tactic_level=float(record.tactical_setup.tactic_level or 0.0),
            win_probability=0.0,
            draw_probability=0.0,
            loss_probability=0.0,
            possession=0.0,
            expected_goals=0.0,
            opponent_expected_goals=0.0,
            is_recommended=True,
            team_ratings=TeamRatingsResult(),
            lineup=lineup,
        )
        csv_path = getattr(record.provenance, "roster_source", "") or ""
        return MatchAnalysisResult(
            player_count=len(self._roster_players) if self._roster_players else len(lineup),
            opponent_name=record.match_context.opponent.opponent_name,
            formations=[formation],
            players_csv_filename=Path(csv_path).name if csv_path else "",
            analyzed_formations=[linked.formation],
            completed_at=record.updated_at,
            match_type=self._match_type_from_record(record),
            analysis_owner_type=ANALYSIS_OWNER_SAVED_MATCH,
            analysis_owner_id=record.snapshot_id,
            recommendation_id=linked.formation,
        )

    def _empty_historical_reconstruction_result(self, record):
        if not record.tactical_setup.formation and not self._roster_players:
            return None
        from pathlib import Path

        from models.formations import DEFAULT_FORMATION_NAMES
        from ht_coach_app.services.match_workspace_service import (
            FormationAnalysisResult,
            MatchAnalysisResult,
            TeamRatingsResult,
        )

        selected = (
            self._view.selected_formations()
            if hasattr(self._view, "selected_formations")
            else ()
        )
        formation_names = list(
            selected
            or (
                [record.tactical_setup.formation]
                if record.tactical_setup.formation
                else DEFAULT_FORMATION_NAMES
            )
        )
        if not formation_names:
            return None
        formations = [
            FormationAnalysisResult(
                formation_name=name,
                recommended_tactic=record.tactical_setup.selected_tactic or "Normal",
                tactic_level=float(record.tactical_setup.tactic_level or 0.0),
                win_probability=0.0,
                draw_probability=0.0,
                loss_probability=0.0,
                possession=0.0,
                expected_goals=0.0,
                opponent_expected_goals=0.0,
                is_recommended=index == 0,
                team_ratings=TeamRatingsResult(),
                lineup=[],
            )
            for index, name in enumerate(formation_names)
        ]
        csv_path = getattr(record.provenance, "roster_source", "") or ""
        return MatchAnalysisResult(
            player_count=len(self._roster_players),
            opponent_name=record.match_context.opponent.opponent_name,
            formations=formations,
            players_csv_filename=Path(csv_path).name if csv_path else "",
            analyzed_formations=formation_names,
            completed_at=record.updated_at,
            match_type=self._match_type_from_record(record),
            analysis_owner_type=ANALYSIS_OWNER_SAVED_MATCH,
            analysis_owner_id=record.snapshot_id,
            recommendation_id=formation_names[0],
        )

    @staticmethod
    def _match_type_from_record(record):
        competition_value = getattr(
            record.match_context.competition_type,
            "value",
            record.match_context.competition_type,
        )
        if str(competition_value).lower() == "cup":
            return MATCH_TYPE_CUP
        if str(competition_value).lower() == "league":
            return MATCH_TYPE_LEAGUE
        if str(competition_value).lower() == "friendly":
            return MATCH_TYPE_FRIENDLY
        return ""

    def _restore_tactical_controls_from_record(self, record):
        if hasattr(self._view, "set_tactic"):
            self._view.set_tactic(record.tactical_setup.selected_tactic or "")
        if hasattr(self._view, "set_team_attitude"):
            self._view.set_team_attitude(record.tactical_setup.team_attitude or "")

    def _make_new_match_draft_id(self):
        return f"new-match:{uuid4()}"

    def _stamp_result_owner(self, result):
        if (
            self._workspace_mode == WORKSPACE_MODE_EDIT_SAVED_MATCH
            and self._editing_snapshot_id
        ):
            return replace(
                result,
                analysis_owner_type=ANALYSIS_OWNER_SAVED_MATCH,
                analysis_owner_id=self._editing_snapshot_id,
            )
        return replace(
            result,
            analysis_owner_type=ANALYSIS_OWNER_NEW_MATCH_DRAFT,
            analysis_owner_id=self._new_match_draft_id,
        )

    def _analysis_result_belongs_to_saved_record(self, result, snapshot_id):
        return (
            result is not None
            and getattr(result, "analysis_owner_type", "") == ANALYSIS_OWNER_SAVED_MATCH
            and getattr(result, "analysis_owner_id", "") == snapshot_id
        )

    def _analysis_result_belongs_to_current_workspace(self, result):
        if result is None:
            return False
        owner_type = getattr(result, "analysis_owner_type", "")
        owner_id = getattr(result, "analysis_owner_id", "")
        if (
            self._workspace_mode == WORKSPACE_MODE_EDIT_SAVED_MATCH
            and self._editing_snapshot_id
        ):
            return (
                owner_type == ANALYSIS_OWNER_SAVED_MATCH
                and owner_id == self._editing_snapshot_id
            )
        return (
            owner_type == ANALYSIS_OWNER_NEW_MATCH_DRAFT
            and owner_id == self._new_match_draft_id
        )

    def _current_workspace_result(self, include_legacy=False):
        result = self._settings_repository.load_last_result()
        if self._analysis_result_belongs_to_current_workspace(result):
            return result
        if (
            include_legacy
            and result is not None
            and not getattr(result, "analysis_owner_type", "")
            and not getattr(result, "analysis_owner_id", "")
        ):
            return result
        return None

    def _current_or_saved_workspace_result(self, include_legacy=False):
        result = self._current_workspace_result(include_legacy=include_legacy)
        if result is not None:
            return result
        record = self._current_workspace_record()
        if record is None:
            return None
        return self._result_from_saved_record(record) or self._result_from_linked_weekly_record(record)

    def _result_with_active_workspace_lineup(self, result):
        """Return `result` with the Formation Board's visible lineup as
        the active saved formation.

        The optimizer recommendation and the user-editable workspace
        are intentionally separate concepts. When the user saves or
        imports official evidence, the visible board is the tactical
        plan that must be preserved.
        """
        state_getter = getattr(self._view, "current_workspace_state", None)
        state = state_getter() if callable(state_getter) else None
        board = getattr(state, "current_board", None)
        if board is None or not getattr(board, "slots", None):
            return result

        from ht_coach_app.services.match_workspace_service import LineupPlayerResult

        original_lineup = tuple(
            getattr(getattr(result, "recommended_formation", None), "lineup", ()) or ()
        )
        lineup = [
            LineupPlayerResult(
                number=index + 1,
                position=slot.player.position,
                side=slot.side or slot.player.side,
                order=slot.player.individual_order,
                order_side=slot.player.order_side,
                player_name=slot.player.player_name,
            )
            for index, slot in enumerate(board.slots)
            if slot.player is not None
        ]
        if (
            len(lineup) != 11
            and len(original_lineup) == 11
            and board.formation_name == getattr(
                getattr(result, "recommended_formation", None),
                "formation_name",
                "",
            )
        ):
            return result
        if not lineup:
            return result

        formations = list(getattr(result, "formations", ()) or ())
        base_formation = next(
            (
                formation
                for formation in formations
                if formation.formation_name == board.formation_name
            ),
            None,
        )
        if base_formation is None:
            base_formation = getattr(result, "recommended_formation", None)
        if base_formation is None:
            return result

        selected_tactic = (
            self._view.tactic() if hasattr(self._view, "tactic") else ""
        )
        recommendation_id = self._stable_recommendation_id(result)
        active_formation = replace(
            base_formation,
            formation_name=board.formation_name,
            recommended_tactic=selected_tactic or base_formation.recommended_tactic,
            tactic_level=getattr(board, "tactic_level", base_formation.tactic_level),
            lineup=lineup,
            is_recommended=(board.formation_name == recommendation_id),
        )
        updated_formations = [
            (
                active_formation
                if formation.formation_name == active_formation.formation_name
                else replace(
                    formation,
                    is_recommended=(formation.formation_name == recommendation_id),
                )
            )
            for formation in formations
        ]
        if not any(
            formation.formation_name == active_formation.formation_name
            for formation in formations
        ):
            updated_formations.insert(0, active_formation)
        return replace(
            result,
            formations=updated_formations,
            recommendation_id=recommendation_id,
        )

    def _active_workspace_formation(self, result):
        state_getter = getattr(self._view, "current_workspace_state", None)
        state = state_getter() if callable(state_getter) else None
        board = getattr(state, "current_board", None)
        if board is None or not getattr(board, "slots", None):
            return getattr(result, "recommended_formation", None)

        from ht_coach_app.services.match_workspace_service import LineupPlayerResult

        original = getattr(result, "recommended_formation", None)
        original_lineup = tuple(getattr(original, "lineup", ()) or ())
        lineup = [
            LineupPlayerResult(
                number=index + 1,
                position=slot.player.position,
                side=slot.side or slot.player.side,
                order=slot.player.individual_order,
                order_side=slot.player.order_side,
                player_name=slot.player.player_name,
            )
            for index, slot in enumerate(board.slots)
            if slot.player is not None
        ]
        if (
            len(lineup) != 11
            and len(original_lineup) == 11
            and board.formation_name == getattr(original, "formation_name", "")
        ):
            return original
        if not lineup:
            return original

        formations = list(getattr(result, "formations", ()) or ())
        base_formation = next(
            (
                formation
                for formation in formations
                if formation.formation_name == board.formation_name
            ),
            None,
        ) or getattr(result, "recommended_formation", None)
        if base_formation is None:
            return None
        selected_tactic = (
            self._view.tactic() if hasattr(self._view, "tactic") else ""
        )
        return replace(
            base_formation,
            formation_name=board.formation_name,
            recommended_tactic=selected_tactic or base_formation.recommended_tactic,
            tactic_level=getattr(board, "tactic_level", base_formation.tactic_level),
            lineup=lineup,
            is_recommended=False,
        )

    @staticmethod
    def _stable_recommendation_id(result):
        explicit_id = str(getattr(result, "recommendation_id", "") or "").strip()
        if explicit_id:
            return explicit_id
        recommended = getattr(result, "recommended_formation", None)
        return getattr(recommended, "formation_name", "")

    def _capture_visible_lineup_board(self, result=None):
        state_getter = getattr(self._view, "current_workspace_state", None)
        state = state_getter() if callable(state_getter) else None
        board = getattr(state, "current_board", None)
        if board is not None:
            board_count = len(
                [
                    slot
                    for slot in getattr(board, "slots", ()) or ()
                    if getattr(slot, "player", None) is not None
                ]
            )
            recommended = getattr(result, "recommended_formation", None)
            if (
                board_count == 11
                or len(getattr(recommended, "lineup", ()) or ()) != 11
                or board.formation_name != getattr(recommended, "formation_name", "")
            ):
                return board
        recommended = getattr(result, "recommended_formation", None)
        if recommended is None:
            return None
        return self._formation_board_mapper.to_board(recommended)

    @staticmethod
    def _assert_visible_board_matches_weekly_record(board, state, linked_match_record_id=""):
        if board is None:
            return
        records = tuple(getattr(state, "match_records", ()) or ())
        if not records:
            raise RuntimeError("weekly lineup save invariant failed: no weekly record")
        saved = next(
            (
                record
                for record in records
                if linked_match_record_id
                and record.linked_match_record_id == linked_match_record_id
            ),
            records[-1],
        )
        if saved.formation != board.formation_name:
            raise RuntimeError(
                "weekly lineup save invariant failed: "
                f"visible={board.formation_name!r} persisted={saved.formation!r}"
            )

    def _analyze(self):
        if self._selected_opponent_requires_manager_restore():
            self._view.show_error(t("match.saved_opponent_missing_analyze_blocked"))
            return
        try:
            self._service.validate_inputs(
                self._resolved_players_csv_path(),
                self._view.selected_opponent_name(),
                self._view.selected_formations()
            )
        except MatchWorkspaceValidationError as exc:
            self._view.show_error(
                str(exc)
            )
            return

        match_type = self._current_match_type()
        if match_type is None:
            return

        training_context = self._training_context_for_current_match()
        self._pending_training_context = training_context
        self._show_training_context(training_context)
        required_player_ids = None
        training_rules = None
        required_slot_classes = None
        if match_type in {MATCH_TYPE_LEAGUE, MATCH_TYPE_CUP, MATCH_TYPE_FRIENDLY}:
            training_rules = self._weekly_training_service.active_training_rules()
            if training_rules is None:
                self._view.show_error(
                    t("match.cup_training_rules_unavailable")
                )
                return
            required_player_ids = (
                training_context.required_player_ids
                if training_context is not None
                else self._weekly_training_service.required_player_ids_for_match()
            )
            required_slot_classes = (
                self._weekly_training_service.required_player_training_slot_classes(
                    getattr(training_context, "training_cycle_id", None),
                    self._roster_players,
                )
            )
        match_1_player_ids = self._match_1_player_ids_for_context(training_context)

        self._trace_runtime_integrity(
            "ANALYZE_CLICKED",
            caller="_analyze",
            reason="primary_analysis",
            match_type=match_type,
            selection_policy=(
                "friendly_rotation"
                if match_type == MATCH_TYPE_FRIENDLY
                else "competitive"
            ),
            selected_formations=self._view.selected_formations(),
            required_player_ids=tuple(sorted(required_player_ids or ())),
            required_slot_classes=required_slot_classes or {},
            match_1_player_ids=tuple(sorted(match_1_player_ids)),
            training_context=(
                {
                    "cycle_id": training_context.training_cycle_id,
                    "revision": training_context.weekly_cycle_revision,
                    "role": training_context.suggested_role,
                }
                if training_context is not None
                else {}
            ),
        )

        if hasattr(self._view, "set_training_conflict_warning"):
            self._view.set_training_conflict_warning("")

        if self._should_stop_for_existing_or_conflicting_match():
            return

        self._save_current_settings()
        self._pending_workspace_state = None
        self._view.set_processing(
            True
        )
        self._view.show_status(
            t("match.status_recalculating_recommendation")
        )

        self._thread = QThread(self)
        self._worker = MatchAnalysisWorker(
            self._service,
            self._resolved_players_csv_path(),
            self._view.selected_opponent_name(),
            self._view.selected_formations(),
            availability_mode=self._availability_mode(),
            match_type=match_type,
            required_player_ids=required_player_ids,
            training_rules=training_rules,
            required_slot_classes=required_slot_classes,
            match_1_player_ids=match_1_player_ids,
        )
        self._worker.moveToThread(
            self._thread
        )

        self._thread.started.connect(
            self._worker.run
        )
        self._worker.progress_changed.connect(
            self._view.show_status
        )
        self._worker.finished.connect(
            self._analysis_finished
        )
        self._worker.failed.connect(
            self._analysis_failed
        )
        self._worker.finished.connect(
            self._thread.quit
        )
        self._worker.failed.connect(
            self._thread.quit
        )
        self._thread.finished.connect(
            self._worker.deleteLater
        )
        self._thread.finished.connect(
            self._thread.deleteLater
        )
        self._thread.finished.connect(
            self._clear_worker_refs
        )

        self._thread.start()

    def _recalculate_workspace(self, workspace_state):
        self._queued_workspace_state = workspace_state
        self._latest_workspace_revision = workspace_state.revision
        self._trace_runtime_integrity(
            "MANUAL_PLAYER_CHANGE",
            caller="_recalculate_workspace",
            reason="workspace_modified",
            workspace_revision=getattr(workspace_state, "revision", ""),
            workspace_formation=getattr(workspace_state, "current_formation_name", ""),
        )
        if hasattr(self._view, "show_workspace_updating"):
            self._view.show_workspace_updating()
        self._workspace_recalc_timer.start()

    def _start_queued_workspace_recalculation(self):
        workspace_state = self._queued_workspace_state
        if workspace_state is None:
            return
        if self._thread is not None:
            return
        self._queued_workspace_state = None
        if self._selected_opponent_requires_manager_restore():
            self._view.show_error(t("match.saved_opponent_missing_analyze_blocked"))
            return
        try:
            self._service.validate_inputs(
                self._resolved_players_csv_path(),
                self._view.selected_opponent_name(),
                list(workspace_state.workspace_boards.keys())
            )
        except MatchWorkspaceValidationError as exc:
            self._view.show_error(
                str(exc)
            )
            return

        match_type = self._current_match_type()
        if match_type is None:
            return

        training_context = self._training_context_for_current_match()
        self._pending_training_context = training_context
        self._show_training_context(training_context)

        self._save_current_settings()
        self._pending_workspace_state = workspace_state
        self._trace_runtime_integrity(
            "ANALYSIS_REFRESH",
            caller="_start_queued_workspace_recalculation",
            reason="workspace_recalculation",
            workspace_revision=getattr(workspace_state, "revision", ""),
            workspace_boards=tuple(workspace_state.workspace_boards.keys()),
        )
        if hasattr(self._view, "set_workspace_processing"):
            self._view.set_workspace_processing(True)
        else:
            self._view.set_processing(True)
        self._view.show_status(
            t("match.status_updating_available_lineup")
        )

        self._thread = QThread(self)
        self._worker = MatchAnalysisWorker(
            self._service,
            self._resolved_players_csv_path(),
            self._view.selected_opponent_name(),
            list(workspace_state.workspace_boards.keys()),
            workspace_state=workspace_state,
            availability_mode=self._availability_mode(),
            match_type=match_type,
        )
        self._worker.moveToThread(
            self._thread
        )

        self._thread.started.connect(
            self._worker.run
        )
        self._worker.progress_changed.connect(
            self._view.show_status
        )
        self._worker.finished.connect(
            self._analysis_finished
        )
        self._worker.failed.connect(
            self._analysis_failed
        )
        self._worker.finished.connect(
            self._thread.quit
        )
        self._worker.failed.connect(
            self._thread.quit
        )
        self._thread.finished.connect(
            self._worker.deleteLater
        )
        self._thread.finished.connect(
            self._thread.deleteLater
        )
        self._thread.finished.connect(
            self._clear_worker_refs
        )

        self._thread.start()

    def _selected_opponent_requires_manager_restore(self):
        if not hasattr(self._view, "selected_opponent_identity"):
            return False
        identity = self._view.selected_opponent_identity()
        return identity.get("source") == "SAVED_MATCH_SNAPSHOT"

    def _analysis_finished(self, result):
        finished_workspace_state = self._pending_workspace_state
        self._trace_runtime_integrity(
            "ANALYSIS_RESULT_RECEIVED",
            result=result,
            caller="_analysis_finished",
            reason=(
                "workspace_recalculation"
                if finished_workspace_state is not None
                else "primary_analysis"
            ),
        )
        if (
            finished_workspace_state is not None
            and self._latest_workspace_revision is not None
            and finished_workspace_state.revision != self._latest_workspace_revision
        ):
            self._pending_workspace_state = None
            if hasattr(self._view, "set_workspace_processing"):
                self._view.set_workspace_processing(False)
            else:
                self._view.set_processing(False)
            return

        previous_result = self._current_workspace_result()

        if finished_workspace_state is not None:
            result = self._preserve_recommendation_after_manual_reevaluation(
                previous_result,
                result,
            )
            previous_result = self._current_workspace_result()
            change_analysis = self._change_analysis_service.analyze(
                previous_result,
                result,
                finished_workspace_state,
            )
            result = replace(
                result,
                change_analysis=change_analysis,
            )
            result = self._service.refresh_presentational_analysis(result)
        else:
            result = self._mark_explicit_recommendation_revision(
                previous_result,
                result,
            )

        if finished_workspace_state is not None and hasattr(
            self._view,
            "set_workspace_processing",
        ):
            self._view.set_workspace_processing(False)
        else:
            self._view.set_processing(False)
        result = self._apply_official_pre_if_available(result)
        result = self._stamp_training_context(result)
        result = self._stamp_result_owner(result)
        self._compute_and_show_plan_revision(previous_result, result)
        self._update_pre_status_and_ratings_panel()
        self._settings_repository.save_last_result(
            result
        )
        self._load_current_roster_for_inspector(show_errors=False)
        if hasattr(self._view, "set_training_conflict_warning"):
            self._view.set_training_conflict_warning(
                getattr(result, "training_conflict_warning", "")
            )
        self._view.show_results(
            result,
            workspace_state=self._pending_workspace_state,
        )
        self._trace_runtime_integrity(
            "RECOMMENDATION_RENDERED",
            result=result,
            caller="_analysis_finished",
            reason="show_results",
        )
        self._trace_runtime_integrity(
            "FORMATION_BOARD_REBUILT",
            result=result,
            caller="_analysis_finished",
            reason="show_results",
        )
        self._pending_workspace_state = None
        self._pending_training_context = None
        self._view.show_status(
            "Match analysis complete."
        )

    @staticmethod
    def _preserve_recommendation_after_manual_reevaluation(previous_result, result):
        previous_recommended = getattr(previous_result, "recommended_formation", None)
        previous_name = (
            str(getattr(previous_result, "recommendation_id", "") or "").strip()
            or getattr(previous_recommended, "formation_name", "")
        )
        formations = list(getattr(result, "formations", ()) or ())
        if previous_name and any(
            formation.formation_name == previous_name for formation in formations
        ):
            formations = [
                replace(
                    formation,
                    is_recommended=(formation.formation_name == previous_name),
                )
                for formation in formations
            ]
            result = replace(result, formations=formations)

        return replace(
            result,
            recommendation_id=previous_name,
            recommendation_revision=getattr(
                previous_result, "recommendation_revision", 0
            ),
            manual_lineup_revision=(
                getattr(previous_result, "manual_lineup_revision", 0) + 1
            ),
        )

    @staticmethod
    def _mark_explicit_recommendation_revision(previous_result, result):
        recommended = getattr(result, "recommended_formation", None)
        return replace(
            result,
            recommendation_id=getattr(recommended, "formation_name", ""),
            recommendation_revision=(
                getattr(previous_result, "recommendation_revision", 0) + 1
            ),
            manual_lineup_revision=getattr(
                previous_result, "manual_lineup_revision", 0
            ),
        )

    def _training_context_for_current_match(self):
        match_date = self._current_match_date()
        if not match_date:
            return None
        try:
            return self._weekly_training_service.match_training_context(
                match_date,
                self._roster_players,
            )
        except Exception:
            return None

    def _stamp_training_context(self, result):
        context = self._pending_training_context
        if context is None:
            return result
        try:
            from ht_coach_app.services.ht_week_context_provider import (
                get_calendar_service,
            )

            timestamp = get_calendar_service().now().isoformat(timespec="seconds")
        except Exception:
            timestamp = ""
        return replace(
            result,
            training_cycle_id=context.training_cycle_id,
            weekly_cycle_revision_used=context.weekly_cycle_revision,
            training_context_timestamp=timestamp,
            training_context_summary=self._format_training_context_summary(context),
            training_context_stale=False,
        )

    def _show_training_context(self, context, stale=False):
        if not hasattr(self._view, "set_training_context_summary"):
            return
        if context is None:
            self._view.set_training_context_summary("", stale=False)
            return
        self._view.set_training_context_summary(
            self._format_training_context_summary(context),
            stale=stale,
        )

    @staticmethod
    def _format_training_context_summary(context):
        start = context.start_date.strftime("%d/%m/%Y") if context.start_date else ""
        end = context.end_date.strftime("%d/%m/%Y") if context.end_date else ""
        role_key = {
            "first": "match.training_context_role_first",
            "second": "match.training_context_role_second",
        }.get(
            context.suggested_role,
            "match.training_context_role_unassigned",
        )
        return t(
            "match.training_context_summary",
            cycle=context.training_cycle_id,
            start=start,
            end=end,
            role=t(role_key),
            full=context.full_covered_count,
            half=context.half_covered_count,
            pending=context.pending_count,
        )

    def _handle_weekly_plan_saved_for_match_context(self):
        result = self._current_workspace_result()
        if result is None or not getattr(result, "training_cycle_id", ""):
            return
        current_revision = self._weekly_training_service.weekly_cycle_revision(
            result.training_cycle_id
        )
        if current_revision == getattr(result, "weekly_cycle_revision_used", ""):
            self._show_training_context_from_result(result)
            return
        stale_result = replace(result, training_context_stale=True)
        self._settings_repository.save_last_result(stale_result)
        self._show_training_context_from_result(stale_result)

    def _show_training_context_from_result(self, result):
        if not hasattr(self._view, "set_training_context_summary"):
            return
        summary = getattr(result, "training_context_summary", "")
        if getattr(result, "training_context_stale", False) and summary:
            summary = f"{summary}\n{t('match.training_context_stale')}"
        self._view.set_training_context_summary(
            summary,
            stale=getattr(result, "training_context_stale", False),
        )

    def _compute_and_show_plan_revision(self, previous_result, new_result):
        """Alpha 0.6.6, Parts 2-4: compares the previously saved lineup
        against the new recommendation, classifies how meaningful the
        change is, and builds a contextual explanation -- never
        touches the optimizer, purely a post-processing/presentation
        step. Silently skipped if the view doesn't support displaying
        it yet."""
        if not hasattr(self._view, "show_plan_revision"):
            return
        try:
            from engine.lineup_memory import (
                classify_stability,
                compare_lineups,
                explain_revision,
            )

            previous_formation = (
                previous_result.recommended_formation if previous_result else None
            )
            new_formation = new_result.recommended_formation
            if new_formation is None:
                return
            revision = compare_lineups(previous_formation, new_formation)
            classification = classify_stability(revision)
            explanation = explain_revision(revision, classification)
            self._view.show_plan_revision(revision, classification, explanation)
        except Exception:
            # Never let a presentation-layer computation break the
            # underlying analysis result from being shown.
            pass

    def _update_pre_status_and_ratings_panel(self, snapshot_id_override=None):
        """Alpha 0.6.7 HF-03, Part 3: the compact "Calificaciones"
        card must render *only* the currently open workspace's own
        record -- this used to read `latest_snapshot_with_official_
        data()`, the same database-wide "most recent" lookup that
        caused the PRE-leakage bug fixed in `_latest_official_pre_
        ratings()`. Both now resolve through the exact same
        `_current_workspace_record()`, so the status label, the
        ratings card, and the actually-applied PRE override can never
        disagree with each other or with which match is truly open."""
        if not hasattr(self._view, "set_pre_status"):
            return
        record = self._current_workspace_record(snapshot_id_override=snapshot_id_override)
        has_pre = record is not None and record.official_pre is not None
        self._view.set_pre_status(has_pre)

        if not hasattr(self._view, "show_compact_official_ratings"):
            return
        if not has_pre:
            self._view.show_compact_official_ratings(None)
            if hasattr(self._view, "set_tactic_mismatch"):
                self._view.set_tactic_mismatch("", "")
            return

        pre = record.official_pre
        ratings = pre.ratings
        pre_tactic_raw = pre.canonical_tactic or getattr(pre.tactic, "label", "")
        self._view.show_compact_official_ratings({
            "left_defense": getattr(ratings, "left_defense", None),
            "central_defense": getattr(ratings, "central_defense", None),
            "right_defense": getattr(ratings, "right_defense", None),
            "midfield": getattr(ratings, "midfield", None),
            "left_attack": getattr(ratings, "left_attack", None),
            "central_attack": getattr(ratings, "central_attack", None),
            "right_attack": getattr(ratings, "right_attack", None),
            "tactic": pre_tactic_raw,
            "tactic_level": getattr(pre.tactic, "level", None),
            "formation": getattr(pre.formation, "label", ""),
            "team_attitude": pre.team_attitude,
        })

        if hasattr(self._view, "set_tactic_mismatch"):
            self._update_tactic_mismatch_indicator(pre_tactic_raw)

    def _update_tactic_mismatch_indicator(self, pre_tactic_raw):
        """Alpha 0.6.7 HF-03, Parts 9-10: Official PRE is evidence, not
        an editor -- it must never silently overwrite the current
        plan's tactic. When they genuinely differ, show the mismatch
        as information only (the brief's own fallback, since an
        automatic "apply PRE to plan" action isn't safely supported by
        the current architecture without touching the protected
        optimizer). This is also the diagnostic tool for the reported
        AIM-workspace-showing-AOW-PRE bug -- if the *record IDs*
        differ, Part 3's isolation fix is what actually matters; this
        indicator only ever compares two tactics *for the same,
        correctly-resolved record*."""
        from ht_coach_app.core.tactic_formatting import format_tactic

        current_tactic_raw = (
            self._view.tactic() if hasattr(self._view, "tactic") else ""
        )
        if not current_tactic_raw or not pre_tactic_raw:
            self._view.set_tactic_mismatch("", "")
            return
        if current_tactic_raw == pre_tactic_raw:
            self._view.set_tactic_mismatch("", "")
            return
        self._view.set_tactic_mismatch(
            format_tactic(current_tactic_raw), format_tactic(pre_tactic_raw)
        )

    def _updated_record_with_metadata(self, record, metadata):
        from engine.history.models import MatchContext, OpponentReference

        csv_path = (
            self._view.players_csv_path()
            if hasattr(self._view, "players_csv_path")
            else ""
        )
        provenance = record.provenance
        if csv_path:
            provenance = replace(
                provenance,
                roster_source=csv_path,
            )
        updated_context = MatchContext(
            official_match_id=record.match_context.official_match_id,
            match_date=metadata.scheduled_date,
            kickoff_time=record.match_context.kickoff_time,
            season=record.match_context.season,
            round=record.match_context.round,
            competition_type=metadata.competition_type,
            match_type=record.match_context.match_type,
            home_away=metadata.venue_role,
            team_type=record.match_context.team_type,
            opponent=replace(
                record.match_context.opponent
                if record.match_context.opponent is not None
                else OpponentReference(),
                opponent_id=metadata.opponent_id,
                opponent_name=metadata.opponent_name,
            ),
            venue=record.match_context.venue,
            snapshot_stage=record.match_context.snapshot_stage,
        )
        return record.with_updates(
            match_context=updated_context,
            training_cycle_id=metadata.training_cycle_id,
            ht_season_number=metadata.season_number,
            ht_season_week=metadata.competitive_week,
            provenance=provenance,
        )

    def _save_metadata_to_canonical_record(self, snapshot_id, metadata):
        repository = self._history_repository()
        if repository is None:
            raise RuntimeError("history repository unavailable")
        record = repository.get(snapshot_id)
        if record is None:
            raise RuntimeError(f"match record not found: {snapshot_id}")
        return repository.save(self._updated_record_with_metadata(record, metadata))

    def _persist_metadata_corrections_to_canonical_record(self, snapshot_id):
        """Alpha 0.6.7 HF-02, Part 4: while editing a saved match,
        correcting date/competition type/venue role in the setup form
        must persist back onto the *same* canonical record -- these
        fields were previously only ever read when restoring the
        workspace, never written back on save."""
        repository = self._history_repository()
        if repository is None:
            return
        record = repository.get(snapshot_id)
        if record is None:
            return

        metadata = self._current_workspace_metadata(fallback_record=record)

        try:
            self._save_metadata_to_canonical_record(snapshot_id, metadata)
            if hasattr(self._view, "clear_metadata_dirty"):
                self._view.clear_metadata_dirty()
            if (
                self._app_events is not None
                and hasattr(self._app_events, "match_records_changed")
            ):
                self._app_events.match_records_changed.emit(snapshot_id)
        except Exception:
            # Never let a best-effort metadata correction break the
            # actual save flow it's attached to.
            pass

    def _save_metadata_only_to_canonical_record(self, snapshot_id):
        repository = self._history_repository()
        if repository is None:
            self._view.show_error(t("match.save_workspace_error", reason="history repository unavailable"))
            return False
        record = repository.get(snapshot_id)
        if record is None:
            self._view.show_error(t("match.save_workspace_error", reason="match record not found"))
            return False

        metadata = self._current_workspace_metadata(fallback_record=record)
        if not self._validate_metadata_for_save(metadata):
            return False
        if (
            (record.official_pre or record.official_post or record.official_match_post)
            and self._metadata_differs_from_record(record)
            and hasattr(self._view, "confirm_metadata_evidence_save")
            and not self._view.confirm_metadata_evidence_save()
        ):
            return False

        try:
            saved_record = self._save_metadata_to_canonical_record(
                snapshot_id,
                metadata,
            )
            self._assert_saved_metadata_matches_workspace(metadata, saved_record)
        except Exception as exc:
            self._save_failure_result("save_metadata", exc)
            return False

        if hasattr(self._view, "clear_metadata_dirty"):
            self._view.clear_metadata_dirty()
        self._update_metadata_evidence_warning()
        self._update_season_preview(saved_record.match_context.match_date)
        self._update_pre_status_and_ratings_panel(snapshot_id_override=snapshot_id)
        if hasattr(self._view, "show_status"):
            self._view.show_status(t("match.metadata_saved"))
        self._record_app_event("save_metadata", snapshot_id)
        if (
            self._app_events is not None
            and hasattr(self._app_events, "match_records_changed")
        ):
            self._app_events.match_records_changed.emit(snapshot_id)
        return True

    def _save_lineup_to_canonical_record(self, snapshot_id, result):
        repository = self._history_repository()
        if repository is None:
            raise RuntimeError("history repository unavailable")
        if not snapshot_id:
            raise RuntimeError("match record id is required")
        record = repository.get(snapshot_id)
        if record is None:
            raise RuntimeError(f"match record not found: {snapshot_id}")
        active_formation = self._active_workspace_formation(result)
        if active_formation is None:
            raise RuntimeError("recommended formation is required")

        from engine.history.lineup_snapshot import build_historical_lineup, build_tactical_setup

        tactical_setup = build_tactical_setup(active_formation)
        selected_tactic = (
            self._view.tactic() if hasattr(self._view, "tactic") else ""
        )
        if selected_tactic:
            from dataclasses import replace as _dc_replace

            tactical_setup = _dc_replace(
                tactical_setup, selected_tactic=selected_tactic
            )
        selected_attitude = (
            self._view.team_attitude() if hasattr(self._view, "team_attitude") else ""
        )
        if selected_attitude:
            from dataclasses import replace as _dc_replace

            tactical_setup = _dc_replace(
                tactical_setup, team_attitude=selected_attitude
            )
        provenance = record.provenance
        historical_reconstruction = (
            self._workspace_mode == WORKSPACE_MODE_EDIT_SAVED_MATCH
            and not record.lineup
            and float(getattr(active_formation, "win_probability", 0.0) or 0.0) == 0.0
            and float(getattr(active_formation, "draw_probability", 0.0) or 0.0) == 0.0
            and float(getattr(active_formation, "loss_probability", 0.0) or 0.0) == 0.0
        )
        if historical_reconstruction:
            provenance = replace(
                provenance,
                lineup_source="MANUAL_HISTORICAL_RECONSTRUCTION",
            )
        updated = record.with_updates(
            lineup=build_historical_lineup(active_formation),
            tactical_setup=tactical_setup,
            provenance=provenance,
        )
        return repository.save(updated)

    def _persist_lineup_to_canonical_record(self, snapshot_id, result):
        """Alpha 0.6.7, Part 8's remaining piece: saves the recommended
        formation's own lineup/tactic onto the canonical record so a
        later Edit has something real to restore -- never a full
        board-state duplication, just the summary
        (player/position/order) `HistoricalLineupEntry` already models.

        Alpha 0.6.7 HF-03, Parts 7-8: the user's own tactic/team
        attitude selection (from the canonical selectors, when
        genuinely different from the optimizer's own recommendation)
        overrides what gets saved -- never silently reverting to the
        recommendation the user explicitly changed away from.
        """
        try:
            self._save_lineup_to_canonical_record(snapshot_id, result)
        except Exception:
            # Never let a best-effort summary save break the actual
            # save-as-first/second-match flow it's attached to.
            pass

    def _apply_official_pre_if_available(self, result, snapshot_id_override=None):
        official_pre_ratings = self._latest_official_pre_ratings(
            snapshot_id_override=snapshot_id_override
        )
        if official_pre_ratings is None:
            return result
        try:
            return self._service.apply_official_pre_override(
                result, official_pre_ratings
            )
        except Exception:
            # Never let a source-selection issue break the underlying
            # analysis -- fall back to whatever was already computed.
            return result

    def _latest_official_pre_ratings(self, snapshot_id_override=None):
        """Alpha 0.6.7 HF-03, Part 1-3: the root cause of the reported
        PRE-leakage bug. This used to call
        `service.latest_snapshot_with_official_data()` -- "whatever
        record anywhere in the whole database was most recently
        touched" -- with no regard for which match is actually open in
        this workspace. A brand-new, unrelated match would silently
        inherit another match's Official PRE the moment *any* analysis
        ran, since that other record simply happened to be the most
        recently updated one globally.

        Fixed to resolve strictly against the currently open workspace
        context: the record being edited (`_editing_snapshot_id`) when
        one is set, otherwise the record matching the current
        opponent + date (the same identity `_should_stop_for_existing_
        or_conflicting_match` and `_linked_canonical_record_id`
        already use) -- never a database-wide "most recent" fallback.
        """
        record = self._current_workspace_record(snapshot_id_override=snapshot_id_override)
        if record is None or record.official_pre is None:
            return None
        return record.official_pre.ratings

    def _record_app_event(self, action, match_record_id="", outcome="ok", detail=""):
        """Alpha 0.6.7 HF-03, Part 15: structured logging around Match
        actions -- record IDs and outcomes, never raw personal data."""
        try:
            from ht_coach_app.diagnostics.event_buffer import record_event

            record_event(action, match_record_id, outcome, detail)
        except Exception:
            pass

    def _update_app_context(self, **changes):
        """Alpha 0.6.7 HF-03, Part 13: keeps the global diagnostic
        context current, so a crash log written moments later reflects
        what was actually happening."""
        try:
            from ht_coach_app.diagnostics.app_context import update_context

            update_context(active_page="match", **changes)
        except Exception:
            pass

    def _save_recovery_snapshot_if_dirty(self):
        """Alpha 0.6.7 HF-03, Part 16: before a high-risk action
        (switching records, importing evidence, rerunning the
        optimizer, replacing a saved formation), save a lightweight
        recovery snapshot -- only the latest one per record is kept,
        and it's never auto-restored without the person's own
        confirmation."""
        if not self._editing_snapshot_id:
            return
        try:
            from ht_coach_app.diagnostics.recovery_snapshot import RecoverySnapshotStore

            store = RecoverySnapshotStore()
            store.save(
                self._editing_snapshot_id,
                tactic=self._view.tactic() if hasattr(self._view, "tactic") else "",
                team_attitude=(
                    self._view.team_attitude() if hasattr(self._view, "team_attitude") else ""
                ),
            )
        except Exception:
            pass

    def _discard_recovery_snapshot(self, match_record_id):
        """Once a formation is genuinely saved, its recovery snapshot
        is no longer needed."""
        if not match_record_id:
            return
        try:
            from ht_coach_app.diagnostics.recovery_snapshot import RecoverySnapshotStore

            RecoverySnapshotStore().discard(match_record_id)
        except Exception:
            pass

    def _current_workspace_record(self, snapshot_id_override=None):
        """Alpha 0.6.7 HF-03: the one, single source of truth for
        "which canonical Match Record does this workspace currently
        represent" -- used everywhere a workspace action needs to read
        or write record-scoped evidence, so every consumer resolves
        the *same* record the same way."""
        repository = self._history_repository()
        if repository is None:
            return None

        if snapshot_id_override:
            return repository.get(snapshot_id_override)

        if self._workspace_mode == WORKSPACE_MODE_EDIT_SAVED_MATCH:
            if not self._active_match_record_id:
                return None
            return repository.get(self._active_match_record_id)

        if self._editing_snapshot_id:
            return repository.get(self._editing_snapshot_id)

        last_result = self._current_workspace_result(include_legacy=True)
        metadata = self._current_workspace_metadata(result=last_result)
        opponent_name = metadata.opponent_name
        if not opponent_name:
            # The opponent selector may be empty in some flows (e.g. a
            # result was already shown but the combo wasn't
            # separately re-populated) -- the currently displayed
            # analysis result's own opponent is just as valid a source
            # for "which match is this workspace showing."
            opponent_name = getattr(last_result, "opponent_name", "") if last_result else ""
        if not opponent_name:
            return None
        match_date = metadata.scheduled_date
        competition_type = metadata.competition_type
        if not competition_type:
            return None

        from engine.history.match_lookup import find_existing_or_conflicting_record

        result = find_existing_or_conflicting_record(
            repository, opponent_name, competition_type, match_date=match_date,
        )
        if result.kind == "exact":
            return result.record
        return None

    def _require_active_saved_match_record_id(self, action=""):
        if self._workspace_mode != WORKSPACE_MODE_EDIT_SAVED_MATCH:
            return ""
        if not self._active_match_record_id:
            message = t("match.saved_edit_integrity_error")
            self._record_app_event(
                action or "saved_match_integrity",
                "",
                "error",
                "missing_active_match_record_id",
            )
            raise RuntimeError(message)
        if (
            self._editing_snapshot_id
            and self._editing_snapshot_id != self._active_match_record_id
        ):
            message = t("match.saved_edit_integrity_error")
            self._record_app_event(
                action or "saved_match_integrity",
                self._active_match_record_id,
                "error",
                f"editing_id_mismatch:{self._editing_snapshot_id}",
            )
            raise RuntimeError(message)
        repository = self._history_repository()
        if repository is None or repository.get(self._active_match_record_id) is None:
            message = t("match.saved_edit_integrity_error")
            self._record_app_event(
                action or "saved_match_integrity",
                self._active_match_record_id,
                "error",
                "active_match_record_not_found",
            )
            raise RuntimeError(message)
        return self._active_match_record_id

    def _match_intelligence_service(self):
        if self._official_rating_service is None:
            return None
        if getattr(self, "_cached_match_intelligence_service", None) is None:
            from ht_coach_app.services.match_intelligence_service import (
                MatchIntelligenceAppService,
            )

            self._cached_match_intelligence_service = MatchIntelligenceAppService(
                repository=getattr(self._official_rating_service, "_repository", None),
                import_service=self._official_rating_service,
            )
        return self._cached_match_intelligence_service

    def _analysis_failed(self, message):
        if self._pending_workspace_state is not None and hasattr(
            self._view,
            "set_workspace_processing",
        ):
            self._view.set_workspace_processing(False)
        else:
            self._view.set_processing(False)
        failed_state = self._pending_workspace_state
        self._pending_workspace_state = None
        if failed_state is not None:
            if hasattr(self._view, "show_workspace_analysis_failed"):
                self._view.show_workspace_analysis_failed(message)
            return
        self._view.show_error(
            message
        )

    def _copy_summary(self):
        result = self._current_workspace_result(include_legacy=True)

        if result is None:
            self._view.show_error(
                "Run an analysis before copying the summary."
            )
            return

        self._view.copy_text_to_clipboard(
            format_match_summary(result)
        )
        self._view.show_status(
            "Match summary copied."
        )

    def _copy_lineup(self):
        result = self._current_workspace_result(include_legacy=True)

        if result is None:
            self._view.show_error(
                "Run an analysis before copying the lineup."
            )
            return

        self._view.copy_text_to_clipboard(
            format_recommended_lineup(result)
        )
        self._view.show_status(
            "Recommended lineup copied."
        )

    def _copy_decision_lab(self):
        result = self._current_workspace_result(include_legacy=True)

        if result is None:
            self._view.show_error(
                "Run an analysis before copying Decision Lab."
            )
            return

        self._view.copy_text_to_clipboard(
            format_decision_lab(result)
        )
        self._view.show_status(
            "Decision Lab copied."
        )

    def _clear_worker_refs(self):
        self._thread = None
        self._worker = None
        if self._queued_workspace_state is not None:
            self._workspace_recalc_timer.start()

    def _save_current_settings(self):
        settings = self._settings_repository.load()
        path = self._view.players_csv_path()
        recent = [path] + [
            item for item in settings.recent_players_csv_paths
            if item != path
        ] if path else list(settings.recent_players_csv_paths)
        recent = recent[: self._settings_repository.MAX_RECENT_PLAYERS_CSV]
        self._settings_repository.save(
            MatchWorkspaceSettings(
                players_csv_path=path,
                recent_players_csv_paths=recent,
                opponent_name=self._view.selected_opponent_name(),
                selected_formations=self._view.selected_formations(),
                squad_availability_mode=self._availability_mode(),
                match_section_states=(
                    self._view.match_section_states()
                    if hasattr(self._view, "match_section_states")
                    else {}
                ),
            )
        )
        if hasattr(self._view, "set_recent_csv_paths"):
            self._view.set_recent_csv_paths(recent)

    def _load_current_roster_for_inspector(self, show_errors, update_count=True):
        try:
            players = self._service.load_players(
                self._resolved_players_csv_path(),
                availability_mode=self._availability_mode(),
            )
        except Exception as exc:
            self._roster_players = []
            self._set_view_roster_players([])
            if update_count and hasattr(self._view, "set_players_loaded_count"):
                self._view.set_players_loaded_count(0)
            if show_errors:
                self._view.show_error(str(exc))
            return

        self._roster_players = players
        self._set_view_roster_players(players)
        if update_count and hasattr(self._view, "set_players_loaded_count"):
            self._view.set_players_loaded_count(len(players))

    def _set_view_roster_players(self, players):
        if hasattr(self._view, "set_roster_players"):
            self._view.set_roster_players(players)

    def _availability_mode(self):
        if hasattr(self._view, "availability_mode"):
            return self._view.availability_mode()

        return CURRENT_AVAILABLE

    def _resolved_players_csv_path(self):
        return str(application_paths().resolve_user_path(self._view.players_csv_path()))

    def _current_match_date(self):
        if hasattr(self._view, "match_date") and self._view.match_date():
            return self._view.match_date()
        return None

    def _current_match_type(self, show_error=True):
        match_type = self._view.match_type() if hasattr(self._view, "match_type") else None
        if match_type in {MATCH_TYPE_LEAGUE, MATCH_TYPE_CUP, MATCH_TYPE_FRIENDLY}:
            return match_type
        if show_error and hasattr(self._view, "show_error"):
            self._view.show_error(t("match.invalid_match_type"))
        return None

    def _current_competition_type(self, fallback="", show_error=True):
        match_type = self._current_match_type(show_error=show_error)
        if match_type == MATCH_TYPE_LEAGUE:
            return "league"
        if match_type == MATCH_TYPE_CUP:
            return "cup"
        if match_type == MATCH_TYPE_FRIENDLY:
            return "friendly"
        value = getattr(fallback, "value", fallback)
        return str(value or "").lower()

    def _competition_type_for_result(self, result):
        match_type = getattr(result, "match_type", "") or self._current_match_type(
            show_error=False
        )
        if match_type == MATCH_TYPE_CUP:
            return "cup"
        if match_type == MATCH_TYPE_LEAGUE:
            return "league"
        if match_type == MATCH_TYPE_FRIENDLY:
            return "friendly"
        return self._current_competition_type(show_error=False) or "unknown"

    def _match_1_player_ids_for_context(self, training_context):
        cycle_id = getattr(training_context, "training_cycle_id", "") if training_context else ""
        if not cycle_id:
            return frozenset()
        try:
            return self._weekly_training_service.first_match_player_ids_for_cycle(
                cycle_id
            )
        except Exception:
            return frozenset()

    def _update_season_preview(self, match_date_text=None):
        """Alpha 0.6.7 HF-02, Part 14: after picking a date, preview
        both Temporada HT / Semana competitiva (from the Season
        Calendar, if configured -- never guessed otherwise) and the
        training cycle it falls into. Never blocks match creation
        either way -- this is read-only, informational preview text."""
        if not hasattr(self._view, "set_season_preview"):
            return
        match_date_text = match_date_text or self._current_match_date()
        if not match_date_text:
            self._view.set_season_preview("")
            return

        from ht_coach_app.services.dual_week_formatting import format_dual_week_summary
        from ht_coach_app.core.localization import t

        training_cycle_id = self._training_cycle_id_for_match_date(match_date_text)
        if self._season_calendar_repository is None or not self._season_calendar_repository.load().is_configured:
            self._view.set_season_preview(
                t("match.season_preview.not_configured") + "\n"
                + t("dual_week.training_cycle_label", cycle_id=f"ht-week-{training_cycle_id}")
            )
            return

        season_week = self._resolve_season_week(match_date_text)
        self._view.set_season_preview(
            format_dual_week_summary(season_week, training_cycle_id)
        )

    def _resolve_season_week(self, match_date_text):
        from engine.calendar import HTSeasonWeek

        if self._season_calendar_repository is None:
            return HTSeasonWeek()
        try:
            from engine.calendar.season_calendar import resolve_season_context

            config = self._season_calendar_repository.load()
            result = resolve_season_context(match_date_text, config)
            return result.season_week
        except Exception:
            return HTSeasonWeek()

    def _training_cycle_id_for_match_date(self, match_date_text):
        try:
            return self._weekly_training_service.cycle_id_for_match_date(match_date_text)
        except Exception:
            return self._resolve_training_cycle_id(match_date_text)

    @staticmethod
    def _resolve_training_cycle_id(match_date_text):
        from datetime import date as _date, datetime as _datetime

        from engine.calendar.service import HTCalendarService

        try:
            target = _date.fromisoformat(match_date_text[:10])
        except ValueError:
            return ""
        service = HTCalendarService()
        return service.training_week_id(_datetime(target.year, target.month, target.day))

    def _target_week_range(self):
        """Alpha 0.6.7 HF-02, Part 3: names the actual training cycle
        that the selected match date resolves to -- matching exactly
        what `record_first_match`/`record_second_match` now use for
        identity, so the confirmation dialog and the record it
        describes can never disagree."""
        from datetime import timedelta as _timedelta

        match_date_text = self._current_match_date()
        if not match_date_text:
            return "", ""
        week_start = self._weekly_training_service.week_start_date_for(match_date_text)
        if week_start is None:
            return "", ""
        week_end = week_start + _timedelta(days=6)
        return week_start.strftime("%d/%m/%Y"), week_end.strftime("%d/%m/%Y")

    def _weekly_save_success_message(self, slot):
        week_start, week_end = self._target_week_range()
        if week_start and week_end:
            return t(
                "match.save_as_weekly_success_with_range",
                slot=slot,
                week_start=week_start,
                week_end=week_end,
            )
        if slot == 1:
            return t("match.save_as_first_match_success")
        return t("match.save_as_second_match_success")

    def _save_as_first_match(self):
        result = self._current_or_saved_workspace_result(include_legacy=True)
        if result is None or not getattr(result, "formations", None):
            self._view.show_error(
                t("match.save_as_first_match_no_result")
            )
            return
        result = self._result_with_active_workspace_lineup(result)
        self._trace_runtime_integrity(
            "SAVE_FORMATION_CLICKED",
            result=result,
            caller="_save_as_first_match",
            reason="save_as_first_match",
        )
        self._trace_runtime_integrity(
            "SAVE_PARTIDO_1_CLICKED",
            result=result,
            caller="_save_as_first_match",
            reason="save_as_first_match",
        )
        match_date = self._current_match_date()
        if not match_date:
            self._view.show_error(t("match.save_as_weekly_missing_match_date"))
            return
        if not self._confirm_match_type_for_save(result):
            return
        metadata = self._current_workspace_metadata(result=result)
        if not self._validate_metadata_for_save(metadata):
            return

        board = self._capture_visible_lineup_board(result)
        if not self._has_usable_lineup(board, result):
            self._view.show_error(t("match.save_disabled_no_lineup"))
            return
        canonical_save = self._try_save_active_match_workspace(
            result,
            "save_as_first_match_canonical",
            emit_events=True,
        )
        if not canonical_save.success:
            return
        try:
            state = self._weekly_training_service.record_first_match(
                board,
                opponent_name=metadata.opponent_name,
                roster_players=self._roster_players,
                match_date=metadata.scheduled_date,
                linked_match_record_id=canonical_save.match_record_id,
                competition_type=self._weekly_competition_type_for_save(result),
            )
            self._assert_visible_board_matches_weekly_record(
                board,
                state,
                canonical_save.match_record_id,
            )
            self._trace_runtime_integrity(
                "WEEKLY_MATCH_SAVED",
                result=result,
                caller="_save_as_first_match",
                reason="record_first_match",
                saved_weekly_formation=getattr(board, "formation_name", ""),
                saved_match_record_id=canonical_save.match_record_id,
            )
        except ValueError as exc:
            if str(exc) == "duplicate_match_id":
                self._replace_first_match_after_confirmation(
                    board,
                    result,
                    canonical_save.match_record_id,
                )
                return
            self._view.show_error(
                t(
                    "match.save_as_first_match_error",
                    reason=f"ValueError: {exc}",
                )
            )
            return
        except Exception as exc:
            self._view.show_error(
                t(
                    "match.save_as_first_match_error",
                    reason=f"{type(exc).__name__}: {exc}",
                )
            )
            return

        self._view.show_status(
            self._weekly_save_success_message(1)
        )
        if self._app_events is not None:
            self._app_events.weekly_plan_saved.emit()

    def _confirm_match_type_for_save(self, result):
        """Warn if the analysis about to be saved (the last one that
        finished, which may not be the one currently showing on screen)
        was run in a different mode than the slot being saved into.
        Saving a League-mode analysis as the second (Cup) match, or vice
        versa, is very easy to do by mistake — e.g. re-running a League
        check right before saving silently swaps out the Cup-aware
        lineup for a plain one, with no error to flag it."""
        current_type = self._current_match_type()
        if current_type is None:
            return False
        actual_type = getattr(result, "match_type", None)
        if actual_type == current_type:
            return True
        if hasattr(self._view, "set_analysis_stale"):
            self._view.set_analysis_stale(
                True,
                t("match.analysis_stale_match_type"),
            )
        else:
            self._view.show_error(t("match.analysis_stale_match_type"))
        return False

    def _weekly_competition_type_for_save(self, result):
        match_type = getattr(result, "match_type", "")
        if match_type == MATCH_TYPE_LEAGUE:
            return "league"
        if match_type == MATCH_TYPE_CUP:
            return "cup"
        if match_type == MATCH_TYPE_FRIENDLY:
            return "friendly"
        return self._current_competition_type(show_error=False) or "unknown"

    def _replace_first_match_after_confirmation(self, board, result, linked_match_record_id=""):
        if not hasattr(self._view, "confirm_replace_first_match"):
            self._view.show_error(
                t(
                    "match.save_as_first_match_error",
                    reason="ValueError: duplicate_match_id",
                )
            )
            return
        week_start, week_end = self._target_week_range()
        if not self._view.confirm_replace_first_match(week_start, week_end):
            return
        match_date = self._current_match_date()
        if not match_date:
            self._view.show_error(t("match.save_as_weekly_missing_match_date"))
            return
        result = self._result_with_active_workspace_lineup(result)
        board = self._capture_visible_lineup_board(result) or board
        if not self._has_usable_lineup(board, result):
            self._view.show_error(t("match.save_disabled_no_lineup"))
            return
        metadata = self._current_workspace_metadata(result=result)
        if not self._validate_metadata_for_save(metadata):
            return
        try:
            state = self._weekly_training_service.replace_first_match(
                board,
                opponent_name=metadata.opponent_name,
                roster_players=self._roster_players,
                match_date=metadata.scheduled_date,
                linked_match_record_id=linked_match_record_id or self._linked_canonical_record_id(result),
                competition_type=self._weekly_competition_type_for_save(result),
            )
            self._assert_visible_board_matches_weekly_record(
                board,
                state,
                linked_match_record_id,
            )
        except Exception as exc:
            self._view.show_error(
                t(
                    "match.save_as_first_match_error",
                    reason=f"{type(exc).__name__}: {exc}",
                )
            )
            return
        self._view.show_status(
            self._weekly_save_success_message(1)
        )
        if self._app_events is not None:
            self._app_events.weekly_plan_saved.emit()

    def _save_formation(self):
        """Alpha 0.6.7 HF-03, Part 5: the main save action for
        historical matches, tactical experiments, and saved analyses
        not linked to training -- persists straight onto the
        canonical Match Record, with no Weekly Planner slot required
        and never creating/replacing Match 1/2. Uses the exact same
        record-resolution logic as everything else in this workspace
        (`_current_workspace_record()`), so "Guardar formación" always
        saves onto the same record the rest of the workspace is
        already scoped to -- creating a fresh provisional record only
        when genuinely none exists yet for this opponent+date+type."""
        if self._workspace_mode == WORKSPACE_MODE_EDIT_SAVED_MATCH:
            try:
                self._require_active_saved_match_record_id("save_formation")
            except RuntimeError as exc:
                self._view.show_error(str(exc))
                return
        result = self._current_workspace_result(include_legacy=True)
        metadata_dirty = (
            self._view.is_metadata_dirty()
            if hasattr(self._view, "is_metadata_dirty")
            else False
        )
        board = getattr(self._view, "_formation_board_widget", None)
        board_dirty = bool(board is not None and board.is_dirty())
        if (
            self._workspace_mode == WORKSPACE_MODE_EDIT_SAVED_MATCH
            and self._editing_snapshot_id
            and metadata_dirty
            and (result is None or not getattr(result, "formations", None) or not board_dirty)
        ):
            self._save_metadata_only_to_canonical_record(self._editing_snapshot_id)
            return
        if result is None or not getattr(result, "formations", None):
            if self._editing_snapshot_id:
                self._save_metadata_only_to_canonical_record(self._editing_snapshot_id)
                return
            self._view.show_error(
                t("match.save_as_first_match_no_result")
            )
            return
        if not self._confirm_match_type_for_save(result):
            return

        result = self._result_with_active_workspace_lineup(result)
        self._trace_runtime_integrity(
            "SAVE_FORMATION_CLICKED",
            result=result,
            caller="_save_formation",
            reason="save_formation",
        )
        saved = self._try_save_active_match_workspace(
            result,
            "save_formation",
            emit_events=True,
            refresh_weekly_link=True,
        )
        if not saved.success:
            return

        if hasattr(self._view, "show_status"):
            self._view.show_status(t("match.formation_saved"))
        self._update_metadata_evidence_warning()

    def _refresh_linked_weekly_lineup(self, snapshot_id, result):
        if not snapshot_id:
            return
        try:
            result = self._result_with_active_workspace_lineup(result)
            board = self._capture_visible_lineup_board(result)
            if board is None:
                return
            metadata = self._current_workspace_metadata(result=result)
            state = self._weekly_training_service.replace_linked_match_lineup(
                snapshot_id,
                board,
                opponent_name=metadata.opponent_name,
                roster_players=self._roster_players,
                match_date=metadata.scheduled_date,
                competition_type=self._weekly_competition_type_for_save(result),
            )
            self._assert_visible_board_matches_weekly_record(
                board,
                state,
                snapshot_id,
            )
            self._trace_runtime_integrity(
                "WEEKLY_MATCH_SAVED",
                result=result,
                caller="_refresh_linked_weekly_lineup",
                reason="replace_linked_match_lineup",
                saved_weekly_formation=getattr(board, "formation_name", ""),
                saved_match_record_id=snapshot_id,
            )
            if (
                self._app_events is not None
                and any(
                    record.linked_match_record_id == snapshot_id
                    for record in getattr(state, "match_records", ())
                )
            ):
                self._app_events.weekly_plan_saved.emit()
        except Exception:
            pass

    def _save_as_second_match(self):
        result = self._current_or_saved_workspace_result(include_legacy=True)
        if result is None or not getattr(result, "formations", None):
            self._view.show_error(
                t("match.save_as_first_match_no_result")
            )
            return
        result = self._result_with_active_workspace_lineup(result)
        self._trace_runtime_integrity(
            "SAVE_FORMATION_CLICKED",
            result=result,
            caller="_save_as_second_match",
            reason="save_as_second_match",
        )
        self._trace_runtime_integrity(
            "SAVE_PARTIDO_2_CLICKED",
            result=result,
            caller="_save_as_second_match",
            reason="save_as_second_match",
        )
        match_date = self._current_match_date()
        if not match_date:
            self._view.show_error(t("match.save_as_weekly_missing_match_date"))
            return
        if not self._confirm_match_type_for_save(result):
            return
        metadata = self._current_workspace_metadata(result=result)
        if not self._validate_metadata_for_save(metadata):
            return

        board = self._capture_visible_lineup_board(result)
        if not self._has_usable_lineup(board, result):
            self._view.show_error(t("match.save_disabled_no_lineup"))
            return
        canonical_save = self._try_save_active_match_workspace(
            result,
            "save_as_second_match_canonical",
            emit_events=True,
        )
        if not canonical_save.success:
            return
        try:
            state = self._weekly_training_service.record_second_match(
                board,
                opponent_name=metadata.opponent_name,
                roster_players=self._roster_players,
                match_date=metadata.scheduled_date,
                linked_match_record_id=canonical_save.match_record_id,
                competition_type=self._weekly_competition_type_for_save(result),
            )
            self._assert_visible_board_matches_weekly_record(
                board,
                state,
                canonical_save.match_record_id,
            )
            self._trace_runtime_integrity(
                "WEEKLY_MATCH_SAVED",
                result=result,
                caller="_save_as_second_match",
                reason="record_second_match",
                saved_weekly_formation=getattr(board, "formation_name", ""),
                saved_match_record_id=canonical_save.match_record_id,
            )
        except ValueError as exc:
            if str(exc) == "duplicate_match_id":
                self._replace_second_match_after_confirmation(
                    board,
                    result,
                    canonical_save.match_record_id,
                )
                return
            self._view.show_error(
                t(
                    "match.save_as_first_match_error",
                    reason=f"ValueError: {exc}",
                )
            )
            return
        except Exception as exc:
            self._view.show_error(
                t(
                    "match.save_as_first_match_error",
                    reason=f"{type(exc).__name__}: {exc}",
                )
            )
            return

        self._view.show_status(
            self._weekly_save_success_message(2)
        )
        if self._app_events is not None:
            self._app_events.weekly_plan_saved.emit()

    def _replace_second_match_after_confirmation(self, board, result, linked_match_record_id=""):
        if not hasattr(self._view, "confirm_replace_second_match"):
            self._view.show_error(
                t(
                    "match.save_as_first_match_error",
                    reason="ValueError: duplicate_match_id",
                )
            )
            return
        week_start, week_end = self._target_week_range()
        if not self._view.confirm_replace_second_match(week_start, week_end):
            return
        match_date = self._current_match_date()
        if not match_date:
            self._view.show_error(t("match.save_as_weekly_missing_match_date"))
            return
        result = self._result_with_active_workspace_lineup(result)
        board = self._capture_visible_lineup_board(result) or board
        if not self._has_usable_lineup(board, result):
            self._view.show_error(t("match.save_disabled_no_lineup"))
            return
        metadata = self._current_workspace_metadata(result=result)
        if not self._validate_metadata_for_save(metadata):
            return
        try:
            state = self._weekly_training_service.replace_second_match(
                board,
                opponent_name=metadata.opponent_name,
                roster_players=self._roster_players,
                match_date=metadata.scheduled_date,
                linked_match_record_id=linked_match_record_id or self._linked_canonical_record_id(result),
                competition_type=self._weekly_competition_type_for_save(result),
            )
            self._assert_visible_board_matches_weekly_record(
                board,
                state,
                linked_match_record_id,
            )
        except Exception as exc:
            self._view.show_error(
                t(
                    "match.save_as_first_match_error",
                    reason=f"{type(exc).__name__}: {exc}",
                )
            )
            return
        self._view.show_status(
            self._weekly_save_success_message(2)
        )
        if self._app_events is not None:
            self._app_events.weekly_plan_saved.emit()

    @staticmethod
    def _has_usable_lineup(board, result=None):
        board_count = 0
        if board is not None:
            board_count = len(
                [
                    slot
                    for slot in getattr(board, "slots", ()) or ()
                    if getattr(slot, "player", None) is not None
                ]
            )
        if board_count == 11:
            return True
        formation = getattr(result, "recommended_formation", None)
        return len(getattr(formation, "lineup", ()) or ()) == 11

    def _import_official_ratings(self, raw_text, slot=None):
        from ht_coach_app.services.official_rating_service import (
            OfficialRatingAmbiguousMatch,
            OfficialRatingImportError,
            OfficialRatingImportService,
            OfficialRatingMatchIdMismatch,
            OfficialRatingReplaceConfirmationRequired,
            POST,
            PRE,
        )
        from ht_coach_app.widgets.match_id_mismatch_dialog import (
            MatchIdMismatchDialog,
        )

        slot = slot or PRE
        if slot == PRE:
            self._trace_runtime_integrity(
                "PRE_IMPORT_STARTED",
                caller="_import_official_ratings",
                reason="official_rating_import_requested",
            )
        self._save_recovery_snapshot_if_dirty()
        if self._official_rating_service is None:
            self._official_rating_service = OfficialRatingImportService()

        try:
            target_snapshot_id = ""
            if self._workspace_mode == WORKSPACE_MODE_EDIT_SAVED_MATCH:
                try:
                    target_snapshot_id = self._require_active_saved_match_record_id(
                        "import_official_ratings",
                    )
                except RuntimeError as exc:
                    self._show_official_import_error(exc)
                    return

            if target_snapshot_id:
                record = self._official_rating_service.get_snapshot(
                    target_snapshot_id
                )
                if slot == POST and record is not None and record.official_pre is not None:
                    parsed_post = self._official_rating_service._parse_and_validate(
                        raw_text,
                        "",
                        POST,
                    )
                    pre_match_id = record.official_pre.hattrick_match_id
                    post_match_id = parsed_post.hattrick_match_id
                    if pre_match_id and post_match_id and pre_match_id != post_match_id:
                        raise OfficialRatingMatchIdMismatch(
                            pre_match_id,
                            post_match_id,
                            target_snapshot_id,
                            raw_text,
                        )
                outcome = self._official_rating_service.import_ratings(
                    target_snapshot_id,
                    raw_text,
                    slot=slot,
                )
            else:
                outcome = self._official_rating_service.import_and_link(
                    raw_text, slot=slot
                )
            if slot == PRE:
                self._trace_runtime_integrity(
                    "PRE_PARSED",
                    caller="_import_official_ratings",
                    reason="import_outcome",
                    imported_snapshot_id=getattr(outcome.snapshot, "snapshot_id", ""),
                    official_match_id=getattr(
                        getattr(outcome, "parsed", None),
                        "hattrick_match_id",
                        "",
                    ),
                )
        except OfficialRatingMatchIdMismatch as exc:
            match_id = MatchIdMismatchDialog.request_match_id(
                exc.pre_match_id,
                exc.post_match_id,
                self._view,
            )
            if not match_id:
                return
            try:
                outcome = (
                    self._official_rating_service
                    .associate_post_after_match_id_confirmation(
                        exc.pre_snapshot_id,
                        exc.raw_text,
                        match_id,
                        language=exc.language,
                    )
                )
            except OfficialRatingImportError as retry_exc:
                self._show_official_import_error(retry_exc)
                return
        except OfficialRatingReplaceConfirmationRequired as exc:
            if not self._view.confirm_official_import_replace(exc.slot):
                return
            try:
                if self._workspace_mode == WORKSPACE_MODE_EDIT_SAVED_MATCH:
                    try:
                        target_snapshot_id = self._require_active_saved_match_record_id(
                            "replace_official_ratings",
                        )
                    except RuntimeError as retry_integrity_exc:
                        self._show_official_import_error(retry_integrity_exc)
                        return
                    outcome = self._official_rating_service.import_ratings(
                        target_snapshot_id,
                        raw_text,
                        slot=slot,
                        confirm_replace=True,
                    )
                else:
                    outcome = self._official_rating_service.import_and_link(
                        raw_text, slot=slot, confirm_replace=True
                    )
            except OfficialRatingImportError as retry_exc:
                self._show_official_import_error(retry_exc)
                return
        except OfficialRatingAmbiguousMatch:
            self._view.confirm_ambiguous_official_import(0)
            return
        except OfficialRatingImportError as exc:
            self._show_official_import_error(exc)
            return

        self._show_official_import_success(outcome)
        self._record_app_event(
            "import_official_ratings", outcome.snapshot.snapshot_id, detail=f"slot={slot}"
        )
        if slot == PRE:
            self._trace_runtime_integrity(
                "PRE_LINKED",
                caller="_import_official_ratings",
                reason=getattr(outcome.snapshot, "snapshot_id", ""),
            )
        self._refresh_after_official_import(outcome.snapshot.snapshot_id)
        if self._app_events is not None:
            self._app_events.official_ratings_changed.emit(outcome.snapshot.snapshot_id)

    def _refresh_after_official_import(self, imported_snapshot_id=None):
        """HF-02.2, Part 3: importing or correcting Official PRE must
        refresh Match Intelligence automatically -- no restart or manual
        re-analysis required. Re-applies the source-selection override
        to whatever result is already on hand; never re-runs the
        optimizer/analysis worker, since only the rating *source* used
        for comparison changed, not the underlying player/formation
        data.

        Alpha 0.6.7 HF-03, Part 1-4: the record the import actually
        touched (`imported_snapshot_id`, from `import_and_link()`'s own
        `ImportOutcome.snapshot`) is threaded straight through, rather
        than re-derived from opponent-name matching -- the two can
        genuinely differ (e.g. the imported text's own Match ID
        resolves to a different opponent than whatever's cached), and
        re-deriving risked resolving to the wrong record entirely."""
        result = self._current_workspace_result(include_legacy=True)
        if result is None:
            return
        result = self._result_with_active_workspace_lineup(result)
        self._trace_runtime_integrity(
            "PRE_IMPORT_REFRESH",
            result=result,
            caller="_refresh_after_official_import",
            reason=imported_snapshot_id or "",
        )
        result = self._apply_official_pre_if_available(
            result, snapshot_id_override=imported_snapshot_id
        )
        self._settings_repository.save_last_result(result)
        self._show_training_context_from_result(result)
        workspace_state = (
            self._view.current_workspace_state()
            if hasattr(self._view, "current_workspace_state")
            else None
        )
        self._view.show_results(result, workspace_state=workspace_state)
        self._trace_runtime_integrity(
            "RECOMMENDATION_RENDERED",
            result=result,
            caller="_refresh_after_official_import",
            reason="show_results_after_pre",
        )
        self._trace_runtime_integrity(
            "FORMATION_BOARD_REBUILT",
            result=result,
            caller="_refresh_after_official_import",
            reason="show_results_after_pre",
        )
        self._update_pre_status_and_ratings_panel(snapshot_id_override=imported_snapshot_id)

    def _show_official_import_error(self, exc):
        reason = str(exc)
        specific_keys = {
            "empty_copy_ratings_text": "match.official_import.error.no_hattrick_summary",
            "no_match_id_in_text": "match.official_import.error.no_match_id",
        }
        matched_key = next(
            (key for prefix, key in specific_keys.items() if reason.startswith(prefix)),
            None,
        )
        message = (
            t(matched_key)
            if matched_key
            else t("match.official_import.error.generic", reason=reason)
        )
        self._view.show_official_import_error(message)

    def _show_official_import_success(self, outcome):
        # Ratings, metadata, timestamps and comparisons intentionally
        # are not shown here -- Match only prepares the next match; all
        # official-rating analysis lives in the dedicated Match
        # Intelligence page. `outcome` is still returned to callers
        # that need it (e.g. Match Intelligence's own refresh), it's
        # just not rendered inside Match itself.
        self._view.show_official_import_success()
