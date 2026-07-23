from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from engine.hattrick_ratings.models import HattrickRating


SCHEMA_VERSION = 1


class CalibrationRecordStatus(str, Enum):
    DRAFT = "draft"
    COMPLETE = "complete"
    INVALID = "invalid"
    ARCHIVED = "archived"


class CalibrationSource(str, Enum):
    CURRENT_MATCH = "current_match"
    CURRENT_SQUAD = "current_squad"
    WEEKLY_PLANNER = "weekly_planner"
    IMPORTED = "imported"
    SYNTHETIC_TEST = "synthetic_test"


class ObservationConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCALIBRATED = "uncalibrated"


class DataQualityStatus(str, Enum):
    COMPLETE = "complete"
    USABLE_WITH_ASSUMPTIONS = "usable_with_assumptions"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"


@dataclass(frozen=True)
class OfficialSectorRatings:
    midfield: HattrickRating | None = None
    defense_left: HattrickRating | None = None
    defense_center: HattrickRating | None = None
    defense_right: HattrickRating | None = None
    attack_left: HattrickRating | None = None
    attack_center: HattrickRating | None = None
    attack_right: HattrickRating | None = None

    def to_dict(self) -> dict:
        return {
            key: getattr(self, key).to_dict() if getattr(self, key) else None
            for key in (
                "midfield",
                "defense_left",
                "defense_center",
                "defense_right",
                "attack_left",
                "attack_center",
                "attack_right",
            )
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "OfficialSectorRatings":
        data = data or {}
        return cls(
            **{
                key: HattrickRating.from_dict(value) if value else None
                for key, value in data.items()
            }
        )


@dataclass(frozen=True)
class PlayerMatchSnapshot:
    player_id: str
    player_name: str
    slot: str
    position_group: str
    order: str
    side: str = "CENTER"
    order_side: str = ""
    playmaking: int | None = None
    winger: int | None = None
    passing: int | None = None
    defending: int | None = None
    scoring: int | None = None
    goalkeeping: int | None = None
    set_pieces: int | None = None
    form: int | None = None
    stamina: int | None = None
    experience: int | None = None
    specialty: str = ""
    snapshot_source: str = ""
    missing_fields: tuple[str, ...] = ()

    @classmethod
    def from_lineup_player(cls, lineup_player, slot: str, source: str = "current_match"):
        player = lineup_player.player
        fields = {
            "playmaking": getattr(player, "playmaking", None),
            "winger": getattr(player, "winger", None),
            "passing": getattr(player, "passing", None),
            "defending": getattr(player, "defending", None),
            "scoring": getattr(player, "scoring", None),
            "goalkeeping": getattr(player, "goalkeeper", None),
            "set_pieces": getattr(player, "set_pieces", None),
            "form": getattr(player, "form", None),
            "stamina": getattr(player, "stamina", None),
            "experience": getattr(player, "experience", None),
        }
        return cls(
            player_id=str(getattr(player, "player_id", "") or getattr(player, "name", "")),
            player_name=getattr(player, "name", ""),
            slot=slot,
            position_group=getattr(lineup_player.position, "value", str(lineup_player.position)),
            order=getattr(lineup_player.order, "value", str(lineup_player.order)),
            side=getattr(lineup_player.side, "value", str(lineup_player.side)),
            order_side=(
                getattr(lineup_player.order_side, "value", str(lineup_player.order_side))
                if lineup_player.order_side is not None
                else ""
            ),
            specialty=getattr(player, "speciality", ""),
            snapshot_source=source,
            missing_fields=tuple(key for key, value in fields.items() if value is None),
            **fields,
        )

    def to_dict(self) -> dict:
        data = dict(self.__dict__)
        data["missing_fields"] = list(self.missing_fields)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerMatchSnapshot":
        values = dict(data)
        values["missing_fields"] = tuple(values.get("missing_fields", ()))
        return cls(**values)


@dataclass(frozen=True)
class LineupSnapshot:
    formation: str
    starters: tuple[PlayerMatchSnapshot, ...]
    source: CalibrationSource | str = CalibrationSource.CURRENT_MATCH
    snapshot_timestamp: str = ""

    def __post_init__(self):
        if not self.snapshot_timestamp:
            object.__setattr__(self, "snapshot_timestamp", utc_now())
        if not isinstance(self.source, CalibrationSource):
            object.__setattr__(self, "source", CalibrationSource(str(self.source)))

    def to_dict(self) -> dict:
        return {
            "formation": self.formation,
            "source": self.source.value,
            "snapshot_timestamp": self.snapshot_timestamp,
            "starters": [player.to_dict() for player in self.starters],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LineupSnapshot":
        return cls(
            formation=data.get("formation", ""),
            source=data.get("source", CalibrationSource.CURRENT_MATCH.value),
            snapshot_timestamp=data.get("snapshot_timestamp", ""),
            starters=tuple(
                PlayerMatchSnapshot.from_dict(item)
                for item in data.get("starters", ())
            ),
        )


@dataclass(frozen=True)
class MatchContextSnapshot:
    team_attitude: str = "normal"
    team_spirit: int | None = None
    venue: str = ""
    home_or_away: str = ""
    coach_type: str = ""
    coach_leadership: str = ""
    tactic: str = ""
    tactic_level: int | None = None
    weather: str = ""
    match_period: str = "start"
    stamina_assumption: str = "start"
    data_complete: bool = False
    unsupported_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: dict | None) -> "MatchContextSnapshot":
        return cls(**(data or {}))


@dataclass(frozen=True)
class OfficialResult:
    goals_for: int | None = None
    goals_against: int | None = None
    possession: Decimal | None = None
    match_id: str = ""
    report_url: str = ""

    def to_dict(self) -> dict:
        return {
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "possession": str(self.possession) if self.possession is not None else None,
            "match_id": self.match_id,
            "report_url": self.report_url,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "OfficialResult":
        data = data or {}
        return cls(
            goals_for=data.get("goals_for"),
            goals_against=data.get("goals_against"),
            possession=(
                Decimal(str(data["possession"]))
                if data.get("possession") is not None
                else None
            ),
            match_id=data.get("match_id", ""),
            report_url=data.get("report_url", ""),
        )


@dataclass(frozen=True)
class RecordValidationIssue:
    code: str
    blocking: bool = True
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "blocking": self.blocking,
            "params": dict(self.params),
        }


@dataclass(frozen=True)
class CalibrationObservation:
    observation_id: str
    record_id: str
    model_version: str
    predicted_midfield: HattrickRating
    official_midfield: HattrickRating
    signed_error: Decimal
    absolute_error: Decimal
    exact_match: bool
    within_0_25: bool
    within_0_50: bool
    confidence: ObservationConfidence | str
    warnings: tuple[str, ...] = ()
    created_at: str = ""
    recalculated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            object.__setattr__(self, "created_at", utc_now())
        if not self.recalculated_at:
            object.__setattr__(self, "recalculated_at", self.created_at)
        if not isinstance(self.confidence, ObservationConfidence):
            object.__setattr__(self, "confidence", ObservationConfidence(str(self.confidence)))

    def to_dict(self) -> dict:
        return {
            "observation_id": self.observation_id,
            "record_id": self.record_id,
            "model_version": self.model_version,
            "predicted_midfield": self.predicted_midfield.to_dict(),
            "official_midfield": self.official_midfield.to_dict(),
            "signed_error": str(self.signed_error),
            "absolute_error": str(self.absolute_error),
            "exact_match": self.exact_match,
            "within_0_25": self.within_0_25,
            "within_0_50": self.within_0_50,
            "confidence": self.confidence.value,
            "warnings": list(self.warnings),
            "created_at": self.created_at,
            "recalculated_at": self.recalculated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CalibrationObservation":
        return cls(
            observation_id=data["observation_id"],
            record_id=data["record_id"],
            model_version=data["model_version"],
            predicted_midfield=HattrickRating.from_dict(data["predicted_midfield"]),
            official_midfield=HattrickRating.from_dict(data["official_midfield"]),
            signed_error=Decimal(str(data["signed_error"])),
            absolute_error=Decimal(str(data["absolute_error"])),
            exact_match=bool(data["exact_match"]),
            within_0_25=bool(data["within_0_25"]),
            within_0_50=bool(data["within_0_50"]),
            confidence=data["confidence"],
            warnings=tuple(data.get("warnings", ())),
            created_at=data.get("created_at", ""),
            recalculated_at=data.get("recalculated_at", ""),
        )


@dataclass(frozen=True)
class RealMatchCalibrationRecord:
    record_id: str
    match_date: str
    formation: str
    lineup_snapshot: LineupSnapshot | None = None
    match_context: MatchContextSnapshot = field(default_factory=MatchContextSnapshot)
    official_ratings: OfficialSectorRatings = field(default_factory=OfficialSectorRatings)
    match_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    competition_type: str = ""
    opponent_name: str = ""
    venue: str = ""
    official_result: OfficialResult = field(default_factory=OfficialResult)
    source: CalibrationSource | str = CalibrationSource.CURRENT_MATCH
    notes: str = ""
    record_status: CalibrationRecordStatus | str = CalibrationRecordStatus.DRAFT
    schema_version: int = SCHEMA_VERSION
    played: bool = False
    observations_by_model_version: dict[str, CalibrationObservation] = field(
        default_factory=dict
    )
    synthetic: bool = False

    def __post_init__(self):
        now = utc_now()
        if not self.created_at:
            object.__setattr__(self, "created_at", now)
        if not self.updated_at:
            object.__setattr__(self, "updated_at", now)
        if not isinstance(self.record_status, CalibrationRecordStatus):
            object.__setattr__(
                self,
                "record_status",
                CalibrationRecordStatus(str(self.record_status)),
            )
        if not isinstance(self.source, CalibrationSource):
            object.__setattr__(self, "source", CalibrationSource(str(self.source)))

    def with_updates(self, **changes) -> "RealMatchCalibrationRecord":
        changes["updated_at"] = utc_now()
        return replace(self, **changes)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "match_id": self.match_id,
            "match_date": self.match_date,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "competition_type": self.competition_type,
            "opponent_name": self.opponent_name,
            "venue": self.venue,
            "formation": self.formation,
            "lineup_snapshot": (
                self.lineup_snapshot.to_dict() if self.lineup_snapshot else None
            ),
            "match_context": self.match_context.to_dict(),
            "official_ratings": self.official_ratings.to_dict(),
            "official_result": self.official_result.to_dict(),
            "source": self.source.value,
            "notes": self.notes,
            "record_status": self.record_status.value,
            "played": self.played,
            "synthetic": self.synthetic,
            "observations_by_model_version": {
                version: observation.to_dict()
                for version, observation in self.observations_by_model_version.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RealMatchCalibrationRecord":
        return cls(
            schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
            record_id=data["record_id"],
            match_id=data.get("match_id", ""),
            match_date=data.get("match_date", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            competition_type=data.get("competition_type", ""),
            opponent_name=data.get("opponent_name", ""),
            venue=data.get("venue", ""),
            formation=data.get("formation", ""),
            lineup_snapshot=(
                LineupSnapshot.from_dict(data["lineup_snapshot"])
                if data.get("lineup_snapshot")
                else None
            ),
            match_context=MatchContextSnapshot.from_dict(data.get("match_context")),
            official_ratings=OfficialSectorRatings.from_dict(
                data.get("official_ratings")
            ),
            official_result=OfficialResult.from_dict(data.get("official_result")),
            source=data.get("source", CalibrationSource.CURRENT_MATCH.value),
            notes=data.get("notes", ""),
            record_status=data.get("record_status", CalibrationRecordStatus.DRAFT.value),
            played=bool(data.get("played", False)),
            synthetic=bool(data.get("synthetic", False)),
            observations_by_model_version={
                version: CalibrationObservation.from_dict(observation)
                for version, observation in data.get(
                    "observations_by_model_version",
                    {},
                ).items()
            },
        )


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_record_date(value: str) -> date:
    return date.fromisoformat(str(value)[:10])
