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
        self._formation_board_mapper = FormationBoardMapper()
        self._change_analysis_service = ChangeAnalysisService()
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
        if hasattr(self._view, "official_rating_import_requested"):
            self._view.official_rating_import_requested.connect(
                self._import_official_ratings
            )
        if hasattr(self._view, "workspace_recalculate_requested"):
            self._view.workspace_recalculate_requested.connect(
                self._recalculate_workspace
            )
        self._view.workspace_changed.connect(
            self._save_current_settings
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
        if not self._view.confirm_replace_first_match():
            return
        try:
            self._weekly_training_service.replace_first_match(
                board,
                opponent_name=result.opponent_name,
                roster_players=self._roster_players,
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

    def _replace_second_match_after_confirmation(self, board, result):
        if not hasattr(self._view, "confirm_replace_second_match"):
            self._view.show_error(
                t(
                    "match.save_as_first_match_error",
                    reason="ValueError: duplicate_match_id",
                )
            )
            return
        if not self._view.confirm_replace_second_match():
            return
        try:
            self._weekly_training_service.replace_second_match(
                board,
                opponent_name=result.opponent_name,
                roster_players=self._roster_players,
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

    def _import_official_ratings(self, raw_text, slot=None):
        from ht_coach_app.services.official_rating_service import (
            OfficialRatingAmbiguousMatch,
            OfficialRatingImportError,
            OfficialRatingImportService,
            OfficialRatingReplaceConfirmationRequired,
            PRE,
        )

        slot = slot or PRE
        if self._official_rating_service is None:
            self._official_rating_service = OfficialRatingImportService()

        try:
            outcome = self._official_rating_service.import_and_link(
                raw_text, slot=slot
            )
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
