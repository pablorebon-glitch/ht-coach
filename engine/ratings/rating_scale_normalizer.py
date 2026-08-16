from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from models.rating_scale import (
    CalibrationConfidence,
    RatingProvenance,
    RatingScale,
    RatingSource,
)
from models.team_ratings import TeamRatings


CANONICAL_ANALYTICAL_SCALE = RatingScale.HT_CALIBRATED_ESTIMATE
BOOTSTRAP_CALIBRATION_VERSION = "internal-to-ht-bootstrap-v1"
PRE_CALIBRATION_VERSION = "internal-to-ht-pre-linear-v1"

SECTORS = (
    "left_defense",
    "central_defense",
    "right_defense",
    "midfield",
    "left_attack",
    "central_attack",
    "right_attack",
)


@dataclass(frozen=True)
class SectorCalibrationMapping:
    slope: float
    intercept: float = 0.0
    sample_count: int = 0
    mean_absolute_error: float | None = None
    confidence: CalibrationConfidence = CalibrationConfidence.LOW
    derivation: str = ""

    def apply(self, value):
        return max(0.0, self.intercept + self.slope * float(value or 0.0))

    def to_dict(self):
        return {
            "slope": self.slope,
            "intercept": self.intercept,
            "sample_count": self.sample_count,
            "mean_absolute_error": self.mean_absolute_error,
            "confidence": self.confidence.value,
            "derivation": self.derivation,
        }

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            slope=float(data.get("slope", 0.0)),
            intercept=float(data.get("intercept", 0.0)),
            sample_count=int(data.get("sample_count", 0)),
            mean_absolute_error=(
                float(data["mean_absolute_error"])
                if data.get("mean_absolute_error") is not None
                else None
            ),
            confidence=CalibrationConfidence(
                data.get("confidence", CalibrationConfidence.LOW.value)
            ),
            derivation=data.get("derivation", ""),
        )


@dataclass(frozen=True)
class RatingCalibrationModel:
    schema_version: int = 1
    calibration_version: str = BOOTSTRAP_CALIBRATION_VERSION
    created_at: str = ""
    target_scale: RatingScale = RatingScale.HT_CALIBRATED_ESTIMATE
    source_scale: RatingScale = RatingScale.INTERNAL_CONTRIBUTION
    confidence: CalibrationConfidence = CalibrationConfidence.LOW
    sector_mappings: dict[str, SectorCalibrationMapping] = field(
        default_factory=dict
    )
    sample_count: int = 0
    notes: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.created_at:
            object.__setattr__(
                self,
                "created_at",
                datetime.now(timezone.utc).isoformat(),
            )
        if not isinstance(self.target_scale, RatingScale):
            object.__setattr__(
                self,
                "target_scale",
                RatingScale(str(self.target_scale)),
            )
        if not isinstance(self.source_scale, RatingScale):
            object.__setattr__(
                self,
                "source_scale",
                RatingScale(str(self.source_scale)),
            )
        if not isinstance(self.confidence, CalibrationConfidence):
            object.__setattr__(
                self,
                "confidence",
                CalibrationConfidence(str(self.confidence)),
            )

    def mapping_for(self, sector):
        if sector in self.sector_mappings:
            return self.sector_mappings[sector]
        return self.sector_mappings["default"]

    def to_dict(self):
        return {
            "schema_version": self.schema_version,
            "calibration_version": self.calibration_version,
            "created_at": self.created_at,
            "target_scale": self.target_scale.value,
            "source_scale": self.source_scale.value,
            "confidence": self.confidence.value,
            "sample_count": self.sample_count,
            "sector_mappings": {
                sector: mapping.to_dict()
                for sector, mapping in self.sector_mappings.items()
            },
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            calibration_version=data.get(
                "calibration_version",
                BOOTSTRAP_CALIBRATION_VERSION,
            ),
            created_at=data.get("created_at", ""),
            target_scale=RatingScale(
                data.get(
                    "target_scale",
                    RatingScale.HT_CALIBRATED_ESTIMATE.value,
                )
            ),
            source_scale=RatingScale(
                data.get(
                    "source_scale",
                    RatingScale.INTERNAL_CONTRIBUTION.value,
                )
            ),
            confidence=CalibrationConfidence(
                data.get("confidence", CalibrationConfidence.LOW.value)
            ),
            sector_mappings={
                sector: SectorCalibrationMapping.from_dict(mapping)
                for sector, mapping in data.get(
                    "sector_mappings",
                    {},
                ).items()
            },
            sample_count=int(data.get("sample_count", 0)),
            notes=tuple(data.get("notes", ())),
        )


