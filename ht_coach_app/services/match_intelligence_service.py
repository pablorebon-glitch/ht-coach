from __future__ import annotations

from engine.history.official_ratings.comparison import compare_official_ratings
from engine.history.official_ratings.interpretation import (
    generate_conclusions,
    interpret_comparison,
)
from engine.history.official_ratings.summary import summarize_official_rating_comparison
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.core.paths import historical_match_snapshots_path
from ht_coach_app.services.official_rating_formatting import (
    SCALES_CONFIRMED_COMPATIBLE,
    format_hattrick_notation,
    format_official_sector_label,
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

    def available_seasons(self):
        from engine.history.record_navigation import available_seasons

        return available_seasons(self._repository)

    def history_records(self, season_number=None, status=None, competition_type=None):
        from engine.history.record_navigation import list_records

        return list_records(
            self._repository, season_number=season_number,
            status=status, competition_type=competition_type,
        )

    def navigate_history(self, records, current_snapshot_id=None, direction="current"):
        from engine.history.record_navigation import navigate_records

        return navigate_records(records, current_snapshot_id, direction)

    def import_ratings(self, raw_text, slot="pre", confirm_replace=False):
        return self._import_service.import_and_link(
            raw_text, slot=slot, confirm_replace=confirm_replace
        )

    def associate_post_after_match_id_confirmation(
        self,
        pre_snapshot_id,
        raw_text,
        match_id,
        *,
        language="",
        confirm_replace=False,
    ):
        return self._import_service.associate_post_after_match_id_confirmation(
            pre_snapshot_id,
            raw_text,
            match_id,
            language=language,
            confirm_replace=confirm_replace,
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

    def official_pre_post_rows(self, snapshot):
        if snapshot is None:
            return ()
        comparison = compare_official_ratings(
            None, snapshot.official_pre, snapshot.official_post
        )
        rows = []
        for sector in comparison.sectors:
            pre = "?" if sector.official_pre_value is None else f"{sector.official_pre_value:.2f}"
            post = "?" if sector.official_post_value is None else f"{sector.official_post_value:.2f}"
            delta = "-" if sector.pre_vs_post_delta is None else f"{sector.pre_vs_post_delta:.2f}"
            rows.append((format_official_sector_label(sector.sector), pre, post, delta))
        return tuple(rows)

    def interpreted_pre_post_rows(self, snapshot):
        """HF-02.2, Part 5: one row per sector with the exact PRE/POST
        values, the signed difference, and a deterministic
        direction/magnitude classification -- never just raw numbers.
        Returns (sector_label, pre_text, post_text, delta_text,
        direction, magnitude) tuples; `direction`/`magnitude` are the
        stable keys from `interpretation.py`, for the caller to
        localize."""
        if snapshot is None:
            return ()
        comparison = compare_official_ratings(
            None, snapshot.official_pre, snapshot.official_post
        )
        interpreted = interpret_comparison(comparison)
        rows = []
        for item in interpreted:
            pre = "?" if item.pre_value is None else f"{item.pre_value:.2f}"
            post = "?" if item.post_value is None else f"{item.post_value:.2f}"
            delta = "-" if item.delta is None else f"{item.delta:+.2f}"
            rows.append(
                (
                    format_official_sector_label(item.sector),
                    pre,
                    post,
                    delta,
                    item.direction,
                    item.magnitude,
                )
            )
        return tuple(rows)

    def pre_post_conclusions(self, snapshot):
        """HF-02.2, Part 6: deterministic, evidence-only conclusions
        from the PRE/POST comparison. Returns a tuple of
        `interpretation.Conclusion` (stable key + params) for the
        caller to localize -- never invents a cause."""
        if snapshot is None:
            return ()
        comparison = compare_official_ratings(
            None, snapshot.official_pre, snapshot.official_post
        )
        interpreted = interpret_comparison(comparison)
        conclusions = generate_conclusions(interpreted)
        return tuple(self._localize_conclusion_sectors(c) for c in conclusions)

    @staticmethod
    def _localize_conclusion_sectors(conclusion):
        from engine.history.official_ratings.interpretation import Conclusion

        params = dict(conclusion.params)
        if "sector" in params:
            params["sector"] = format_official_sector_label(params["sector"])
        if "sectors" in params:
            params["sectors"] = ", ".join(
                format_official_sector_label(name.strip())
                for name in params["sectors"].split(",")
            )
        return Conclusion(conclusion.key, params)

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
