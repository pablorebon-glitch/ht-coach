from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox

from ht_coach_app.core.localization import t


class MatchIntelligenceController(QObject):
    def __init__(self, view, service=None, parent=None):
        super().__init__(parent)
        self._view = view
        self._service = service

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

        comparison_rows = service.prediction_comparison_rows(snapshot)
        prediction_lines = []
        if not service.scales_confirmed_compatible:
            prediction_lines.append(t("official_match_intelligence.scale_limitation"))
        for sector, predicted, official, delta in comparison_rows:
            delta_text = "-" if delta is None else str(delta)
            prediction_lines.append(f"{sector}: {predicted} | {official} | {delta_text}")

        sector_lines = [
            f"{sector}: {t('official_match_intelligence.official')}={official}"
            for sector, _predicted, official, _delta in comparison_rows
            if official != "?"
        ]

        self._view.show_snapshot(
            {
                "pre": pre_text,
                "post": post_text,
                "prediction": "\n".join(prediction_lines),
                "sector": "\n".join(sector_lines) or None,
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

    def _import(self, text, slot, confirm_replace=False):
        from ht_coach_app.services.official_rating_service import (
            OfficialRatingAmbiguousMatch,
            OfficialRatingImportError,
            OfficialRatingReplaceConfirmationRequired,
        )

        service = self._get_service()
        try:
            service.import_ratings(text, slot=slot, confirm_replace=confirm_replace)
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

        self.refresh()