def bootstrap_calibration_model():
    derivation = (
        "Bootstrap v1 derived from the confirmed La Rocha diagnostic "
        "baseline by matching internal sector totals to the official-scale "
        "Candidate B reference used in the scale audit. This is a "
        "low-confidence, replaceable sector mapping until enough paired "
        "Official PRE observations exist."
    )
    ratios = {
        "left_defense": 4.25 / 16.45,
        "central_defense": 5.25 / 28.32,
        "right_defense": 4.50 / 15.89,
        "midfield": 7.75 / 39.68,
        "left_attack": 9.25 / 25.92,
        "central_attack": 12.25 / 39.12,
        "right_attack": 9.00 / 26.56,
        "default": 0.25,
    }
    return RatingCalibrationModel(
        calibration_version=BOOTSTRAP_CALIBRATION_VERSION,
        confidence=CalibrationConfidence.LOW,
        sector_mappings={
            sector: SectorCalibrationMapping(
                slope=ratio,
                intercept=0.0,
                sample_count=1,
                confidence=CalibrationConfidence.LOW,
                derivation=derivation,
            )
            for sector, ratio in ratios.items()
        },
        sample_count=1,
        notes=(
            "Do not treat bootstrap v1 as fully calibrated.",
            "Prefer Official PRE paired observations for future rebuilds.",
        ),
    )


def rebuild_rating_calibration(history, minimum_samples_per_sector=2):
    from engine.ratings.calibration_samples import (
        PRIMARY_PRE,
        build_rating_calibration_samples,
    )

    samples = [
        sample
        for sample in build_rating_calibration_samples(history)
        if sample.source == PRIMARY_PRE
    ]
    grouped = {
        sector: [
            sample
            for sample in samples
            if sample.sector == sector
        ]
        for sector in SECTORS
    }
    if not samples or all(
        len(items) < minimum_samples_per_sector
        for items in grouped.values()
    ):
        return bootstrap_calibration_model()

    bootstrap = bootstrap_calibration_model()
    mappings = {}
    for sector in SECTORS:
        items = grouped[sector]
        if len(items) < minimum_samples_per_sector:
            mappings[sector] = bootstrap.mapping_for(sector)
            continue
        slope, intercept = _linear_fit(
            [item.internal_value for item in items],
            [item.official_value for item in items],
        )
        errors = [
            abs((slope * item.internal_value + intercept) - item.official_value)
            for item in items
        ]
        mappings[sector] = SectorCalibrationMapping(
            slope=slope,
            intercept=intercept,
            sample_count=len(items),
            mean_absolute_error=sum(errors) / len(errors),
            confidence=(
                CalibrationConfidence.MEDIUM
                if len(items) >= 5
                else CalibrationConfidence.LOW
            ),
            derivation="sector-specific linear fit from Official PRE samples",
        )
    mappings["default"] = bootstrap.mapping_for("default")
    sample_count = len(samples)
    confidence = (
        CalibrationConfidence.MEDIUM
        if sample_count >= 35
        else CalibrationConfidence.LOW
    )
    return RatingCalibrationModel(
        calibration_version=PRE_CALIBRATION_VERSION,
        confidence=confidence,
        sector_mappings=mappings,
        sample_count=sample_count,
        notes=(
            "Built only from Official PRE paired observations.",
            "POST observations are intentionally excluded from this fit.",
        ),
    )
@dataclass(frozen=True)
class CalibratedTeamRatings:
    ratings: TeamRatings
    raw_internal_ratings: TeamRatings
    source_scale: RatingScale
    target_scale: RatingScale
    calibration_version: str
    confidence: CalibrationConfidence
    provenance: RatingProvenance

    def to_dict(self):
        return {
            "ratings": ratings_to_dict(self.ratings),
            "raw_internal_ratings": ratings_to_dict(self.raw_internal_ratings),
            "source_scale": self.source_scale.value,
            "target_scale": self.target_scale.value,
            "calibration_version": self.calibration_version,
            "confidence": self.confidence.value,
            "provenance": self.provenance.to_dict(),
        }


