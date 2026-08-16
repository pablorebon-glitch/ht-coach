from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RatingScale(str, Enum):
    INTERNAL_CONTRIBUTION = "internal_contribution"
    HT_OFFICIAL_DECIMAL = "ht_official_decimal"
    HT_CALIBRATED_ESTIMATE = "ht_calibrated_estimate"
    UNKNOWN = "unknown"


class RatingSource(str, Enum):
    LINEUP_ENGINE = "lineup_engine"
    OFFICIAL_PRE = "official_pre"
    OFFICIAL_POST = "official_post"
    OPPONENT_IMPORT = "opponent_import"
    CALIBRATED_MODEL = "calibrated_model"
    MANUAL_INPUT = "manual_input"
    TEST_FIXTURE = "test_fixture"
    UNKNOWN = "unknown"


class CalibrationConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCALIBRATED = "uncalibrated"


@dataclass(frozen=True)
class RatingProvenance:
    source: RatingSource = RatingSource.UNKNOWN
    detail: str = ""
    calibration_version: str = ""
    confidence: CalibrationConfidence = CalibrationConfidence.UNCALIBRATED
    sample_count: int = 0
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self):
        return {
            "source": self.source.value,
            "detail": self.detail,
            "calibration_version": self.calibration_version,
            "confidence": self.confidence.value,
            "sample_count": self.sample_count,
            "notes": list(self.notes),
        }
