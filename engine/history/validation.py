from __future__ import annotations

from dataclasses import dataclass

from engine.history.enums import SnapshotStage
from engine.history.schema import SCHEMA_VERSION
from models.order import Order
from models.position import Position
from models.side import Side


@dataclass(frozen=True)
class HistoricalValidationError:
    field: str
    message: str


def validate_snapshot(snapshot, allow_played_without_official=False):
    errors = []
    if not snapshot.snapshot_id:
        errors.append(HistoricalValidationError("snapshot_id", "snapshot ID is required"))
    if snapshot.schema_version != SCHEMA_VERSION:
        errors.append(HistoricalValidationError("schema_version", "unsupported schema version"))
    _validate_probabilities(snapshot, errors)
    _validate_lineup(snapshot, errors)
    _validate_ratings(snapshot.predictions.ratings, "predictions.ratings", errors)
    if snapshot.official_result is not None:
        _validate_ratings(snapshot.official_result.ratings, "official_result.ratings", errors)
    if (
        snapshot.match_context.snapshot_stage == SnapshotStage.PLAYED
        and not allow_played_without_official
        and snapshot.official_result is None
    ):
        errors.append(
            HistoricalValidationError(
                "official_result",
                "played snapshots require official result data",
            )
        )
    return tuple(errors)


def ensure_valid_snapshot(snapshot, allow_played_without_official=False):
    errors = validate_snapshot(snapshot, allow_played_without_official)
    if errors:
        raise ValueError("; ".join(f"{error.field}: {error.message}" for error in errors))
    return snapshot


def enrich_with_official_result(snapshot, official_result, stage=SnapshotStage.PLAYED):
    if snapshot.match_context.snapshot_stage not in (
        SnapshotStage.PLANNED,
        SnapshotStage.SUBMITTED,
        SnapshotStage.PLAYED,
        SnapshotStage.IMPORTED,
    ):
        raise ValueError("unsupported snapshot stage transition")
    if stage != SnapshotStage.PLAYED:
        raise ValueError("official enrichment must transition to played")
    updated_context = snapshot.match_context.__class__(
        **{
            **snapshot.match_context.to_dict(),
            "snapshot_stage": SnapshotStage.PLAYED.value,
        }
    )
    return snapshot.with_updates(
        match_context=updated_context,
        official_result=official_result,
    )


def _validate_probabilities(snapshot, errors):
    for field_name in ("win_probability", "draw_probability", "loss_probability"):
        value = getattr(snapshot.predictions, field_name)
        if value is not None and not 0 <= value <= 1:
            errors.append(
                HistoricalValidationError(
                    f"predictions.{field_name}",
                    "probability must be between 0 and 1",
                )
            )


def _validate_lineup(snapshot, errors):
    player_ids = [
        entry.player_id
        for entry in snapshot.lineup
        if entry.is_starter and entry.player_id
    ]
    if len(player_ids) != len(set(player_ids)):
        errors.append(HistoricalValidationError("lineup.player_id", "duplicate starter player ID"))
    slots = [
        (entry.position, entry.side, entry.number)
        for entry in snapshot.lineup
        if entry.is_starter
    ]
    if len(slots) != len(set(slots)):
        errors.append(HistoricalValidationError("lineup.slot", "duplicate starting slot assignment"))
    for index, entry in enumerate(snapshot.lineup):
        if not _valid_enum(Position, entry.position):
            errors.append(HistoricalValidationError(f"lineup[{index}].position", "invalid position"))
        if not _valid_enum(Side, entry.side):
            errors.append(HistoricalValidationError(f"lineup[{index}].side", "invalid side"))
        if not _valid_enum(Order, entry.individual_order):
            errors.append(HistoricalValidationError(f"lineup[{index}].individual_order", "invalid order"))
        if entry.order_side and not _valid_enum(Side, entry.order_side):
            errors.append(HistoricalValidationError(f"lineup[{index}].order_side", "invalid order side"))


def _validate_ratings(ratings, prefix, errors):
    if ratings is None:
        return
    for key, value in ratings.to_dict().items():
        if key in {"source", "scale"} or value is None:
            continue
        if float(value) < 0:
            errors.append(HistoricalValidationError(f"{prefix}.{key}", "rating cannot be negative"))


def _valid_enum(enum_type, value):
    raw = getattr(value, "value", value)
    return any(raw in (member.name, member.value) for member in enum_type)
