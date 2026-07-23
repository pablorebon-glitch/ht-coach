from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import uuid4

from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.order import Order
from models.player import Player
from models.position import Position
from models.side import Side

from engine.hattrick_ratings.calibration.metrics import build_report
from engine.hattrick_ratings.calibration.models import (
    CalibrationObservation,
    CalibrationRecordStatus,
    CalibrationSource,
    DataQualityStatus,
    LineupSnapshot,
    MatchContextSnapshot,
    ObservationConfidence,
    OfficialSectorRatings,
    PlayerMatchSnapshot,
    RealMatchCalibrationRecord,
    parse_record_date,
)
from engine.hattrick_ratings.calibration.quality import data_quality, validate_record
from engine.hattrick_ratings.calibration.rating_input import parse_official_rating
from engine.hattrick_ratings.midfield.calculator import MidfieldRatingCalculator
from engine.hattrick_ratings.midfield.models import (
    MatchPeriod,
    MidfieldRatingContext,
    MidfieldRatingInput,
    TeamAttitude,
)
from engine.rating_validation.fixture import (
    OfficialHattrickRatings,
    PredictedRatings,
    RatingValidationFixture,
)


class RealMatchCalibrationService:
    def __init__(self, repository, calculator=None, today_provider=None):
        self._repository = repository
        self._calculator = calculator or MidfieldRatingCalculator()
        self._today_provider = today_provider or date.today

    def list_records(self):
        return self._repository.load_records()

    def load_record(self, record_id):
        for record in self.list_records():
            if record.record_id == record_id:
                return record
        raise ValueError(f"calibration record not found: {record_id}")

    def create_draft_from_current_match(
        self,
        lineup,
        formation,
        match_date,
        source=CalibrationSource.CURRENT_MATCH,
        **metadata,
    ):
        record = RealMatchCalibrationRecord(
            record_id=metadata.get("record_id") or str(uuid4()),
            match_id=metadata.get("match_id", ""),
            match_date=str(match_date),
            competition_type=metadata.get("competition_type", ""),
            opponent_name=metadata.get("opponent_name", ""),
            venue=metadata.get("venue", ""),
            formation=formation,
            lineup_snapshot=snapshot_lineup(lineup, formation, source),
            match_context=metadata.get("match_context", MatchContextSnapshot()),
            source=source,
            notes=metadata.get("notes", ""),
            played=bool(metadata.get("played", False)),
            synthetic=bool(metadata.get("synthetic", False)),
        )
        self._upsert(record)
        return record

    def create_draft_from_current_squad(self, *args, **kwargs):
        return self.create_draft_from_current_match(
            *args,
            source=CalibrationSource.CURRENT_SQUAD,
            **kwargs,
        )

    def update_record(self, record):
        self._upsert(record.with_updates())
        return self.load_record(record.record_id)

    def delete_record(self, record_id):
        records = [record for record in self.list_records() if record.record_id != record_id]
        self._repository.save_records(records)

    def archive_record(self, record_id):
        record = self.load_record(record_id)
        archived = record.with_updates(record_status=CalibrationRecordStatus.ARCHIVED)
        self._upsert(archived)
        return archived

    def validate_record(self, record):
        issues = validate_record(record, self._today_provider())
        quality, reasons = data_quality(record, issues)
        return issues, quality, reasons

    def finalize_record(self, record_id):
        record = self.load_record(record_id)
        issues, _quality, _reasons = self.validate_record(record)
        blocking = [issue for issue in issues if issue.blocking]
        if blocking:
            invalid = record.with_updates(record_status=CalibrationRecordStatus.INVALID)
            self._upsert(invalid)
            raise ValueError(", ".join(issue.code for issue in blocking))
        observation = self.generate_observation(record)
        observations = dict(record.observations_by_model_version)
        observations[observation.model_version] = observation
        finalized = record.with_updates(
            record_status=CalibrationRecordStatus.COMPLETE,
            observations_by_model_version=observations,
        )
        self._upsert(finalized)
        return finalized

    def generate_observation(self, record):
        prediction = self._calculator.predict(
            MidfieldRatingInput(
                lineup=lineup_from_snapshot(record.lineup_snapshot),
                formation=record.formation,
                context=context_from_record(record),
            )
        )
        official = record.official_ratings.midfield
        if official is None:
            raise ValueError("missing_official_midfield_rating")
        signed_error = prediction.rating.decimal - official.decimal
        absolute_error = abs(signed_error)
        existing = record.observations_by_model_version.get(prediction.model_version)
        return CalibrationObservation(
            observation_id=(
                existing.observation_id
                if existing is not None
                else f"{record.record_id}:{prediction.model_version}"
            ),
            record_id=record.record_id,
            model_version=prediction.model_version,
            predicted_midfield=prediction.rating,
            official_midfield=official,
            signed_error=signed_error,
            absolute_error=absolute_error,
            exact_match=signed_error == Decimal("0"),
            within_0_25=absolute_error <= Decimal("0.25"),
            within_0_50=absolute_error <= Decimal("0.50"),
            confidence=ObservationConfidence(prediction.confidence.value),
            warnings=prediction.breakdown.warning_codes,
            created_at=existing.created_at if existing is not None else "",
        )

    def recalculate_dataset(self, model_version="midfield-v1"):
        records = []
        for record in self.list_records():
            if record.record_status != CalibrationRecordStatus.COMPLETE:
                records.append(record)
                continue
            observation = self.generate_observation(record)
            if observation.model_version != model_version:
                records.append(record)
                continue
            observations = dict(record.observations_by_model_version)
            observations[model_version] = observation
            records.append(record.with_updates(observations_by_model_version=observations))
        self._repository.save_records(records)
        return build_report(records, model_version)

    def report(self, model_version="midfield-v1"):
        return build_report(self.list_records(), model_version)

    def export_validation_dataset(self, model_version="midfield-v1"):
        return {
            "fixtures": [
                fixture_from_record(record, model_version).to_dict()
                for record in self.list_records()
                if (
                    record.record_status == CalibrationRecordStatus.COMPLETE
                    and model_version in record.observations_by_model_version
                )
            ]
        }

    def import_validation_dataset(self, payload):
        fixtures = payload.get("fixtures", []) if isinstance(payload, dict) else payload
        existing = {record.record_id: record for record in self.list_records()}
        imported = 0
        skipped = []
        records = list(existing.values())
        for fixture in fixtures:
            source_id = fixture.get("additional_context", {}).get("source_record_id")
            if not source_id:
                skipped.append("missing_source_record_id")
                continue
            if source_id in existing:
                skipped.append(source_id)
                continue
            try:
                records.append(record_from_fixture(fixture))
                imported += 1
            except (KeyError, TypeError, ValueError):
                skipped.append(source_id)
        self._repository.save_records(records)
        return {"imported": imported, "skipped": tuple(skipped)}

    def _upsert(self, record):
        records = list(self.list_records())
        existing_ids = [item.record_id for item in records]
        if record.record_id in existing_ids:
            records[existing_ids.index(record.record_id)] = record
        else:
            records.append(record)
        if len({item.record_id for item in records}) != len(records):
            raise ValueError("duplicate_record_id")
        self._repository.save_records(records)


