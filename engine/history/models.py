from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from engine.history.enums import (
    CompetitionType,
    HistoricalRatingSource,
    HomeAway,
    ScheduleGroup,
    SnapshotSource,
    SnapshotStage,
    TeamType,
)
from engine.history.schema import SCHEMA_VERSION
from engine.ratings.sector_rating import CANONICAL_SECTORS


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_snapshot_id() -> str:
    return str(uuid4())


def _enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _optional_float(value):
    if value is None or value == "":
        return None
    return float(value)


def _optional_int(value):
    if value is None or value == "":
        return None
    return int(value)


@dataclass(frozen=True)
class OpponentReference:
    opponent_id: str = ""
    opponent_name: str = ""
    country_or_region: str = ""
    division_or_league: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "OpponentReference":
        return cls(**(data or {}))


@dataclass(frozen=True)
class MatchContext:
    official_match_id: str = ""
    match_date: str = ""
    kickoff_time: str = ""
    season: str = ""
    round: str = ""
    competition_type: CompetitionType | str = CompetitionType.UNKNOWN
    match_type: str = ""
    home_away: HomeAway | str = HomeAway.UNKNOWN
    team_type: TeamType | str = TeamType.UNKNOWN
    opponent: OpponentReference = field(default_factory=OpponentReference)
    venue: str = ""
    snapshot_stage: SnapshotStage | str = SnapshotStage.PLANNED

    def __post_init__(self):
        object.__setattr__(
            self,
            "competition_type",
            CompetitionType.parse(self.competition_type),
        )
        object.__setattr__(self, "home_away", HomeAway.parse(self.home_away))
        object.__setattr__(self, "team_type", TeamType.parse(self.team_type))
        object.__setattr__(
            self,
            "snapshot_stage",
            SnapshotStage.parse(self.snapshot_stage),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "official_match_id": self.official_match_id,
            "match_date": self.match_date,
            "kickoff_time": self.kickoff_time,
            "season": self.season,
            "round": self.round,
            "competition_type": self.competition_type.value,
            "match_type": self.match_type,
            "home_away": self.home_away.value,
            "team_type": self.team_type.value,
            "opponent": self.opponent.to_dict(),
            "venue": self.venue,
            "snapshot_stage": self.snapshot_stage.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "MatchContext":
        data = data or {}
        return cls(
            official_match_id=data.get("official_match_id", ""),
            match_date=data.get("match_date", ""),
            kickoff_time=data.get("kickoff_time", ""),
            season=data.get("season", ""),
            round=data.get("round", ""),
            competition_type=data.get("competition_type", CompetitionType.UNKNOWN.value),
            match_type=data.get("match_type", ""),
            home_away=data.get("home_away", HomeAway.UNKNOWN.value),
            team_type=data.get("team_type", TeamType.UNKNOWN.value),
            opponent=OpponentReference.from_dict(data.get("opponent")),
            venue=data.get("venue", ""),
            snapshot_stage=data.get("snapshot_stage", SnapshotStage.PLANNED.value),
        )


@dataclass(frozen=True)
class TacticalSetup:
    formation: str = ""
    selected_tactic: str = ""
    tactic_level: float | None = None
    team_attitude: str = ""
    style_or_mentality: str = ""
    confidence: str = ""
    home_away: HomeAway | str = HomeAway.UNKNOWN
    set_piece_taker: str = ""

    def __post_init__(self):
        object.__setattr__(self, "home_away", HomeAway.parse(self.home_away))

    def to_dict(self) -> dict[str, Any]:
        return {
            "formation": self.formation,
            "selected_tactic": self.selected_tactic,
            "tactic_level": self.tactic_level,
            "team_attitude": self.team_attitude,
            "style_or_mentality": self.style_or_mentality,
            "confidence": self.confidence,
            "home_away": self.home_away.value,
            "set_piece_taker": self.set_piece_taker,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "TacticalSetup":
        data = data or {}
        return cls(
            formation=data.get("formation", ""),
            selected_tactic=data.get("selected_tactic", ""),
            tactic_level=_optional_float(data.get("tactic_level")),
            team_attitude=data.get("team_attitude", ""),
            style_or_mentality=data.get("style_or_mentality", ""),
            confidence=data.get("confidence", ""),
            home_away=data.get("home_away", HomeAway.UNKNOWN.value),
            set_piece_taker=data.get("set_piece_taker", ""),
        )


@dataclass(frozen=True)
class HistoricalPlayerSkills:
    goalkeeper: int | None = None
    defending: int | None = None
    playmaking: int | None = None
    winger: int | None = None
    passing: int | None = None
    scoring: int | None = None
    set_pieces: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "HistoricalPlayerSkills":
        data = data or {}
        return cls(**{key: _optional_int(data.get(key)) for key in cls.__annotations__})


@dataclass(frozen=True)
class HistoricalLineupEntry:
    player_id: str = ""
    player_name: str = ""
    number: int = 0
    position: str = ""
    side: str = ""
    individual_order: str = ""
    order_side: str = ""
    specialty: str = ""
    form: int | None = None
    stamina: int | None = None
    experience: int | None = None
    skills: HistoricalPlayerSkills = field(default_factory=HistoricalPlayerSkills)
    is_starter: bool = True
    substitution_minute: int | None = None
    replaced_player_id: str = ""
    replaced_player_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "number": self.number,
            "position": self.position,
            "side": self.side,
            "individual_order": self.individual_order,
            "order_side": self.order_side,
            "specialty": self.specialty,
            "form": self.form,
            "stamina": self.stamina,
            "experience": self.experience,
            "skills": self.skills.to_dict(),
            "is_starter": self.is_starter,
            "substitution_minute": self.substitution_minute,
            "replaced_player_id": self.replaced_player_id,
            "replaced_player_name": self.replaced_player_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoricalLineupEntry":
        return cls(
            player_id=data.get("player_id", ""),
            player_name=data.get("player_name", ""),
            number=int(data.get("number", 0)),
            position=data.get("position", ""),
            side=data.get("side", ""),
            individual_order=data.get("individual_order", ""),
            order_side=data.get("order_side", ""),
            specialty=data.get("specialty", ""),
            form=_optional_int(data.get("form")),
            stamina=_optional_int(data.get("stamina")),
            experience=_optional_int(data.get("experience")),
            skills=HistoricalPlayerSkills.from_dict(data.get("skills")),
            is_starter=bool(data.get("is_starter", True)),
            substitution_minute=_optional_int(data.get("substitution_minute")),
            replaced_player_id=data.get("replaced_player_id", ""),
            replaced_player_name=data.get("replaced_player_name", ""),
        )


@dataclass(frozen=True)
class SectorRatings:
    source: HistoricalRatingSource | str = HistoricalRatingSource.UNKNOWN
    scale: str = ""
    right_defense: float | None = None
    central_defense: float | None = None
    left_defense: float | None = None
    midfield: float | None = None
    right_attack: float | None = None
    central_attack: float | None = None
    left_attack: float | None = None
    indirect_defense: float | None = None
    indirect_attack: float | None = None

    def __post_init__(self):
        object.__setattr__(self, "source", HistoricalRatingSource.parse(self.source))

    def to_dict(self) -> dict[str, Any]:
        data = {
            "source": self.source.value,
            "scale": self.scale,
        }
        data.update({sector: getattr(self, sector) for sector in CANONICAL_SECTORS})
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SectorRatings | None":
        if data is None:
            return None
        values = {
            "source": data.get("source", HistoricalRatingSource.UNKNOWN.value),
            "scale": data.get("scale", ""),
        }
        values.update({sector: _optional_float(data.get(sector)) for sector in CANONICAL_SECTORS})
        return cls(**values)

    @property
    def has_any_rating(self) -> bool:
        return any(getattr(self, sector) is not None for sector in CANONICAL_SECTORS)


@dataclass(frozen=True)
class PredictionSnapshot:
    ratings: SectorRatings | None = None
    possession: float | None = None
    expected_goals: float | None = None
    opponent_expected_goals: float | None = None
    win_probability: float | None = None
    draw_probability: float | None = None
    loss_probability: float | None = None
    recommended_tactic: str = ""
    tactic_level: float | None = None
    model_version: str = ""
    prediction_timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ratings": self.ratings.to_dict() if self.ratings else None,
            "possession": self.possession,
            "expected_goals": self.expected_goals,
            "opponent_expected_goals": self.opponent_expected_goals,
            "win_probability": self.win_probability,
            "draw_probability": self.draw_probability,
            "loss_probability": self.loss_probability,
            "recommended_tactic": self.recommended_tactic,
            "tactic_level": self.tactic_level,
            "model_version": self.model_version,
            "prediction_timestamp": self.prediction_timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PredictionSnapshot":
        data = data or {}
        return cls(
            ratings=SectorRatings.from_dict(data.get("ratings")),
            possession=_optional_float(data.get("possession")),
            expected_goals=_optional_float(data.get("expected_goals")),
            opponent_expected_goals=_optional_float(data.get("opponent_expected_goals")),
            win_probability=_optional_float(data.get("win_probability")),
            draw_probability=_optional_float(data.get("draw_probability")),
            loss_probability=_optional_float(data.get("loss_probability")),
            recommended_tactic=data.get("recommended_tactic", ""),
            tactic_level=_optional_float(data.get("tactic_level")),
            model_version=data.get("model_version", ""),
            prediction_timestamp=data.get("prediction_timestamp", ""),
        )


@dataclass(frozen=True)
class OfficialResultSnapshot:
    goals_for: int | None = None
    goals_against: int | None = None
    ratings: SectorRatings | None = None
    official_tactic: str = ""
    official_tactic_level: float | None = None
    official_team_attitude: str = ""
    possession: float | None = None
    outcome: str = ""
    match_report_reference: str = ""
    played_lineup: tuple[HistoricalLineupEntry, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "ratings": self.ratings.to_dict() if self.ratings else None,
            "official_tactic": self.official_tactic,
            "official_tactic_level": self.official_tactic_level,
            "official_team_attitude": self.official_team_attitude,
            "possession": self.possession,
            "outcome": self.outcome,
            "match_report_reference": self.match_report_reference,
            "played_lineup": [entry.to_dict() for entry in self.played_lineup],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "OfficialResultSnapshot | None":
        if data is None:
            return None
        return cls(
            goals_for=_optional_int(data.get("goals_for")),
            goals_against=_optional_int(data.get("goals_against")),
            ratings=SectorRatings.from_dict(data.get("ratings")),
            official_tactic=data.get("official_tactic", ""),
            official_tactic_level=_optional_float(data.get("official_tactic_level")),
            official_team_attitude=data.get("official_team_attitude", ""),
            possession=_optional_float(data.get("possession")),
            outcome=data.get("outcome", ""),
            match_report_reference=data.get("match_report_reference", ""),
            played_lineup=tuple(
                HistoricalLineupEntry.from_dict(item)
                for item in data.get("played_lineup", [])
                if isinstance(item, dict)
            ),
        )


@dataclass(frozen=True)
class PredictionErrorPlaceholder:
    sector_errors: dict[str, float] = field(default_factory=dict)
    absolute_errors: dict[str, float] = field(default_factory=dict)
    outcome_correct: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sector_errors": dict(self.sector_errors),
            "absolute_errors": dict(self.absolute_errors),
            "outcome_correct": self.outcome_correct,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PredictionErrorPlaceholder | None":
        if data is None:
            return None
        return cls(
            sector_errors=dict(data.get("sector_errors", {})),
            absolute_errors=dict(data.get("absolute_errors", {})),
            outcome_correct=data.get("outcome_correct"),
        )


@dataclass(frozen=True)
class MatchCohort:
    competition_type: CompetitionType | str = CompetitionType.UNKNOWN
    team_type: TeamType | str = TeamType.UNKNOWN
    schedule_group: ScheduleGroup | str = ScheduleGroup.UNKNOWN
    official_context: bool = False

    def __post_init__(self):
        object.__setattr__(
            self,
            "competition_type",
            CompetitionType.parse(self.competition_type),
        )
        object.__setattr__(self, "team_type", TeamType.parse(self.team_type))
        object.__setattr__(
            self,
            "schedule_group",
            ScheduleGroup.parse(self.schedule_group),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "competition_type": self.competition_type.value,
            "team_type": self.team_type.value,
            "schedule_group": self.schedule_group.value,
            "official_context": self.official_context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "MatchCohort":
        data = data or {}
        return cls(
            competition_type=data.get("competition_type", CompetitionType.UNKNOWN.value),
            team_type=data.get("team_type", TeamType.UNKNOWN.value),
            schedule_group=data.get("schedule_group", ScheduleGroup.UNKNOWN.value),
            official_context=bool(data.get("official_context", False)),
        )


@dataclass(frozen=True)
class SnapshotProvenance:
    source_application_version: str = ""
    source_engine_version: str = ""
    imported_filename: str = ""
    imported_match_id: str = ""
    creation_workflow: str = ""
    roster_source: str = ""
    opponent_source: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SnapshotProvenance":
        return cls(**(data or {}))


@dataclass(frozen=True)
class HistoricalMatchSnapshot:
    snapshot_id: str
    schema_version: int = SCHEMA_VERSION
    created_at: str = ""
    updated_at: str = ""
    source: SnapshotSource | str = SnapshotSource.UNKNOWN
    match_context: MatchContext = field(default_factory=MatchContext)
    tactical_setup: TacticalSetup = field(default_factory=TacticalSetup)
    lineup: tuple[HistoricalLineupEntry, ...] = ()
    predictions: PredictionSnapshot = field(default_factory=PredictionSnapshot)
    official_result: OfficialResultSnapshot | None = None
    official_pre: "OfficialRatingSnapshot | None" = None
    official_post: "OfficialRatingSnapshot | None" = None
    cohort: MatchCohort = field(default_factory=MatchCohort)
    prediction_error: PredictionErrorPlaceholder | None = None
    provenance: SnapshotProvenance = field(default_factory=SnapshotProvenance)

    def __post_init__(self):
        if not self.snapshot_id:
            raise ValueError("snapshot_id is required")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"unsupported historical snapshot schema: {self.schema_version}")
        now = utc_now()
        if not self.created_at:
            object.__setattr__(self, "created_at", now)
        if not self.updated_at:
            object.__setattr__(self, "updated_at", self.created_at)
        object.__setattr__(self, "source", SnapshotSource.parse(self.source))

    @property
    def match_date_key(self) -> str:
        return self.match_context.match_date or self.created_at

    def with_updates(self, **changes) -> "HistoricalMatchSnapshot":
        changes["updated_at"] = utc_now()
        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source.value,
            "match_context": self.match_context.to_dict(),
            "tactical_setup": self.tactical_setup.to_dict(),
            "lineup": [entry.to_dict() for entry in self.lineup],
            "predictions": self.predictions.to_dict(),
            "official_result": (
                self.official_result.to_dict() if self.official_result else None
            ),
            "official_pre": (
                self.official_pre.to_dict() if self.official_pre else None
            ),
            "official_post": (
                self.official_post.to_dict() if self.official_post else None
            ),
            "cohort": self.cohort.to_dict(),
            "prediction_error": (
                self.prediction_error.to_dict() if self.prediction_error else None
            ),
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoricalMatchSnapshot":
        if int(data.get("schema_version", 0)) != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported historical snapshot schema: {data.get('schema_version')}"
            )
        # Imported lazily to avoid a circular import: official_ratings
        # imports SectorRatings from this module.
        from engine.history.official_ratings.models import OfficialRatingSnapshot

        return cls(
            snapshot_id=data.get("snapshot_id", ""),
            schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            source=data.get("source", SnapshotSource.UNKNOWN.value),
            match_context=MatchContext.from_dict(data.get("match_context")),
            tactical_setup=TacticalSetup.from_dict(data.get("tactical_setup")),
            lineup=tuple(
                HistoricalLineupEntry.from_dict(item)
                for item in data.get("lineup", [])
                if isinstance(item, dict)
            ),
            predictions=PredictionSnapshot.from_dict(data.get("predictions")),
            official_result=OfficialResultSnapshot.from_dict(data.get("official_result")),
            official_pre=OfficialRatingSnapshot.from_dict(data.get("official_pre")),
            official_post=OfficialRatingSnapshot.from_dict(data.get("official_post")),
            cohort=MatchCohort.from_dict(data.get("cohort")),
            prediction_error=PredictionErrorPlaceholder.from_dict(
                data.get("prediction_error")
            ),
            provenance=SnapshotProvenance.from_dict(data.get("provenance")),
        )
