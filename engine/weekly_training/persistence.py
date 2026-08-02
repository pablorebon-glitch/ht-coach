import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from engine.weekly_training.models import (
    PLAYMAKING,
    CompetitionType,
    ExposureConfidence,
    MatchRole,
    MatchStatus,
    TrainingExposure,
    TrainingPriority,
    TrainingPriorityRecord,
    TrainingWeek,
    TrainingWeekStatus,
    WeeklyMatchLineupEntry,
    WeeklyMatchRecord,
)
from engine.weekly_training.training_week import active_training_week, rollover_week


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class WeeklyTrainingState:
    schema_version: int = SCHEMA_VERSION
    active_training_type: str = PLAYMAKING
    active_week: TrainingWeek | None = None
    priorities: dict[str, TrainingPriorityRecord] = field(default_factory=dict)
    match_records: tuple[WeeklyMatchRecord, ...] = ()
    archived_weeks: tuple[TrainingWeek, ...] = ()
    diagnostics: tuple[str, ...] = ()


class WeeklyTrainingRepository:
    def __init__(self, storage_path):
        self.storage_path = storage_path

    def load(self):
        if not self.storage_path.exists():
            return WeeklyTrainingState(
                active_week=active_training_week(),
            )
        try:
            with open(self.storage_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return WeeklyTrainingState(
                active_week=active_training_week(),
                diagnostics=("planner_data_unreadable",),
            )

        try:
            state = WeeklyTrainingState(
                schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
                active_training_type=str(data.get("active_training_type", PLAYMAKING)),
                active_week=_week_from_dict(data.get("active_week")),
                priorities={
                    player_id: _priority_from_dict(record)
                    for player_id, record in dict(data.get("priorities", {})).items()
                },
                match_records=tuple(
                    _match_from_dict(record)
                    for record in data.get("match_records", [])
                ),
                archived_weeks=tuple(
                    week
                    for week in (
                        _week_from_dict(record)
                        for record in data.get("archived_weeks", [])
                    )
                    if week is not None
                ),
            )
        except (TypeError, ValueError, KeyError):
            return WeeklyTrainingState(
                active_week=active_training_week(),
                diagnostics=("planner_data_malformed",),
            )
        if state.active_week is None:
            return WeeklyTrainingState(
                active_training_type=state.active_training_type,
                active_week=active_training_week(training_type=state.active_training_type),
                priorities=state.priorities,
                match_records=state.match_records,
                archived_weeks=state.archived_weeks,
                diagnostics=("planner_active_week_missing",),
            )
        return state

    def save(self, state):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(_state_to_dict(state), file, indent=2, ensure_ascii=False)
        return state

    def save_priority(self, state, record):
        priorities = dict(state.priorities)
        priorities[record.player_id] = record
        return self.save(
            WeeklyTrainingState(
                active_training_type=state.active_training_type,
                active_week=state.active_week,
                priorities=priorities,
                match_records=state.match_records,
                archived_weeks=state.archived_weeks,
            )
        )

    def add_match_record(self, state, record):
        if any(existing.match_id == record.match_id for existing in state.match_records):
            raise ValueError("duplicate_match_id")
        return self.save(
            WeeklyTrainingState(
                active_training_type=state.active_training_type,
                active_week=state.active_week,
                priorities=state.priorities,
                match_records=state.match_records + (record,),
                archived_weeks=state.archived_weeks,
            )
        )

    def replace_match_record(self, state, record):
        records = tuple(
            record if existing.match_id == record.match_id else existing
            for existing in state.match_records
        )
        if records == state.match_records and not any(
            existing.match_id == record.match_id for existing in state.match_records
        ):
            records = state.match_records + (record,)
        return self.save(
            WeeklyTrainingState(
                active_training_type=state.active_training_type,
                active_week=state.active_week,
                priorities=state.priorities,
                match_records=records,
                archived_weeks=state.archived_weeks,
            )
        )

    def delete_match_record(self, state, match_id):
        return self.save(
            WeeklyTrainingState(
                active_training_type=state.active_training_type,
                active_week=state.active_week,
                priorities=state.priorities,
                match_records=tuple(
                    record
                    for record in state.match_records
                    if record.match_id != match_id
                ),
                archived_weeks=state.archived_weeks,
            )
        )

    def rollover(self, state, today=None):
        archived, active = rollover_week(state.active_week, today)
        archives = state.archived_weeks + ((archived,) if archived is not None else ())
        return self.save(
            WeeklyTrainingState(
                active_training_type=state.active_training_type,
                active_week=active,
                priorities=state.priorities,
                match_records=state.match_records,
                archived_weeks=archives,
            )
        )


def _state_to_dict(state):
    return {
        "schema_version": SCHEMA_VERSION,
        "active_training_type": state.active_training_type,
        "active_week": _week_to_dict(state.active_week),
        "priorities": {
            key: _priority_to_dict(value)
            for key, value in state.priorities.items()
        },
        "match_records": [_match_to_dict(record) for record in state.match_records],
        "archived_weeks": [_week_to_dict(week) for week in state.archived_weeks],
    }


def _week_to_dict(week):
    if week is None:
        return None
    return {
        "week_id": week.week_id,
        "start_date": week.start_date.isoformat(),
        "end_date": week.end_date.isoformat(),
        "training_update_date": week.training_update_date.isoformat(),
        "first_match_date": week.first_match_date.isoformat(),
        "second_match_date": week.second_match_date.isoformat(),
        "active_training_type": week.active_training_type,
        "status": week.status.value,
    }


def _week_from_dict(data):
    if not data:
        return None
    return TrainingWeek(
        week_id=str(data["week_id"]),
        start_date=date.fromisoformat(data["start_date"]),
        end_date=date.fromisoformat(data["end_date"]),
        training_update_date=date.fromisoformat(data["training_update_date"]),
        first_match_date=date.fromisoformat(data["first_match_date"]),
        second_match_date=date.fromisoformat(data["second_match_date"]),
        active_training_type=str(data.get("active_training_type", PLAYMAKING)),
        status=TrainingWeekStatus(str(data.get("status", TrainingWeekStatus.PLANNING.value))),
    )


def _priority_to_dict(record):
    return {
        "player_id": record.player_id,
        "player_name": record.player_name,
        "priority": record.priority.value,
        "notes": record.notes,
    }


def _priority_from_dict(data):
    return TrainingPriorityRecord(
        player_id=str(data["player_id"]),
        player_name=str(data.get("player_name", "")),
        priority=TrainingPriority(str(data.get("priority", TrainingPriority.NO_PRIORITY.value))),
        notes=str(data.get("notes", "")),
    )


def _entry_to_dict(entry):
    return {
        "player_id": entry.player_id,
        "player_name": entry.player_name,
        "slot_id": entry.slot_id,
        "position": entry.position,
        "side": entry.side,
        "order": entry.order,
        "order_side": entry.order_side,
        "played_minutes": str(entry.played_minutes),
    }


def _entry_from_dict(data):
    return WeeklyMatchLineupEntry(
        player_id=str(data["player_id"]),
        player_name=str(data.get("player_name", "")),
        slot_id=str(data.get("slot_id", "")),
        position=str(data.get("position", "")),
        side=str(data.get("side", "")),
        order=str(data.get("order", "Normal")),
        order_side=str(data.get("order_side", "")),
        played_minutes=Decimal(str(data.get("played_minutes", "90"))),
    )


def _exposure_to_dict(exposure):
    return {
        "player_id": exposure.player_id,
        "match_id": exposure.match_id,
        "position_group": exposure.position_group,
        "played_minutes": str(exposure.played_minutes),
        "training_factor": str(exposure.training_factor),
        "effective_training_minutes": str(exposure.effective_training_minutes),
        "source": exposure.source,
        "confidence": exposure.confidence.value,
    }


def _exposure_from_dict(data):
    return TrainingExposure(
        player_id=str(data["player_id"]),
        match_id=str(data["match_id"]),
        position_group=str(data.get("position_group", "")),
        played_minutes=Decimal(str(data.get("played_minutes", "0"))),
        training_factor=Decimal(str(data.get("training_factor", "0"))),
        effective_training_minutes=Decimal(str(data.get("effective_training_minutes", "0"))),
        source=str(data.get("source", "")),
        confidence=ExposureConfidence(str(data.get("confidence", ExposureConfidence.UNKNOWN.value))),
    )


def _match_to_dict(record):
    return {
        "match_id": record.match_id,
        "match_date": record.match_date.isoformat(),
        "match_role": record.match_role.value,
        "opponent_name": record.opponent_name,
        "competition_type": record.competition_type.value,
        "formation": record.formation,
        "lineup": [_entry_to_dict(entry) for entry in record.lineup],
        "planned_or_played": record.planned_or_played.value,
        "source": record.source,
        "minutes_known": record.minutes_known,
        "notes": record.notes,
        "training_exposure_entries": [
            _exposure_to_dict(exposure)
            for exposure in record.training_exposure_entries
        ],
        "linked_match_record_id": record.linked_match_record_id,
    }


def _match_from_dict(data):
    return WeeklyMatchRecord(
        match_id=str(data["match_id"]),
        match_date=date.fromisoformat(data["match_date"]),
        match_role=MatchRole(str(data.get("match_role", MatchRole.OTHER.value))),
        opponent_name=str(data.get("opponent_name", "")),
        competition_type=CompetitionType(str(data.get("competition_type", CompetitionType.UNKNOWN.value))),
        formation=str(data.get("formation", "")),
        lineup=tuple(_entry_from_dict(entry) for entry in data.get("lineup", [])),
        planned_or_played=MatchStatus(str(data.get("planned_or_played", MatchStatus.PLANNED.value))),
        source=str(data.get("source", "manual")),
        minutes_known=bool(data.get("minutes_known", False)),
        notes=str(data.get("notes", "")),
        training_exposure_entries=tuple(
            _exposure_from_dict(exposure)
            for exposure in data.get("training_exposure_entries", [])
        ),
        linked_match_record_id=str(data.get("linked_match_record_id", "")),
    )
