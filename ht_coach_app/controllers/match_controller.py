from PySide6.QtCore import QObject, QThread, QTimer

from dataclasses import replace

from engine.squad_health.availability_service import CURRENT_AVAILABLE
from ht_coach_app.change_analysis.service import ChangeAnalysisService
from ht_coach_app.core.localization import t
from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceSettings,
)
from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.services.match_workspace_service import (
    MATCH_TYPE_CUP,
    MATCH_TYPE_LEAGUE,
    MatchWorkspaceValidationError,
    format_decision_lab,
    format_match_summary,
    format_recommended_lineup,
    with_tactical_advisor,
)
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from ht_coach_app.workers.match_analysis_worker import (
    MatchAnalysisWorker,
)


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
        self._thread = None
        self._worker = None
        self._roster_players = []
        self._pending_workspace_state = None
        self._queued_workspace_state = None
        self._latest_workspace_revision = None
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
                self._handle_external_official_ratings_changed
            )

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
        last_result = self._settings_repository.load_last_result()

        if last_result is not None:
            self._view.show_results(
                last_result,
                restored=True
            )

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
        self._load_current_roster_for_inspector(show_errors=False)
        self._view.show_status(
            f"Roster updated from Squad: {player_count} players."
        )
        self._save_current_settings()

    def _browse_players(self):
        path = self._view.choose_players_file()

        if path:
            self._view.set_players_csv_path(path)
            self._save_current_settings()
            self._load_players()

    def _load_players(self):
        try:
            players = self._service.load_players(
                self._view.players_csv_path(),
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
        match_type = (
            self._view.match_type() if hasattr(self._view, "match_type") else "LEAGUE"
        )
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

    def _linked_canonical_record_id(self, result):
        """Alpha 0.6.7, Part 19: the canonical Match Record this saved
        weekly lineup belongs to. If we're already editing a specific
        record, that's it -- no lookup needed. Otherwise, finds or
        creates the provisional record for this exact match (reusing
        Part 11's own creation flow), so saving from Match never
        creates a second, disconnected weekly-only identity."""
        if self._editing_snapshot_id:
            self._persist_metadata_corrections_to_canonical_record(self._editing_snapshot_id)
            self._persist_lineup_to_canonical_record(self._editing_snapshot_id, result)
            return self._editing_snapshot_id

        repository = self._history_repository()
        if repository is None:
            return ""

        from datetime import date

        from engine.history.provisional_record import find_or_create_provisional_record

        opponent_name = getattr(result, "opponent_name", "") or ""
        if not opponent_name:
            return ""
        match_date = (
            self._view.match_date()
            if hasattr(self._view, "match_date") and self._view.match_date()
            else date.today().isoformat()
        )
        try:
            record = find_or_create_provisional_record(
                repository,
                opponent_name=opponent_name,
                match_date=match_date,
                competition_type="league",
                home_away=(
                    self._view.venue_role() if hasattr(self._view, "venue_role") else ""
                ),
            )
            self._persist_lineup_to_canonical_record(record.snapshot_id, result)
            return record.snapshot_id
        except Exception:
            return ""

    def _history_repository(self):
        service = getattr(self, "_official_rating_service", None)
        return getattr(service, "_repository", None) if service is not None else None

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

        self._editing_snapshot_id = snapshot_id
        self._record_app_event("switch_record", snapshot_id)
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
            match_type = "CUP" if str(competition_value).lower() == "cup" else "LEAGUE"
            self._view.set_match_type(match_type)

        if hasattr(self._view, "set_match_date") and record.match_context.match_date:
            self._view.set_match_date(record.match_context.match_date)

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
        self._restore_full_workspace_if_available(record, opponent_name)

    def _handle_workspace_changed(self):
        self._save_current_settings()
        self._update_metadata_evidence_warning()

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
        current_type = (
            self._view.match_type().lower()
            if hasattr(self._view, "match_type")
            else ""
        )
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
        last_result = self._settings_repository.load_last_result()
        matches_this_record = (
            last_result is not None
            and getattr(last_result, "opponent_name", "") == opponent_name
        )
        if matches_this_record:
            self._pending_workspace_state = None
            self._view.show_results(last_result, restored=True)
            self._update_pre_status_and_ratings_panel()
            return

        if hasattr(self._view, "show_status"):
            self._view.show_status(
                t("match.edit_requires_reanalysis")
            )

    def _analyze(self):
        try:
            self._service.validate_inputs(
                self._view.players_csv_path(),
                self._view.selected_opponent_name(),
                self._view.selected_formations()
            )
        except MatchWorkspaceValidationError as exc:
            self._view.show_error(
                str(exc)
            )
            return

        match_type = (
            self._view.match_type()
            if hasattr(self._view, "match_type")
            else MATCH_TYPE_LEAGUE
        )

        required_player_ids = None
        training_rules = None
        if match_type == MATCH_TYPE_CUP:
            training_rules = self._weekly_training_service.active_training_rules()
            if training_rules is None:
                self._view.show_error(
                    t("match.cup_training_rules_unavailable")
                )
                return
            required_player_ids = (
                self._weekly_training_service.required_player_ids_for_match()
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
            self._view.players_csv_path(),
            self._view.selected_opponent_name(),
            self._view.selected_formations(),
            availability_mode=self._availability_mode(),
            match_type=match_type,
            required_player_ids=required_player_ids,
            training_rules=training_rules,
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
        try:
            self._service.validate_inputs(
                self._view.players_csv_path(),
                self._view.selected_opponent_name(),
                list(workspace_state.workspace_boards.keys())
            )
        except MatchWorkspaceValidationError as exc:
            self._view.show_error(
                str(exc)
            )
            return

        self._save_current_settings()
        self._pending_workspace_state = workspace_state
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
            self._view.players_csv_path(),
            self._view.selected_opponent_name(),
            list(workspace_state.workspace_boards.keys()),
            workspace_state=workspace_state,
            availability_mode=self._availability_mode(),
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

    def _analysis_finished(self, result):
        finished_workspace_state = self._pending_workspace_state
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

        if finished_workspace_state is not None:
            previous_result = self._settings_repository.load_last_result()
            change_analysis = self._change_analysis_service.analyze(
                previous_result,
                result,
                finished_workspace_state,
            )
            result = replace(
                result,
                change_analysis=change_analysis,
            )
            result = with_tactical_advisor(result)

        if finished_workspace_state is not None and hasattr(
            self._view,
            "set_workspace_processing",
        ):
            self._view.set_workspace_processing(False)
        else:
            self._view.set_processing(False)
        previous_result = self._settings_repository.load_last_result()
        result = self._apply_official_pre_if_available(result)
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
        self._pending_workspace_state = None
        self._view.show_status(
            "Match analysis complete."
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

        from engine.history.models import MatchContext, OpponentReference

        match_date = self._current_match_date() or record.match_context.match_date
        opponent_name = (
            self._view.selected_opponent_name()
            if hasattr(self._view, "selected_opponent_name")
            else ""
        ) or record.match_context.opponent.opponent_name
        competition_type = (
            self._view.match_type().lower()
            if hasattr(self._view, "match_type")
            else record.match_context.competition_type
        )
        venue_role = (
            self._view.venue_role()
            if hasattr(self._view, "venue_role")
            else record.match_context.home_away
        )

        try:
            updated_context = MatchContext(
                official_match_id=record.match_context.official_match_id,
                match_date=match_date,
                kickoff_time=record.match_context.kickoff_time,
                season=record.match_context.season,
                round=record.match_context.round,
                competition_type=competition_type,
                match_type=record.match_context.match_type,
                home_away=venue_role,
                team_type=record.match_context.team_type,
                opponent=replace(
                    record.match_context.opponent
                    if record.match_context.opponent is not None
                    else OpponentReference(),
                    opponent_name=opponent_name,
                ),
                venue=record.match_context.venue,
                snapshot_stage=record.match_context.snapshot_stage,
            )
            season_week = self._resolve_season_week(match_date)
            training_cycle_id = self._resolve_training_cycle_id(match_date)
            repository.save(
                record.with_updates(
                    match_context=updated_context,
                    training_cycle_id=training_cycle_id,
                    ht_season_number=season_week.season_number,
                    ht_season_week=season_week.season_week,
                )
            )
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
        repository = self._history_repository()
        if repository is None or not snapshot_id:
            return
        record = repository.get(snapshot_id)
        if record is None:
            return
        recommended = getattr(result, "recommended_formation", None)
        if recommended is None:
            return

        from engine.history.lineup_snapshot import build_historical_lineup, build_tactical_setup

        try:
            tactical_setup = build_tactical_setup(recommended)
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
            updated = record.with_updates(
                lineup=build_historical_lineup(recommended),
                tactical_setup=tactical_setup,
            )
            repository.save(updated)
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

        if self._editing_snapshot_id:
            return repository.get(self._editing_snapshot_id)

        opponent_name = (
            self._view.selected_opponent_name()
            if hasattr(self._view, "selected_opponent_name")
            else ""
        )
        if not opponent_name:
            # The opponent selector may be empty in some flows (e.g. a
            # result was already shown but the combo wasn't
            # separately re-populated) -- the currently displayed
            # analysis result's own opponent is just as valid a source
            # for "which match is this workspace showing."
            last_result = self._settings_repository.load_last_result()
            opponent_name = getattr(last_result, "opponent_name", "") if last_result else ""
        if not opponent_name:
            return None
        match_date = self._current_match_date() or ""
        match_type = (
            self._view.match_type() if hasattr(self._view, "match_type") else "LEAGUE"
        )
        competition_type = str(match_type).lower()

        from engine.history.match_lookup import find_existing_or_conflicting_record

        result = find_existing_or_conflicting_record(
            repository, opponent_name, competition_type, match_date=match_date,
        )
        if result.kind == "exact":
            return result.record
        return None

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
        result = self._settings_repository.load_last_result()

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
        result = self._settings_repository.load_last_result()

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
        result = self._settings_repository.load_last_result()

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

    def _load_current_roster_for_inspector(self, show_errors):
        try:
            players = self._service.load_players(
                self._view.players_csv_path(),
                availability_mode=self._availability_mode(),
            )
        except Exception as exc:
            self._roster_players = []
            self._set_view_roster_players([])
            if show_errors:
                self._view.show_error(str(exc))
            return

        self._roster_players = players
        self._set_view_roster_players(players)

    def _set_view_roster_players(self, players):
        if hasattr(self._view, "set_roster_players"):
            self._view.set_roster_players(players)

    def _availability_mode(self):
        if hasattr(self._view, "availability_mode"):
            return self._view.availability_mode()

        return CURRENT_AVAILABLE

    def _current_match_date(self):
        if hasattr(self._view, "match_date") and self._view.match_date():
            return self._view.match_date()
        return None

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

        training_cycle_id = self._resolve_training_cycle_id(match_date_text)
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

    def _save_as_first_match(self):
        result = self._settings_repository.load_last_result()
        if result is None or not getattr(result, "formations", None):
            self._view.show_error(
                t("match.save_as_first_match_no_result")
            )
            return
        if not self._confirm_match_type_for_save(result, MATCH_TYPE_LEAGUE):
            return

        recommended = result.recommended_formation
        try:
            board = self._formation_board_mapper.to_board(recommended)
            self._weekly_training_service.record_first_match(
                board,
                opponent_name=result.opponent_name,
                roster_players=self._roster_players,
                match_date=self._current_match_date(),
                linked_match_record_id=self._linked_canonical_record_id(result),
            )
        except ValueError as exc:
            if str(exc) == "duplicate_match_id":
                self._replace_first_match_after_confirmation(board, result)
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
            t("match.save_as_first_match_success")
        )
        if self._app_events is not None:
            self._app_events.weekly_plan_saved.emit()

    def _confirm_match_type_for_save(self, result, expected_type):
        """Warn if the analysis about to be saved (the last one that
        finished, which may not be the one currently showing on screen)
        was run in a different mode than the slot being saved into.
        Saving a League-mode analysis as the second (Cup) match, or vice
        versa, is very easy to do by mistake — e.g. re-running a League
        check right before saving silently swaps out the Cup-aware
        lineup for a plain one, with no error to flag it."""
        actual_type = getattr(result, "match_type", None)
        if actual_type is None or actual_type == expected_type:
            return True
        if not hasattr(self._view, "confirm_save_match_type_mismatch"):
            return True
        expected_label = (
            t("match.match_type_league")
            if expected_type == MATCH_TYPE_LEAGUE
            else t("match.match_type_cup")
        )
        actual_label = (
            t("match.match_type_league")
            if actual_type == MATCH_TYPE_LEAGUE
            else t("match.match_type_cup")
        )
        return self._view.confirm_save_match_type_mismatch(
            expected_label, actual_label
        )

    def _replace_first_match_after_confirmation(self, board, result):
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
        try:
            self._weekly_training_service.replace_first_match(
                board,
                opponent_name=result.opponent_name,
                roster_players=self._roster_players,
                match_date=self._current_match_date(),
                linked_match_record_id=self._linked_canonical_record_id(result),
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
            t("match.save_as_first_match_success")
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
        result = self._settings_repository.load_last_result()
        if result is None or not getattr(result, "formations", None):
            if self._editing_snapshot_id:
                self._persist_metadata_corrections_to_canonical_record(
                    self._editing_snapshot_id
                )
                self._update_metadata_evidence_warning()
                if hasattr(self._view, "show_status"):
                    self._view.show_status(t("match.metadata_saved"))
                self._record_app_event("save_metadata", self._editing_snapshot_id)
                return
            self._view.show_error(
                t("match.save_as_first_match_no_result")
            )
            return

        record = self._current_workspace_record()
        if record is None:
            opponent_name = getattr(result, "opponent_name", "") or ""
            if not opponent_name:
                self._view.show_error(t("match.save_as_first_match_no_result"))
                return
            repository = self._history_repository()
            if repository is None:
                return
            from datetime import date

            match_date = self._current_match_date() or date.today().isoformat()
            match_type = (
                self._view.match_type() if hasattr(self._view, "match_type") else "LEAGUE"
            )
            from engine.history.provisional_record import find_or_create_provisional_record

            record = find_or_create_provisional_record(
                repository,
                opponent_name=opponent_name,
                match_date=match_date,
                competition_type=str(match_type).lower(),
                home_away=(
                    self._view.venue_role() if hasattr(self._view, "venue_role") else ""
                ),
            )
            self._editing_snapshot_id = record.snapshot_id

        self._persist_metadata_corrections_to_canonical_record(record.snapshot_id)
        self._persist_lineup_to_canonical_record(record.snapshot_id, result)
        self._record_app_event("save_formation", record.snapshot_id)
        self._discard_recovery_snapshot(record.snapshot_id)
        if (
            self._app_events is not None
            and hasattr(self._app_events, "match_records_changed")
        ):
            self._app_events.match_records_changed.emit(record.snapshot_id)

        if hasattr(self._view, "show_status"):
            self._view.show_status(t("match.formation_saved"))
        self._update_metadata_evidence_warning()

    def _save_as_second_match(self):
        result = self._settings_repository.load_last_result()
        if result is None or not getattr(result, "formations", None):
            self._view.show_error(
                t("match.save_as_first_match_no_result")
            )
            return
        if not self._confirm_match_type_for_save(result, MATCH_TYPE_CUP):
            return

        recommended = result.recommended_formation
        try:
            board = self._formation_board_mapper.to_board(recommended)
            self._weekly_training_service.record_second_match(
                board,
                opponent_name=result.opponent_name,
                roster_players=self._roster_players,
                match_date=self._current_match_date(),
                linked_match_record_id=self._linked_canonical_record_id(result),
            )
        except ValueError as exc:
            if str(exc) == "duplicate_match_id":
                self._replace_second_match_after_confirmation(board, result)
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
            t("match.save_as_first_match_success")
        )
        if self._app_events is not None:
            self._app_events.weekly_plan_saved.emit()

    def _replace_second_match_after_confirmation(self, board, result):
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
        try:
            self._weekly_training_service.replace_second_match(
                board,
                opponent_name=result.opponent_name,
                roster_players=self._roster_players,
                match_date=self._current_match_date(),
                linked_match_record_id=self._linked_canonical_record_id(result),
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
            t("match.save_as_first_match_success")
        )
        if self._app_events is not None:
            self._app_events.weekly_plan_saved.emit()

    def _import_official_ratings(self, raw_text, slot=None):
        from ht_coach_app.services.official_rating_service import (
            OfficialRatingAmbiguousMatch,
            OfficialRatingImportError,
            OfficialRatingImportService,
            OfficialRatingMatchIdMismatch,
            OfficialRatingReplaceConfirmationRequired,
            PRE,
        )
        from ht_coach_app.widgets.match_id_mismatch_dialog import (
            MatchIdMismatchDialog,
        )

        slot = slot or PRE
        self._save_recovery_snapshot_if_dirty()
        if self._official_rating_service is None:
            self._official_rating_service = OfficialRatingImportService()

        try:
            outcome = self._official_rating_service.import_and_link(
                raw_text, slot=slot
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
        result = self._settings_repository.load_last_result()
        if result is None:
            return
        result = self._apply_official_pre_if_available(
            result, snapshot_id_override=imported_snapshot_id
        )
        self._settings_repository.save_last_result(result)
        self._view.show_results(result, workspace_state=None)
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
