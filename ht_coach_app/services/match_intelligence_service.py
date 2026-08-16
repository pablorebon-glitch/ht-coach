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
from ht_coach_app.services.official_rating_service import (
    OfficialRatingMatchIdMismatch,
)


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
            if (
                snapshot.official_pre is not None
                or snapshot.official_post is not None
                or snapshot.retrospective_pre is not None
            )
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

    def import_ratings(
        self,
        raw_text,
        slot="pre",
        confirm_replace=False,
        active_snapshot_id=None,
    ):
        if active_snapshot_id and slot == "post":
            snapshot = self._repository.get(active_snapshot_id)
            if snapshot is not None and snapshot.official_pre is not None:
                parsed = self._import_service._parse_and_validate(raw_text, "", slot)
                pre_match_id = snapshot.official_pre.hattrick_match_id
                post_match_id = parsed.hattrick_match_id
                if pre_match_id and post_match_id and pre_match_id != post_match_id:
                    raise OfficialRatingMatchIdMismatch(
                        pre_match_id,
                        post_match_id,
                        active_snapshot_id,
                        raw_text,
                    )
            return self._import_service.import_ratings(
                active_snapshot_id,
                raw_text,
                slot=slot,
                confirm_replace=confirm_replace,
            )
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

    @staticmethod
    def effective_pre(snapshot):
        if snapshot is None:
            return None
        return snapshot.official_pre or snapshot.retrospective_pre

    def prediction_comparison_rows(self, snapshot):
        """(sector, predicted, official_pre, delta_or_none) rows,
        comparing HT Coach's own prediction against official PRE.
        `delta_or_none` is always None today -- see
        `official_rating_formatting.SCALES_CONFIRMED_COMPATIBLE`."""
        if snapshot is None:
            return ()
        prediction_ratings = snapshot.predictions.ratings if snapshot.predictions else None
        comparison = compare_official_ratings(
            prediction_ratings, self.effective_pre(snapshot), snapshot.official_post
        )
        return format_prediction_vs_official_comparison(comparison)

    def official_pre_post_rows(self, snapshot):
        if snapshot is None:
            return ()
        comparison = compare_official_ratings(
            None, self.effective_pre(snapshot), snapshot.official_post
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
            None, self.effective_pre(snapshot), snapshot.official_post
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
            None, self.effective_pre(snapshot), snapshot.official_post
        )
        interpreted = interpret_comparison(comparison)
        conclusions = generate_conclusions(interpreted)
        return tuple(self._localize_conclusion_sectors(c) for c in conclusions)

    def post_source_indicator(self, snapshot):
        match_post = getattr(snapshot, "official_match_post", None) if snapshot else None
        if match_post is None and getattr(snapshot, "official_post", None) is not None:
            return "Solo Hit'em up"
        if match_post is None:
            return ""
        return (
            "Completo del partido"
            if getattr(match_post, "opponent_team_post", None) is not None
            else "Solo Hit'em up"
        )

    def opponent_actual_summary(self, snapshot):
        match_post = getattr(snapshot, "official_match_post", None) if snapshot else None
        opponent = getattr(match_post, "opponent_team_post", None)
        if opponent is None:
            return ""
        lines = [
            opponent.team_name,
            f"MID       {_fmt(opponent.ratings.midfield)}",
            (
                "DEF   "
                f"{_fmt(opponent.ratings.right_defense)} / "
                f"{_fmt(opponent.ratings.central_defense)} / "
                f"{_fmt(opponent.ratings.left_defense)}"
            ),
            (
                "ATT   "
                f"{_fmt(opponent.ratings.right_attack)} / "
                f"{_fmt(opponent.ratings.central_attack)} / "
                f"{_fmt(opponent.ratings.left_attack)}"
            ),
        ]
        if opponent.tactic.label:
            lines.append(f"Táctica: {opponent.tactic.label}")
        if opponent.tactic_level is not None:
            lines.append(f"Nivel: {opponent.tactic_level:g}")
        if opponent.playing_style:
            lines.append(f"Estilo: {opponent.playing_style}")
        if opponent.score is not None:
            lines.append(f"Resultado rival: {opponent.score}")
        return "\n".join(lines)

    def scenario_drift_summary(self, snapshot):
        match_post = getattr(snapshot, "official_match_post", None) if snapshot else None
        opponent = getattr(match_post, "opponent_team_post", None)
        if opponent is None:
            return ""
        expected = _expected_opponent_snapshot(snapshot)
        if expected is None:
            return "Sin escenario previo para comparar."
        from engine.history.official_ratings.scenario_drift import (
            compare_expected_opponent_to_actual_post,
        )

        drift = compare_expected_opponent_to_actual_post(expected, opponent)
        lines = [
            f"Escenario rival: {drift.overall_magnitude}",
            drift.explanation,
        ]
        comparable = [item for item in drift.sectors if item.delta is not None]
        for item in comparable[:3]:
            lines.append(
                f"{format_official_sector_label(item.sector)}: "
                f"{item.expected:.2f} -> {item.actual:.2f} ({item.delta:+.2f})"
            )
        if drift.tactic_changed is True:
            lines.append("La táctica real difirió del escenario esperado.")
        return "\n".join(lines)

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
        if snapshot is None or self.effective_pre(snapshot) is None:
            return None
        prediction_ratings = snapshot.predictions.ratings if snapshot.predictions else None
        comparison = compare_official_ratings(
            prediction_ratings, self.effective_pre(snapshot), snapshot.official_post
        )
        return summarize_official_rating_comparison(comparison, "official_pre")

    @property
    def scales_confirmed_compatible(self):
        return SCALES_CONFIRMED_COMPATIBLE


def _fmt(value):
    return "?" if value is None else f"{float(value):.2f}"


def _expected_opponent_snapshot(snapshot):
    predictions = getattr(snapshot, "predictions", None)
    return (
        getattr(predictions, "opponent_ratings", None)
        or getattr(predictions, "opponent_snapshot", None)
        or getattr(snapshot, "opponent_expected_snapshot", None)
    )
