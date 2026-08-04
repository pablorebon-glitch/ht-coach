from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox

from ht_coach_app.core.localization import t


class MatchIntelligenceController(QObject):
    def __init__(self, view, service=None, app_events=None, parent=None):
        super().__init__(parent)
        self._view = view
        self._service = service
        self._app_events = app_events
        self._season_filter = None
        self._selected_snapshot_id = None

        if hasattr(self._view, "import_requested"):
            self._view.import_requested.connect(self._open_import_dialog)
        if hasattr(self._view, "refresh_requested"):
            self._view.refresh_requested.connect(self.refresh)
        if hasattr(self._view, "season_filter_changed"):
            self._view.season_filter_changed.connect(self._change_season_filter)
        if hasattr(self._view, "record_navigation_requested"):
            self._view.record_navigation_requested.connect(self._navigate_record)
        if hasattr(self._view, "record_selected"):
            self._view.record_selected.connect(self._select_record)
        if (
            self._app_events is not None
            and hasattr(self._app_events, "match_records_changed")
        ):
            self._app_events.match_records_changed.connect(
                self._handle_match_records_changed
            )

        self.refresh()

    def _handle_match_records_changed(self, snapshot_id):
        if snapshot_id:
            self._selected_snapshot_id = snapshot_id
        self.refresh()

    def _populate_history_navigation(self, service):
        if not hasattr(self._view, "set_available_seasons"):
            return
        self._view.set_available_seasons(service.available_seasons())

        records = service.history_records(season_number=self._season_filter)
        options = [
            (record.snapshot_id, self._format_record_option(record))
            for record in records
        ]
        self._view.set_record_options(options, self._selected_snapshot_id)

        context = service.navigate_history(records, self._selected_snapshot_id, "current")
        if hasattr(self._view, "show_record_navigation_state"):
            self._view.show_record_navigation_state(
                context.can_go_previous, context.can_go_next
            )

    @staticmethod
    def _format_record_option(record):
        """Alpha 0.6.7, Part 14/HF-02 Part 6: the selector shows *only*
        the match identity, built through the one central formatter
        used everywhere a match needs to be named -- never a
        one-off string built here, which is exactly how duplicated
        fragments crept in before."""
        from ht_coach_app.services.match_display_formatter import (
            format_match_record_identity,
        )

        return format_match_record_identity(record)

    @staticmethod
    def _format_record_identity(snapshot):
        from ht_coach_app.services.dual_week_formatting import format_season_week
        from ht_coach_app.services.match_record_status_formatting import (
            match_record_status_label,
        )

        from ht_coach_app.services.match_display_formatter import (
            format_match_record_identity,
        )

        identity = format_match_record_identity(snapshot)
        date_text = snapshot.match_context.match_date or "?"
        competition = t(
            f"official_match_intelligence.history.competition.{getattr(snapshot.match_context.competition_type, 'value', snapshot.match_context.competition_type)}"
        )
        lines = [
            identity,
            format_season_week(snapshot.season_week),
            f"{date_text} · {competition}",
            t(
                "official_match_intelligence.history.status_line",
                status=match_record_status_label(snapshot.status),
            ),
        ]
        if snapshot.match_context.official_match_id:
            lines.append(
                t(
                    "official_match_intelligence.history.match_id_line",
                    match_id=snapshot.match_context.official_match_id,
                )
            )
        return "\n".join(lines)

    def _change_season_filter(self, season_number):
        self._season_filter = season_number
        self._selected_snapshot_id = None
        self.refresh()

    def _navigate_record(self, direction):
        records = self._get_service().history_records(season_number=self._season_filter)
        context = self._get_service().navigate_history(
            records, self._selected_snapshot_id, direction
        )
        self._selected_snapshot_id = context.record.snapshot_id if context.record else None
        self.refresh()

    def _select_record(self, snapshot_id):
        self._selected_snapshot_id = snapshot_id
        self.refresh()

    def _offer_retrospective_pre_if_applicable(self, text):
        """Alpha 0.6.6, Part 17: before treating a PRE-shaped import as
        a normal PRE, check whether it looks like a formation
        reproduced *after* an already-played, still-PRE-less match --
        if so, offer it as a retrospective simulation instead. Returns
        True when this path fully handled the import (whether the user
        confirmed or declined), False to let the normal import flow
        proceed unchanged."""
        from engine.history.retrospective_pre import (
            detect_retrospective_pre_candidate,
            save_as_retrospective_simulation,
        )
        from ht_coach_app.services.official_rating_service import (
            OfficialRatingImportError,
            OfficialRatingImportService,
            PRE,
        )

        if not hasattr(self._view, "confirm_retrospective_pre"):
            return False

        try:
            parsed = OfficialRatingImportService._parse_and_validate(text, "", PRE)
        except OfficialRatingImportError:
            # Not parseable as PRE at all -- let the normal import path
            # raise and surface the real error message.
            return False

        service = self._get_service()
        candidate = detect_retrospective_pre_candidate(service._repository, parsed)
        if candidate is None:
            return False

        if not self._view.confirm_retrospective_pre():
            return True

        save_as_retrospective_simulation(service._repository, candidate, parsed)
        self._selected_snapshot_id = candidate.snapshot_id
        self._refresh_and_notify()
        return True

    def _get_service(self):
        if self._service is None:
            from ht_coach_app.services.match_intelligence_service import (
                MatchIntelligenceAppService,
            )

            self._service = MatchIntelligenceAppService()
        return self._service

    def refresh(self):
        service = self._get_service()
        self._populate_history_navigation(service)

        snapshot = None
        if self._selected_snapshot_id is not None:
            snapshot = service._repository.get(self._selected_snapshot_id)
        if snapshot is None:
            snapshot = service.latest_snapshot_with_official_data()
            if snapshot is not None:
                self._selected_snapshot_id = snapshot.snapshot_id
        if snapshot is None:
            self._view.show_empty_state()
            return

        if hasattr(self._view, "set_record_identity"):
            self._view.set_record_identity(self._format_record_identity(snapshot))

        effective_pre = service.effective_pre(snapshot)
        pre_text = service.format_official_summary(effective_pre)
        if snapshot.official_pre is None and snapshot.retrospective_pre is not None:
            pre_text = "\n".join(
                text
                for text in (
                    t("official_match_intelligence.retrospective.pre_label"),
                    pre_text,
                    t("official_match_intelligence.retrospective.limitation"),
                )
                if text
            )
        post_text = service.format_official_summary(snapshot.official_post)

        # Part 5: interpreted comparison -- exact values plus a
        # deterministic direction/magnitude classification, never just
        # raw numbers.
        comparison_lines = []
        if effective_pre is not None and snapshot.official_post is not None:
            from ht_coach_app.services.retrospective_comparison_formatting import (
                comparison_label,
            )

            interpreted_rows = service.interpreted_pre_post_rows(snapshot)
            comparison_lines.append(
                comparison_label(
                    snapshot.official_pre is not None,
                    snapshot.retrospective_pre is not None,
                )
            )
            for sector, pre, post, delta, direction, magnitude in interpreted_rows:
                if direction is None:
                    comparison_lines.append(
                        f"{sector}: PRE {pre} -> POST {post} "
                        f"({t('official_match_intelligence.missing_data_short')})"
                    )
                    continue
                direction_label = t(f"official_match_intelligence.direction.{direction}")
                magnitude_key = (
                    "large_improvement"
                    if magnitude == "large" and direction == "improved"
                    else magnitude
                )
                magnitude_label = t(f"official_match_intelligence.magnitude.{magnitude_key}")
                comparison_lines.append(
                    f"{sector}\nPRE {pre}  POST {post}  "
                    f"{t('official_match_intelligence.change_label')} {delta}\n"
                    f"{direction_label} — {magnitude_label}"
                )
        elif effective_pre is not None:
            comparison_lines = [t("official_match_intelligence.post_missing")]
        elif snapshot.official_post is not None:
            comparison_lines = [t("official_match_intelligence.pre_missing")]

        # Part 6: deterministic, useful conclusions -- never just "PRE
        # and POST are associated by Match ID."
        conclusions = service.pre_post_conclusions(snapshot)
        conclusion_lines = [t(c.key, **c.params) for c in conclusions]

        # Part 7: the internal HT Coach estimate collapses under
        # "Diagnóstico interno" -- shown only on request, with a
        # concise limitation note instead of question-mark rows when
        # the scale isn't confirmed comparable.
        comparison_rows = service.prediction_comparison_rows(snapshot)
        prediction_lines = []
        internal_limitation = ""
        if not service.scales_confirmed_compatible:
            internal_limitation = t("official_match_intelligence.internal_diagnostic_limitation")
        for sector, predicted, official, delta in comparison_rows:
            if predicted is None and official is None:
                continue
            delta_text = "-" if delta is None else str(delta)
            prediction_lines.append(f"{sector}: {predicted} | {official} | {delta_text}")

        self._view.show_snapshot(
            {
                "pre": pre_text,
                "post": post_text,
                "comparison": "\n\n".join(comparison_lines),
                "conclusions": "\n".join(conclusion_lines),
                "prediction": "\n".join(prediction_lines),
                "internal_diagnostic_limitation": internal_limitation,
            }
        )

    def _open_import_dialog(self):
        from ht_coach_app.widgets.match_intelligence_import_dialog import (
            MatchIntelligenceImportDialog,
        )

        default_slot, hint_text = self._import_dialog_defaults()

        result = MatchIntelligenceImportDialog.request_import(
            self._view, default_slot=default_slot, hint_text=hint_text
        )
        if result is None:
            return
        text, slot = result
        self._import(text, slot)

    def _import_dialog_defaults(self):
        """Alpha 0.6.7, Part 13: the pre-selected slot (and an
        optional explanatory hint) reflect the currently selected
        record's own state -- never a fixed default regardless of
        context. The existing replace-confirmation dialog
        (`OfficialRatingReplaceConfirmationRequired`) still runs
        afterward for a Complete record; this only sets a sensible
        starting choice, it never bypasses that confirmation."""
        service = self._get_service()
        snapshot = None
        if self._selected_snapshot_id is not None:
            snapshot = service._repository.get(self._selected_snapshot_id)

        has_pre = snapshot is not None and snapshot.official_pre is not None
        has_post = snapshot is not None and snapshot.official_post is not None

        if has_pre and has_post:
            return "pre", t("official_match_intelligence.import.hint_complete")
        if has_pre and not has_post:
            return "post", t("official_match_intelligence.import.hint_post_priority")
        if has_post and not has_pre:
            from datetime import date as _date

            match_date_text = snapshot.match_context.match_date
            is_future = False
            if match_date_text:
                try:
                    is_future = _date.fromisoformat(match_date_text[:10]) > _date.today()
                except ValueError:
                    is_future = False
            hint_key = (
                "official_match_intelligence.import.hint_pre_missing_future"
                if is_future
                else "official_match_intelligence.import.hint_pre_missing_past"
            )
            return "pre", t(hint_key)
        return "pre", ""

    def _refresh_and_notify(self):
        self.refresh()
        if self._app_events is not None:
            self._app_events.official_ratings_changed.emit(self._selected_snapshot_id or "")

    def _import(self, text, slot, confirm_replace=False):
        from ht_coach_app.services.official_rating_service import (
            OfficialRatingAmbiguousMatch,
            OfficialRatingImportError,
            OfficialRatingMatchIdMismatch,
            OfficialRatingReplaceConfirmationRequired,
        )
        from ht_coach_app.widgets.match_id_mismatch_dialog import (
            MatchIdMismatchDialog,
        )

        if slot == "pre" and self._offer_retrospective_pre_if_applicable(text):
            return

        service = self._get_service()
        try:
            active_snapshot_id = (
                self._selected_snapshot_id
                if slot == "post" and self._selected_snapshot_id
                else None
            )
            outcome = service.import_ratings(
                text,
                slot=slot,
                confirm_replace=confirm_replace,
                active_snapshot_id=active_snapshot_id,
            )
            self._selected_snapshot_id = outcome.snapshot.snapshot_id
        except OfficialRatingMatchIdMismatch as exc:
            match_id = MatchIdMismatchDialog.request_match_id(
                exc.pre_match_id,
                exc.post_match_id,
                self._view,
            )
            if not match_id:
                return
            try:
                service.associate_post_after_match_id_confirmation(
                    exc.pre_snapshot_id,
                    exc.raw_text,
                    match_id,
                    language=exc.language,
                    confirm_replace=confirm_replace,
                )
            except OfficialRatingReplaceConfirmationRequired:
                if QMessageBox.question(
                    self._view,
                    t("match.official_import.confirm_replace_title"),
                    t("match.official_import.confirm_replace_post"),
                ) == QMessageBox.Yes:
                    service.associate_post_after_match_id_confirmation(
                        exc.pre_snapshot_id,
                        exc.raw_text,
                        match_id,
                        language=exc.language,
                        confirm_replace=True,
                    )
            except OfficialRatingImportError as retry_exc:
                QMessageBox.warning(
                    self._view,
                    t("match.official_import.error_title"),
                    t("match.official_import.error.generic", reason=str(retry_exc)),
                )
                return
            self._refresh_and_notify()
            return
        except OfficialRatingReplaceConfirmationRequired as exc:
            key = (
                "match.official_import.confirm_replace_pre"
                if exc.slot == "pre"
                else "match.official_import.confirm_replace_post"
            )
            if QMessageBox.question(
                self._view,
                t("match.official_import.confirm_replace_title"),
                t(key),
            ) == QMessageBox.Yes:
                self._import(text, slot, confirm_replace=True)
            return
        except OfficialRatingAmbiguousMatch:
            QMessageBox.warning(
                self._view,
                t("match.official_import.error_title"),
                t("match.official_import.error.ambiguous_match"),
            )
            return
        except OfficialRatingImportError as exc:
            QMessageBox.warning(
                self._view,
                t("match.official_import.error_title"),
                t("match.official_import.error.generic", reason=str(exc)),
            )
            return

        self._refresh_and_notify()