class RatingScaleNormalizer:
    def __init__(self, calibration_model=None):
        self._model = calibration_model or bootstrap_calibration_model()

    @property
    def calibration_model(self):
        return self._model

    def normalize_own_ratings(self, ratings, source=RatingSource.LINEUP_ENGINE):
        ratings = as_team_ratings(ratings)
        current_scale = rating_scale_of(ratings)
        if current_scale in {
            RatingScale.HT_OFFICIAL_DECIMAL,
            RatingScale.HT_CALIBRATED_ESTIMATE,
        }:
            return CalibratedTeamRatings(
                ratings=ratings.with_metadata(
                    RatingScale.HT_CALIBRATED_ESTIMATE,
                    RatingSource.CALIBRATED_MODEL,
                    RatingProvenance(
                        source=source,
                        detail="already HT-compatible",
                        calibration_version=self._model.calibration_version,
                        confidence=self._model.confidence,
                        sample_count=self._model.sample_count,
                    ),
                ),
                raw_internal_ratings=ratings,
                source_scale=current_scale,
                target_scale=RatingScale.HT_CALIBRATED_ESTIMATE,
                calibration_version=self._model.calibration_version,
                confidence=self._model.confidence,
                provenance=RatingProvenance(
                    source=source,
                    detail="already HT-compatible",
                    calibration_version=self._model.calibration_version,
                    confidence=self._model.confidence,
                    sample_count=self._model.sample_count,
                ),
            )
        if current_scale not in {
            RatingScale.INTERNAL_CONTRIBUTION,
            RatingScale.UNKNOWN,
        }:
            raise ValueError(f"unsupported_rating_scale:{current_scale.value}")

        values = {
            sector: self._model.mapping_for(sector).apply(
                getattr(ratings, sector, 0.0)
            )
            for sector in SECTORS
        }
        provenance = RatingProvenance(
            source=source,
            detail="internal contribution calibrated to HT-compatible estimate",
            calibration_version=self._model.calibration_version,
            confidence=self._model.confidence,
            sample_count=self._model.sample_count,
            notes=self._model.notes,
        )
        calibrated = TeamRatings(
            **values,
            indirect_defense=getattr(ratings, "indirect_defense", None),
            indirect_attack=getattr(ratings, "indirect_attack", None),
            rating_scale=RatingScale.HT_CALIBRATED_ESTIMATE,
            rating_source=RatingSource.CALIBRATED_MODEL,
            provenance=provenance,
        )
        return CalibratedTeamRatings(
            ratings=calibrated,
            raw_internal_ratings=ratings.with_metadata(
                RatingScale.INTERNAL_CONTRIBUTION,
                source,
            ),
            source_scale=RatingScale.INTERNAL_CONTRIBUTION,
            target_scale=RatingScale.HT_CALIBRATED_ESTIMATE,
            calibration_version=self._model.calibration_version,
            confidence=self._model.confidence,
            provenance=provenance,
        )

    def normalize_opponent_ratings(
        self,
        ratings,
        source=RatingSource.OPPONENT_IMPORT,
    ):
        ratings = as_team_ratings(ratings)
        scale = rating_scale_of(ratings)
        if scale == RatingScale.UNKNOWN:
            scale = RatingScale.HT_OFFICIAL_DECIMAL
        if scale not in {
            RatingScale.HT_OFFICIAL_DECIMAL,
            RatingScale.HT_CALIBRATED_ESTIMATE,
        }:
            raise ValueError(f"opponent_rating_scale_not_comparable:{scale.value}")
        return ratings.with_metadata(
            RatingScale.HT_CALIBRATED_ESTIMATE,
            source,
            RatingProvenance(
                source=source,
                detail="opponent rating treated as HT-compatible input",
                calibration_version=self._model.calibration_version,
                confidence=self._model.confidence,
                sample_count=self._model.sample_count,
            ),
        )

    def normalize_matchup(self, our_ratings, opponent_ratings):
        own = self.normalize_own_ratings(our_ratings)
        opponent = self.normalize_opponent_ratings(opponent_ratings)
        return own, opponent


def rating_scale_of(ratings):
    return _coerce_scale(
        getattr(ratings, "rating_scale", RatingScale.UNKNOWN)
    )


def rating_source_of(ratings):
    value = getattr(ratings, "rating_source", RatingSource.UNKNOWN)
    if isinstance(value, RatingSource):
        return value
    try:
        return RatingSource(str(value))
    except ValueError:
        return RatingSource.UNKNOWN


def validate_compatible_ratings(our_ratings, opponent_ratings):
    our_scale = rating_scale_of(our_ratings)
    opponent_scale = rating_scale_of(opponent_ratings)
    if RatingScale.UNKNOWN in {our_scale, opponent_scale}:
        raise ValueError(
            "rating_scale_missing: analytical ratings must declare scale"
        )
    if our_scale != opponent_scale:
        raise ValueError(
            "rating_scale_mismatch:"
            f"{our_scale.value}!={opponent_scale.value}"
        )
    return True


def ratings_to_dict(ratings):
    return {
        sector: float(getattr(ratings, sector, 0.0) or 0.0)
        for sector in SECTORS
    }


def _linear_fit(xs, ys):
    count = len(xs)
    if count == 0:
        return 0.0, 0.0
    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return mean_y / mean_x if mean_x else 0.0, 0.0
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
    intercept = mean_y - slope * mean_x
    return slope, intercept


def as_team_ratings(ratings):
    if isinstance(ratings, TeamRatings):
        return ratings
    return TeamRatings(
        left_defense=getattr(ratings, "left_defense", 0.0),
        central_defense=getattr(ratings, "central_defense", 0.0),
        right_defense=getattr(ratings, "right_defense", 0.0),
        midfield=getattr(ratings, "midfield", 0.0),
        left_attack=getattr(ratings, "left_attack", 0.0),
        central_attack=getattr(ratings, "central_attack", 0.0),
        right_attack=getattr(ratings, "right_attack", 0.0),
        indirect_defense=getattr(ratings, "indirect_defense", None),
        indirect_attack=getattr(ratings, "indirect_attack", None),
        rating_scale=getattr(
            ratings,
            "rating_scale",
            RatingScale.INTERNAL_CONTRIBUTION,
        ),
        rating_source=getattr(
            ratings,
            "rating_source",
            RatingSource.LINEUP_ENGINE,
        ),
        provenance=getattr(ratings, "provenance", None),
    )


def _coerce_scale(value):
    if isinstance(value, RatingScale):
        return value
    try:
        return RatingScale(str(value))
    except ValueError:
        return RatingScale.UNKNOWN
