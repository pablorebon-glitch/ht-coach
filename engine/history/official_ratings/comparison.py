from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.history.evolution.comparison_engine import REPORTED_SECTORS
from engine.history.evolution.comparison_metrics import absolute_delta


@dataclass(frozen=True)
class SectorRatingComparison:
    sector: str
    predicted_value: float | None = None
    official_pre_value: float | None = None
    official_post_value: float | None = None
    predicted_vs_pre_delta: float | None = None
    pre_vs_post_delta: float | None = None
    predicted_vs_post_delta: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sector": self.sector,
            "predicted_value": self.predicted_value,
            "official_pre_value": self.official_pre_value,
            "official_post_value": self.official_post_value,
            "predicted_vs_pre_delta": self.predicted_vs_pre_delta,
            "pre_vs_post_delta": self.pre_vs_post_delta,
            "predicted_vs_post_delta": self.predicted_vs_post_delta,
        }


@dataclass(frozen=True)
class OfficialRatingComparison:
    """Deterministic, three-way comparison of predicted ratings against
    the official PRE- and POST-match "Copy Ratings" captures. Every
    field is a straight delta between whatever values are actually
    present -- a missing side of the comparison (e.g. no POST captured
    yet) simply leaves those deltas as `None`, never a guess."""

    sectors: tuple[SectorRatingComparison, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"sectors": [sector.to_dict() for sector in self.sectors]}

    def sector(self, name):
        return next((item for item in self.sectors if item.sector == name), None)


def _sector_value(ratings, sector):
    if ratings is None:
        return None
    return getattr(ratings, sector, None)


def compare_official_ratings(
    prediction_ratings=None,
    official_pre=None,
    official_post=None,
) -> OfficialRatingComparison:
    """`prediction_ratings` is a plain `SectorRatings` (from a
    `PredictionSnapshot`); `official_pre` / `official_post` are
    `OfficialRatingSnapshot` instances (or None if not yet captured)."""
    pre_ratings = official_pre.ratings if official_pre else None
    post_ratings = official_post.ratings if official_post else None

    sectors = []
    for sector in REPORTED_SECTORS:
        predicted_value = _sector_value(prediction_ratings, sector)
        pre_value = _sector_value(pre_ratings, sector)
        post_value = _sector_value(post_ratings, sector)
        sectors.append(
            SectorRatingComparison(
                sector=sector,
                predicted_value=predicted_value,
                official_pre_value=pre_value,
                official_post_value=post_value,
                predicted_vs_pre_delta=absolute_delta(predicted_value, pre_value),
                pre_vs_post_delta=absolute_delta(pre_value, post_value),
                predicted_vs_post_delta=absolute_delta(predicted_value, post_value),
            )
        )
    return OfficialRatingComparison(sectors=tuple(sectors))
