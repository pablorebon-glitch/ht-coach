from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox

from ht_coach_app.core.localization import t


class MatchIntelligenceController(QObject):
    def __init__(self, view, service=None, app_events=None, parent=None):
        super().__init__(parent)
        self._view = view
        self._service = service
        self._app_events = app_events

        if hasattr(self._view, "import_requested"):
            self._view.import_requested.connect(self._open_import_dialog)
        if hasattr(self._view, "refresh_requested"):
            self._view.refresh_requested.connect(self.refresh)

        self.refresh()

    def _get_service(self):
        if self._service is None:
            from ht_coach_app.services.match_intelligence_service import (
                MatchIntelligenceAppService,
            )

            self._service = MatchIntelligenceAppService()
        return self._service

    def refresh(self):
        service = self._get_service()
        snapshot = service.latest_snapshot_with_official_data()
        if snapshot is None:
            self._view.show_empty_state()
            return

        pre_text = service.format_official_summary(snapshot.official_pre)
        post_text = service.format_official_summary(snapshot.official_post)

        # Part 5: interpreted comparison -- exact values plus a
        # deterministic direction/magnitude classification, never just
        # raw numbers.
        comparison_lines = []
        if snapshot.official_pre is not None and snapshot.official_post is not None:
            interpreted_rows = service.interpreted_pre_post_rows(snapshot)
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
        elif snapshot.official_pre is not None:
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

        result = MatchIntelligenceImportDialog.request_import(self._view)
        if result is None:
            return
        text, slot = result
        self._import(text, slot)

    def _refresh_and_notify(self):
        self.refresh()
        if self._app_events is not None:
            self._app_events.official_ratings_changed.emit()

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

        service = self._get_service()
        try:
            service.import_ratings(text, slot=slot, confirm_replace=confirm_replace)
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
