from __future__ import annotations

import json
from pathlib import Path

from engine.hattrick_ratings.calibration.models import (
    RealMatchCalibrationRecord,
    SCHEMA_VERSION,
)


class CalibrationRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load_records(self) -> tuple[RealMatchCalibrationRecord, ...]:
        if not self.path.exists():
            return ()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return ()
        if int(raw.get("schema_version", 0)) > SCHEMA_VERSION:
            return ()
        records = []
        for item in raw.get("records", ()):
            try:
                records.append(RealMatchCalibrationRecord.from_dict(item))
            except (KeyError, TypeError, ValueError):
                continue
        return tuple(records)

    def save_records(self, records) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "records": [record.to_dict() for record in records],
        }
        self.path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
