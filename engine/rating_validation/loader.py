from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.rating_validation.dataset import RatingValidationDataset
from engine.rating_validation.exceptions import FixtureLoadError, InvalidFixtureError
from engine.rating_validation.fixture import RatingValidationFixture


def load_rating_validation_dataset(path: str | Path) -> RatingValidationDataset:
    fixture_path = Path(path)
    if not fixture_path.exists():
        raise FixtureLoadError(f"fixture path does not exist: {fixture_path}")

    if fixture_path.is_dir():
        fixtures = []
        for json_path in sorted(fixture_path.glob("*.json")):
            fixtures.extend(_fixtures_from_json_file(json_path))
        return RatingValidationDataset.from_fixtures(fixtures)

    if fixture_path.suffix.lower() != ".json":
        raise FixtureLoadError("only JSON validation fixtures are currently supported")
    return RatingValidationDataset.from_fixtures(_fixtures_from_json_file(fixture_path))


def _fixtures_from_json_file(path: Path) -> list[RatingValidationFixture]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FixtureLoadError(f"invalid JSON fixture file: {path}") from exc

    try:
        payloads = _normalize_payload(raw)
        return [RatingValidationFixture.from_dict(payload) for payload in payloads]
    except (TypeError, ValueError) as exc:
        raise InvalidFixtureError(f"invalid validation fixture in {path}: {exc}") from exc


def _normalize_payload(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and isinstance(raw.get("fixtures"), list):
        return raw["fixtures"]
    if isinstance(raw, dict):
        return [raw]
    raise InvalidFixtureError("JSON fixture payload must be an object or list")
