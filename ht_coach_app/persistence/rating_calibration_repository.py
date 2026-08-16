from __future__ import annotations

import json
from pathlib import Path

from engine.ratings.rating_scale_normalizer import (
    RatingCalibrationModel,
    bootstrap_calibration_model,
)
from ht_coach_app.core.paths import application_paths


class RatingCalibrationRepository:
    def __init__(self, path=None):
        self._path = Path(path) if path is not None else (
            application_paths().data_dir / "rating_calibration.json"
        )

    @property
    def path(self):
        return self._path

    def load(self):
        if not self._path.exists():
            return bootstrap_calibration_model()
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return bootstrap_calibration_model()
        return RatingCalibrationModel.from_dict(data)

    def save(self, model):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(model.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return model