def snapshot_lineup(lineup, formation, source=CalibrationSource.CURRENT_MATCH):
    players = lineup.players if isinstance(lineup, Lineup) else list(lineup)
    source_value = source.value if isinstance(source, CalibrationSource) else str(source)
    return LineupSnapshot(
        formation=formation,
        source=source,
        starters=tuple(
            PlayerMatchSnapshot.from_lineup_player(
                item,
                f"starter_{index + 1}",
                source_value,
            )
            for index, item in enumerate(players)
        ),
    )


def lineup_from_snapshot(snapshot):
    if snapshot is None:
        return Lineup()
    return Lineup(
        [
            LineupPlayer(
                player=Player(
                    name=item.player_name,
                    age=0,
                    days=0,
                    speciality=item.specialty,
                    form=item.form,
                    stamina=item.stamina,
                    goalkeeper=item.goalkeeping,
                    defending=item.defending,
                    playmaking=item.playmaking,
                    winger=item.winger,
                    passing=item.passing,
                    scoring=item.scoring,
                    set_pieces=item.set_pieces,
                    experience=item.experience,
                    leadership=0,
                    tsi=0,
                    salary=0,
                ),
                position=Position(item.position_group),
                side=Side(item.side or "CENTER"),
                order=Order(item.order or "Normal"),
                order_side=Side(item.order_side) if item.order_side else None,
            )
            for item in snapshot.starters
        ]
    )


