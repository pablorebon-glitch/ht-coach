from __future__ import annotations

from engine.history.official_ratings.comparison import compare_official_ratings
from engine.history.official_ratings.summary import summarize_official_rating_comparison
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.core.paths import historical_match_snapshots_path
from ht_coach_app.services.official_rating_formatting import (
    SCALES_CONFIRMED_COMPATIBLE,
    format_hattrick_notation,
    format_prediction_vs_official_comparison,
)
from ht_coach_app.services.official_rating_service import OfficialRatingImportService


class MatchIntelligenceAppService:
    """The app-facing bridge for the Match Intelligence page. Reuses
    OfficialRatingImportService for the actual PRE/POST import workflow
    (Alpha 0.5.9.0 / UX-02) rather than duplicating it -- this service's
    only new job is finding the relevant snapshot to display and
    assembling the diagnostic HT-Coach-vs-official comparison."""

    def __init__(self, repository=None, import_service=None):
        self._repository = repository or HistoricalMatchRepository(
            historical_match_snapshots_path()
        )
        self._import_service = import_service or OfficialRatingImportService(
            repository=self._repository
        )

    def latest_snapshot_with_official_data(self):
        """The most recently updated snapshot carrying an official PRE
        or POST capture, or None if nothing has been imported yet."""
        candidates = [
            snapshot for snapshot in self._repository.list_all()
            if snapshot.official_pre is not None or snapshot.official_post is not None
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda snapshot: snapshot.updated_at or "")

    def import_ratings(self, raw_text, slot="pre", confirm_replace=False):
        return self._import_service.import_and_link(
            raw_text, slot=slot, confirm_replace=confirm_replace
        )

    @staticmethod
    def format_official_summary(official_rating_snapshot):
        if official_rating_snapshot is None:
            return ""
        return format_hattrick_notation(
            official_rating_snapshot.ratings,
            official_rating_snapshot.formation,
            official_rating_snapshot.tactic,
            official_rating_snapshot.team_attitude,
        )

    def prediction_comparison_rows(self, snapshot):
        """(sector, predicted, official_pre, delta_or_none) rows,
        comparing HT Coach's own prediction against official PRE.
        `delta_or_none` is always None today -- see
        `official_rating_formatting.SCALES_CONFIRMED_COMPATIBLE`."""
        if snapshot is None:
            return ()
        prediction_ratings = snapshot.predictions.ratings if snapshot.predictions else None
        comparison = compare_official_ratings(
            prediction_ratings, snapshot.official_pre, snapshot.official_post
        )
        return format_prediction_vs_official_comparison(comparison)

    def prediction_accuracy_summary(self, snapshot):
        if snapshot is None or snapshot.official_pre is None:
            return None
        prediction_ratings = snapshot.predictions.ratings if snapshot.predictions else None
        comparison = compare_official_ratings(
            prediction_ratings, snapshot.official_pre, snapshot.official_post
        )
        return summarize_official_rating_comparison(comparison, "official_pre")

    @property
    def scales_confirmed_compatible(self):
        return SCALES_CONFIRMED_COMPATIBLE
