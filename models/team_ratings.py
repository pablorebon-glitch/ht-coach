from dataclasses import dataclass, replace

from models.rating_scale import (
    RatingProvenance,
    RatingScale,
    RatingSource,
)


@dataclass
class TeamRatings:

    left_defense: float = 0

    central_defense: float = 0

    right_defense: float = 0

    midfield: float = 0

    left_attack: float = 0

    central_attack: float = 0

    right_attack: float = 0

    indirect_defense: float | None = None

    indirect_attack: float | None = None

    rating_scale: RatingScale | str = RatingScale.UNKNOWN

    rating_source: RatingSource | str = RatingSource.UNKNOWN

    provenance: RatingProvenance | None = None

    def __post_init__(self):
        if not isinstance(self.rating_scale, RatingScale):
            try:
                self.rating_scale = RatingScale(str(self.rating_scale))
            except ValueError:
                self.rating_scale = RatingScale.UNKNOWN
        if not isinstance(self.rating_source, RatingSource):
            try:
                self.rating_source = RatingSource(str(self.rating_source))
            except ValueError:
                self.rating_source = RatingSource.UNKNOWN
        if isinstance(self.provenance, dict):
            self.provenance = RatingProvenance(
                source=self.rating_source,
                detail=str(self.provenance.get("detail", "")),
                calibration_version=str(
                    self.provenance.get("calibration_version", "")
                ),
                sample_count=int(self.provenance.get("sample_count", 0) or 0),
            )

    def with_metadata(
        self,
        rating_scale,
        rating_source=None,
        provenance=None
    ):
        return replace(
            self,
            rating_scale=rating_scale,
            rating_source=rating_source or self.rating_source,
            provenance=provenance if provenance is not None else self.provenance
        )

    def without_metadata(self):
        return replace(
            self,
            rating_scale=RatingScale.UNKNOWN,
            rating_source=RatingSource.UNKNOWN,
            provenance=None
        )
