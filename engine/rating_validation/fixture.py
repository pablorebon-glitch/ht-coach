from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any

from engine.ratings.sector_rating import CANONICAL_SECTORS


class FixtureCompleteness(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    MINIMAL = "minimal"
    UNKNOWN = "unknown"


class RatingPredictionProvider:
    """Interface for future rating engines.

    The validation framework consumes predictions when supplied; it never creates or
    estimates ratings itself.
    """

    def predict_fixture(self, fixture: "RatingValidationFixture") -> "PredictedRatings":
        raise NotImplementedError

    def predict_lineup(self, lineup, context=None) -> "PredictedRatings":
        raise NotImplementedError


@dataclass(frozen=True)
class HattrickRatings:
    midfield: float | None = None
    right_defense: float | None = None
    central_defense: float | None = None
    left_defense: float | None = None
    right_attack: float | None = None
    central_attack: float | None = None
    left_attack: float | None = None
    indirect_defense: float | None = None
    indirect_attack: float | None = None

    def __post_init__(self):
        for sector in CANONICAL_SECTORS:
            value = getattr(self, sector)
            if value is not None:
                _validate_numeric_rating(sector, value)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "HattrickRatings | None":
        if data is None:
            return None
        _reject_unsupported_rating_sectors(data)
        return cls(**{sector: data.get(sector) for sector in CANONICAL_SECTORS})

    def to_dict(self) -> dict[str, float | None]:
        return {sector: getattr(self, sector) for sector in CANONICAL_SECTORS}

    def present_sectors(self) -> tuple[str, ...]:
        return tuple(sector for sector in CANONICAL_SECTORS if getattr(self, sector) is not None)

    def missing_sectors(self) -> tuple[str, ...]:
        return tuple(sector for sector in CANONICAL_SECTORS if getattr(self, sector) is None)


@dataclass(frozen=True)
class OfficialHattrickRatings(HattrickRatings):
    pass


@dataclass(frozen=True)
class PredictedRatings(HattrickRatings):
    provider: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PredictedRatings | None":
        if data is None:
            return None
        _reject_unsupported_rating_sectors(data, allowed_extra={"provider"})
        values = {sector: data.get(sector) for sector in CANONICAL_SECTORS}
        values["provider"] = data.get("provider", "")
        return cls(**values)

    def to_dict(self) -> dict[str, float | None | str]:
        data = super().to_dict()
        data["provider"] = self.provider
        return data


@dataclass(frozen=True)
class RatingValidationFixture:
    fixture_name: str
    match_id: str = ""
    team_name: str = ""
    formation: str = ""
    orders: tuple[str, ...] = ()
    players: tuple[str, ...] = ()
    home_or_away: str = ""
    attitude: str = ""
    confidence: str = ""
    coach: str = ""
    weather: str = ""
    metadata_complete: bool = False
    official_hattrick_ratings: OfficialHattrickRatings | None = None
    predicted_ratings: PredictedRatings | None = None
    notes: str = ""
    additional_context: dict[str, Any] = field(default_factory=dict)
    completeness: FixtureCompleteness | None = None

    def __post_init__(self):
        if not self.fixture_name:
            raise ValueError("fixture_name is required")
        if self.completeness is not None and not isinstance(
            self.completeness,
            FixtureCompleteness,
        ):
            object.__setattr__(
                self,
                "completeness",
                FixtureCompleteness(str(self.completeness)),
            )

    @property
    def identifier(self) -> str:
        return self.match_id or self.fixture_name

    @property
    def classified_completeness(self) -> FixtureCompleteness:
        if self.completeness is not None:
            return self.completeness
        return classify_completeness(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RatingValidationFixture":
        values = dict(data)
        if "official_hattrick_ratings" in values:
            values["official_hattrick_ratings"] = OfficialHattrickRatings.from_dict(
                values["official_hattrick_ratings"]
            )
        if "predicted_ratings" in values:
            values["predicted_ratings"] = PredictedRatings.from_dict(
                values["predicted_ratings"]
            )
        for key in ("orders", "players"):
            if key in values and values[key] is not None:
                values[key] = tuple(values[key])
        if values.get("completeness") is not None:
            values["completeness"] = FixtureCompleteness(values["completeness"])
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture_name": self.fixture_name,
            "match_id": self.match_id,
            "team_name": self.team_name,
            "formation": self.formation,
            "orders": list(self.orders),
            "players": list(self.players),
            "home_or_away": self.home_or_away,
            "attitude": self.attitude,
            "confidence": self.confidence,
            "coach": self.coach,
            "weather": self.weather,
            "metadata_complete": self.metadata_complete,
            "official_hattrick_ratings": (
                self.official_hattrick_ratings.to_dict()
                if self.official_hattrick_ratings
                else None
            ),
            "predicted_ratings": (
                self.predicted_ratings.to_dict() if self.predicted_ratings else None
            ),
            "notes": self.notes,
            "additional_context": dict(self.additional_context),
            "completeness": self.classified_completeness.value,
        }


def classify_completeness(fixture: RatingValidationFixture) -> FixtureCompleteness:
    official = fixture.official_hattrick_ratings
    if official is None:
        return FixtureCompleteness.UNKNOWN

    present = set(official.present_sectors())
    if not present:
        return FixtureCompleteness.UNKNOWN
    if present != set(CANONICAL_SECTORS):
        return FixtureCompleteness.UNKNOWN

    context_fields = (
        fixture.team_name,
        fixture.formation,
        fixture.home_or_away,
        fixture.attitude,
        fixture.confidence,
        fixture.coach,
        fixture.weather,
    )
    has_context = any(context_fields) or bool(fixture.orders) or bool(fixture.players)
    if not has_context:
        return FixtureCompleteness.MINIMAL
    if fixture.metadata_complete and all(context_fields) and fixture.players:
        return FixtureCompleteness.COMPLETE
    return FixtureCompleteness.PARTIAL


def _validate_numeric_rating(sector: str, value: Any) -> None:
    if isinstance(value, bool):
        raise ValueError(f"{sector} rating must be numeric")
    numeric = float(value)
    if not isfinite(numeric):
        raise ValueError(f"{sector} rating must be finite")


def _reject_unsupported_rating_sectors(
    data: dict[str, Any],
    allowed_extra: set[str] | None = None,
) -> None:
    allowed = set(CANONICAL_SECTORS)
    if allowed_extra:
        allowed.update(allowed_extra)
    unsupported = sorted(set(data) - allowed)
    if unsupported:
        raise ValueError(f"unsupported rating sectors: {', '.join(unsupported)}")
