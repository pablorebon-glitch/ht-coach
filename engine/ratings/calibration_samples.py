from __future__ import annotations

from dataclasses import dataclass

from models.rating_scale import CalibrationConfidence


PRIMARY_PRE = "official_pre"
SECONDARY_POST = "official_post"

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
    formation: str = ""
    tactic: str = ""
    orders_provenance: str = ""
    capture_timestamp: str = ""
    confidence: CalibrationConfidence = CalibrationConfidence.LOW

    def to_dict(self):
        return {
            "match_record_id": self.match_record_id,
            "sector": self.sector,
            "internal_value": self.internal_value,
            "official_value": self.official_value,
            "source": self.source,
            "formation": self.formation,
            "tactic": self.tactic,
            "orders_provenance": self.orders_provenance,
            "capture_timestamp": self.capture_timestamp,
            "confidence": self.confidence.value,
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
                CalibrationConfidence.MEDIUM,
            )
        )
        samples.extend(
            _samples_from_snapshot(
                record,
                predicted,
                getattr(record, "official_post", None),
                SECONDARY_POST,
                CalibrationConfidence.LOW,
            )
        )
    return tuple(samples)


def _samples_from_snapshot(record, predicted, snapshot, source, confidence):
    if snapshot is None or getattr(snapshot, "ratings", None) is None:
        return ()
    official = snapshot.ratings
    result = []
    for sector, official_sector in SECTOR_MAP.items():
        internal_value = getattr(predicted, sector, None)
        official_value = getattr(official, official_sector, None)
        if internal_value is None or official_value is None:
            continue
        result.append(
            RatingCalibrationSample(
                match_record_id=(
                    getattr(record, "snapshot_id", "")
                    or getattr(record, "record_id", "")
                    or getattr(record, "match_id", "")
                ),
                sector=sector,
                internal_value=float(internal_value),
                official_value=float(official_value),
                source=source,
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
                capture_timestamp=getattr(snapshot, "captured_at", ""),
                confidence=confidence,
            )
        )
    return tuple(result)
