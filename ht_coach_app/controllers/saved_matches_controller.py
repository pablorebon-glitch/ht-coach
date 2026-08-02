from PySide6.QtCore import QObject

from ht_coach_app.core.localization import t
from ht_coach_app.services.match_record_status_formatting import (
    match_record_status_label,
)


class SavedMatchesController(QObject):
    def __init__(
        self, view, repository=None, weekly_repository=None,
        workspace_repository=None, app_events=None, parent=None,
    ):
        super().__init__(parent)
        self._view = view
        self._repository = repository
        self._weekly_repository = weekly_repository
        self._workspace_repository = workspace_repository
        self._app_events = app_events

        if hasattr(self._view, "refresh_requested"):
            self._view.refresh_requested.connect(self.refresh)
        if hasattr(self._view, "delete_requested"):
            self._view.delete_requested.connect(self._delete_record)
        if hasattr(self._view, "find_duplicates_requested"):
            self._view.find_duplicates_requested.connect(self._find_duplicates)
        if (
            self._app_events is not None
            and hasattr(self._app_events, "match_records_changed")
        ):
            self._app_events.match_records_changed.connect(
                lambda _snapshot_id: self.refresh()
            )

    def _find_duplicates(self):
        """Alpha 0.6.7 HF-02, Part 10: safe duplicates merge
        automatically; anything ambiguous gets an explicit choice from
        the person, one group at a time -- never silently merged."""
        if self._repository is None:
            return

        from engine.history.duplicate_reconciliation import (
            reconcile_duplicates,
            resolve_duplicate_group_manually,
        )

        report = reconcile_duplicates(self._repository)

        resolved_count = 0
        if hasattr(self._view, "ask_which_record_to_keep"):
            for group in report.unresolved_groups:
                description = t(
                    "saved_matches.resolve_duplicate_intro"
                ) + f"\n\n{group.conflict_reason}"
                record_descriptions = [
                    (record.snapshot_id, self._describe_record(record))
                    for record in group.records
                ]
                chosen_id = self._view.ask_which_record_to_keep(
                    description, record_descriptions
                )
                if chosen_id is None:
                    continue
                resolve_duplicate_group_manually(self._repository, group, chosen_id)
                resolved_count += 1

        if hasattr(self._view, "show_reconciliation_summary"):
            self._view.show_reconciliation_summary(
                report.merged_count, report.unresolved_count - resolved_count
            )
        self.refresh()

    @staticmethod
    def _describe_record(record):
        opponent = record.match_context.opponent.opponent_name or "?"
        date_text = record.match_context.match_date or t("saved_matches.date_unknown")
        has_pre = t("saved_matches.resolve_duplicate.has_pre") if record.official_pre else ""
        has_post = t("saved_matches.resolve_duplicate.has_post") if record.official_post else ""
        evidence = " / ".join(part for part in (has_pre, has_post) if part)
        base = f"{opponent} — {date_text}"
        return f"{base} ({evidence})" if evidence else base

    def open_record(self, snapshot_id):
        self.refresh()
        if hasattr(self._view, "select_snapshot"):
            self._view.select_snapshot(snapshot_id)

    def _delete_record(self, snapshot_id):
        if self._repository is None:
            return
        if hasattr(self._view, "confirm_delete") and not self._view.confirm_delete():
            return

        from engine.history.match_deletion import (
            delete_saved_match,
            find_linked_weekly_match_records,
        )

        record = self._repository.get(snapshot_id)
        weekly_state = self._weekly_repository.load() if self._weekly_repository else None
        linked_records = (
            find_linked_weekly_match_records(weekly_state, record)
            if record is not None and weekly_state is not None
            else ()
        )

        delete_weekly_link = False
        if linked_records:
            if not hasattr(self._view, "confirm_weekly_link_deletion"):
                return
            choice = self._view.confirm_weekly_link_deletion()
            if choice == "cancel":
                return
            delete_weekly_link = choice == "analysis_and_weekly"

        delete_saved_match(
            self._repository, snapshot_id,
            delete_weekly_link=delete_weekly_link,
            weekly_repository=self._weekly_repository,
            weekly_state=weekly_state,
            workspace_repository=self._workspace_repository,
        )
        try:
            from ht_coach_app.diagnostics.event_buffer import record_event

            record_event("delete_record", snapshot_id)
        except Exception:
            pass
        self.refresh()

    def refresh(self):
        if self._repository is None:
            self._view.show_rows([])
            return

        from engine.history.record_navigation import list_records

        records = list_records(self._repository)
        rows = [self._format_row(record) for record in records]
        self._view.show_rows(rows)

    @staticmethod
    def _format_row(record):
        opponent = record.match_context.opponent.opponent_name or "?"
        competition_key = getattr(
            record.match_context.competition_type,
            "value",
            record.match_context.competition_type,
        )
        competition = t(f"official_match_intelligence.history.competition.{competition_key}")
        date_text = record.match_context.match_date or t("saved_matches.date_unknown")
        season_week_text = (
            f"{record.season_week.season_number} / {record.season_week.season_week}"
            if record.season_week.is_known
            else t("dual_week.season_unknown")
        )
        venue_key = getattr(
            record.match_context.home_away, "value", record.match_context.home_away
        ) or "unknown"
        venue_text = t(f"match.venue_role_{venue_key}")
        return {
            "snapshot_id": record.snapshot_id,
            "opponent": opponent,
            "competition": competition,
            "date": date_text,
            "season_week": season_week_text,
            "venue": venue_text,
            "status": match_record_status_label(record.status),
        }
