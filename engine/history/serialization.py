from __future__ import annotations

import json
from pathlib import Path

from engine.history.models import HistoricalMatchSnapshot
from engine.history.schema import SCHEMA_VERSION


class HistoricalSerializationError(ValueError):
    pass


def snapshot_to_json(snapshot: HistoricalMatchSnapshot) -> str:
    return json.dumps(
        snapshot.to_dict(),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )


def snapshot_from_json(text: str) -> HistoricalMatchSnapshot:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HistoricalSerializationError("corrupt historical snapshot JSON") from exc
    if not isinstance(data, dict):
        raise HistoricalSerializationError("historical snapshot JSON must be an object")
    return HistoricalMatchSnapshot.from_dict(data)


def repository_payload_to_json(snapshots) -> str:
    return json.dumps(
        {
            "schema_version": SCHEMA_VERSION,
            "snapshots": [snapshot.to_dict() for snapshot in snapshots],
        },
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )


def snapshots_from_repository_payload(text: str) -> tuple[HistoricalMatchSnapshot, ...]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HistoricalSerializationError("corrupt historical repository JSON") from exc
    if not isinstance(data, dict):
        raise HistoricalSerializationError("historical repository JSON must be an object")
    if int(data.get("schema_version", 0)) != SCHEMA_VERSION:
        raise HistoricalSerializationError(
            f"unsupported historical repository schema: {data.get('schema_version')}"
        )
    return tuple(
        HistoricalMatchSnapshot.from_dict(item)
        for item in data.get("snapshots", [])
        if isinstance(item, dict)
    )


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(text, encoding="utf-8")
    temp_path.replace(path)