def context_from_record(record):
    context = record.match_context
    return MidfieldRatingContext(
        team_spirit=context.team_spirit,
        attitude=context.team_attitude or TeamAttitude.NORMAL.value,
        period=context.match_period or MatchPeriod.START.value,
        coach=context.coach_type or context.coach_leadership,
    )


def fixture_from_record(record, model_version):
    observation = record.observations_by_model_version[model_version]
    return RatingValidationFixture(
        fixture_name=f"calibration_{record.record_id}",
        match_id=record.match_id,
        team_name="",
        formation=record.formation,
        official_hattrick_ratings=OfficialHattrickRatings(
            midfield=float(record.official_ratings.midfield.decimal)
        ),
        predicted_ratings=PredictedRatings(
            midfield=float(observation.predicted_midfield.decimal),
            provider=model_version,
        ),
        notes=record.notes,
        additional_context={
            "source_record_id": record.record_id,
            "lineup_players": [
                _fixture_player_from_snapshot(item)
                for item in (record.lineup_snapshot.starters if record.lineup_snapshot else ())
            ],
            "midfield_context": record.match_context.to_dict(),
            "source": record.source.value,
            "synthetic": record.synthetic,
        },
    )


def record_from_fixture(fixture):
    official = fixture.get("official_hattrick_ratings", {})
    context = fixture.get("additional_context", {})
    record = RealMatchCalibrationRecord(
        record_id=context["source_record_id"],
        match_id=fixture.get("match_id", ""),
        match_date=context.get("match_date", date.today().isoformat()),
        formation=fixture.get("formation", ""),
        lineup_snapshot=LineupSnapshot.from_dict(
            {
                "formation": fixture.get("formation", ""),
                "source": context.get("source", CalibrationSource.IMPORTED.value),
                "starters": [
                    _snapshot_from_fixture_player(item)
                    for item in context.get("lineup_players", ())
                ],
            }
        ),
        match_context=MatchContextSnapshot.from_dict(context.get("midfield_context")),
        official_ratings=OfficialSectorRatings(
            midfield=parse_official_rating(official.get("midfield"))
        ),
        notes=fixture.get("notes", ""),
        source=CalibrationSource.IMPORTED,
        played=True,
    )
    return record


def _fixture_player_from_snapshot(item):
    return {
        "name": item.player_name,
        "position": item.position_group,
        "side": item.side,
        "order": item.order,
        "order_side": item.order_side,
        "playmaking": item.playmaking,
        "winger": item.winger,
        "passing": item.passing,
        "defending": item.defending,
        "scoring": item.scoring,
        "goalkeeper": item.goalkeeping,
        "set_pieces": item.set_pieces,
        "form": item.form,
        "stamina": item.stamina,
        "experience": item.experience,
        "speciality": item.specialty,
    }


def _snapshot_from_fixture_player(item):
    return {
        "player_id": item.get("player_id") or item.get("name", ""),
        "player_name": item.get("name", ""),
        "slot": item.get("slot", ""),
        "position_group": item.get("position", "INNER_MIDFIELDER"),
        "side": item.get("side", "CENTER"),
        "order": item.get("order", "Normal"),
        "order_side": item.get("order_side", ""),
        "playmaking": item.get("playmaking"),
        "winger": item.get("winger"),
        "passing": item.get("passing"),
        "defending": item.get("defending"),
        "scoring": item.get("scoring"),
        "goalkeeping": item.get("goalkeeper"),
        "set_pieces": item.get("set_pieces"),
        "form": item.get("form"),
        "stamina": item.get("stamina"),
        "experience": item.get("experience"),
        "specialty": item.get("speciality", ""),
        "snapshot_source": "imported",
        "missing_fields": [],
    }
