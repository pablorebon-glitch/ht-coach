from __future__ import annotations

from dataclasses import dataclass

from models.rating_scale import CalibrationConfidence


PRIMARY_PRE = "official_pre"
SECONDARY_POST = "official_post"
OPPONENT_ACTUAL_POST = "opponent_actual_post"

PRE_RATING_PAIR = "PRE_RATING_PAIR"
POST_VALIDATION_PAIR = "POST_VALIDATION_PAIR"
OPPONENT_SCENARIO_PAIR = "OPPONENT_SCENARIO_PAIR"

SECTOR_MAP = {
    "left_defense": "left_defense",
    "central_defense": "central_defense",
    "right_defense": "right_defense",
    "midfield": "midfield",
    "left_attack": "left_attack",
    "central_attack": "central_attack",
    "right_attack": "right_attack",
}


@dataclass(frozen=True)
class RatingCalibrationSample:
    match_record_id: str
    sector: str
    internal_value: float
    official_value: float
    source: str
    sample_type: str = PRE_RATING_PAIR
    sample_id: str = ""
    match_id: str = ""
    formation: str = ""
    tactic: str = ""
    orders_provenance: str = ""
    capture_timestamp: str = ""
    confidence: CalibrationConfidence = CalibrationConfidence.LOW
    calibration_version: str = ""

    def to_dict(self):
        return {
            "match_record_id": self.match_record_id,
            "match_id": self.match_id,
            "sector": self.sector,
            "internal_value": self.internal_value,
            "official_value": self.official_value,
            "source": self.source,
            "sample_type": self.sample_type,
            "sample_id": self.sample_id,
            "formation": self.formation,
            "tactic": self.tactic,
            "orders_provenance": self.orders_provenance,
            "capture_timestamp": self.capture_timestamp,
            "confidence": self.confidence.value,
            "calibration_version": self.calibration_version,
        }


def build_rating_calibration_samples(history):
    samples = []
    for record in history or ():
        predicted = getattr(getattr(record, "predictions", None), "ratings", None)
        if predicted is None:
            continue
        samples.extend(
            _samples_from_snapshot(
                record,
                predicted,
                getattr(record, "official_pre", None),
                PRIMARY_PRE,
                PRE_RATING_PAIR,
                CalibrationConfidence.MEDIUM,
            )
        )
        samples.extend(
            _samples_from_snapshot(
                record,
                predicted,
                getattr(record, "official_post", None),
                SECONDARY_POST,
                POST_VALIDATION_PAIR,
                CalibrationConfidence.LOW,
            )
        )
        opponent_actual = getattr(getattr(record, "official_match_post", None), "opponent_team_post", None)
        expected_opponent = _expected_opponent_ratings(record)
        if opponent_actual is not None and expected_opponent is not None:
            samples.extend(
                _samples_from_ratings(
                    record,
                    expected_opponent,
                    opponent_actual.ratings,
                    OPPONENT_ACTUAL_POST,
                    OPPONENT_SCENARIO_PAIR,
                    CalibrationConfidence.LOW,
                    getattr(getattr(record, "official_match_post", None), "imported_at", ""),
                )
            )
    return tuple(samples)


def _expected_opponent_ratings(record):
    predictions = getattr(record, "predictions", None)
    return (
        getattr(predictions, "opponent_ratings", None)
        or getattr(predictions, "opponent_snapshot", None)
        or getattr(record, "opponent_expected_snapshot", None)
    )


def _samples_from_snapshot(record, predicted, snapshot, source, sample_type, confidence):
    if snapshot is None or getattr(snapshot, "ratings", None) is None:
        return ()
    return _samples_from_ratings(
        record,
        predicted,
        snapshot.ratings,
        source,
        sample_type,
        confidence,
        getattr(snapshot, "captured_at", ""),
    )


def _samples_from_ratings(record, predicted, official, source, sample_type, confidence, timestamp):
    result = []
    match_record_id = (
        getattr(record, "snapshot_id", "")
        or getattr(record, "record_id", "")
        or getattr(record, "match_id", "")
    )
    official_match_id = getattr(getattr(record, "match_context", None), "official_match_id", "")
    for sector, official_sector in SECTOR_MAP.items():
        internal_value = getattr(predicted, sector, None)
        official_value = getattr(official, official_sector, None)
        if internal_value is None or official_value is None:
            continue
        result.append(
            RatingCalibrationSample(
                match_record_id=match_record_id,
                match_id=official_match_id,
                sector=sector,
                internal_value=float(internal_value),
                official_value=float(official_value),
                source=source,
                sample_type=sample_type,
                sample_id=f"{match_record_id}:{sample_type}:{sector}:v1",
                formation=getattr(
                    getattr(record, "tactical_setup", None),
                    "formation",
                    "",
                ),
                tactic=getattr(
                    getattr(record, "tactical_setup", None),
                    "selected_tactic",
                    "",
                ),
                orders_provenance="historical_snapshot_lineup",
                capture_timestamp=timestamp,
                confidence=confidence,
            )
        )
    return tuple(result)
