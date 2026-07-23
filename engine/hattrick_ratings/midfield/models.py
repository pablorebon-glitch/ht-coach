from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

from engine.hattrick_ratings.models import HattrickRating, PredictionConfidence


MODEL_VERSION = "midfield-v1"


class MatchPeriod(str, Enum):
    START = "start"
    END = "end"


class TeamAttitude(str, Enum):
    NORMAL = "normal"
    PLAY_IT_COOL = "play_it_cool"
    MATCH_OF_THE_SEASON = "match_of_the_season"


@dataclass(frozen=True)
class MidfieldModelParameters:
    playmaking_scale: Decimal = Decimal("11.0")
    base_rating: Decimal = Decimal("1.00")
    position_weights: dict[str, Decimal] = field(default_factory=dict)
    order_modifiers: dict[str, dict[str, Decimal]] = field(default_factory=dict)
    form_step: Decimal = Decimal("0.035")
    form_neutral: int = 7
    minimum_form_modifier: Decimal = Decimal("0.72")
    maximum_form_modifier: Decimal = Decimal("1.18")
    stamina_neutral: int = 7
    end_stamina_step: Decimal = Decimal("0.040")
    minimum_end_stamina_modifier: Decimal = Decimal("0.68")
    team_spirit_step: Decimal = Decimal("0.030")
    attitude_modifiers: dict[str, Decimal] = field(default_factory=dict)

    @classmethod
    def default(cls) -> "MidfieldModelParameters":
        return cls(
            position_weights={
                "INNER_MIDFIELDER": Decimal("1.00"),
                "WINGER": Decimal("0.33"),
                "WING_BACK": Decimal("0.12"),
                "CENTRAL_DEFENDER": Decimal("0.14"),
                "FORWARD": Decimal("0.10"),
                "GOALKEEPER": Decimal("0.00"),
            },
            order_modifiers={
                "INNER_MIDFIELDER": {
                    "NORMAL": Decimal("1.00"),
                    "OFFENSIVE": Decimal("0.92"),
                    "DEFENSIVE": Decimal("0.86"),
                    "TOWARDS_WING": Decimal("0.84"),
                },
                "WINGER": {
                    "NORMAL": Decimal("1.00"),
                    "TOWARDS_MIDDLE": Decimal("1.45"),
                    "OFFENSIVE": Decimal("0.90"),
                    "DEFENSIVE": Decimal("0.88"),
                },
                "WING_BACK": {
                    "NORMAL": Decimal("1.00"),
                    "TOWARDS_MIDDLE": Decimal("1.30"),
                    "DEFENSIVE": Decimal("0.95"),
                    "OFFENSIVE": Decimal("0.90"),
                },
                "CENTRAL_DEFENDER": {
                    "NORMAL": Decimal("1.00"),
                    "OFFENSIVE": Decimal("1.28"),
                    "DEFENSIVE": Decimal("0.88"),
                },
                "FORWARD": {
                    "NORMAL": Decimal("1.00"),
                    "DEFENSIVE": Decimal("1.35"),
                    "OFFENSIVE": Decimal("0.88"),
                    "TOWARDS_WING": Decimal("0.92"),
                },
                "GOALKEEPER": {"NORMAL": Decimal("1.00")},
            },
            attitude_modifiers={
                TeamAttitude.NORMAL.value: Decimal("1.00"),
                TeamAttitude.PLAY_IT_COOL.value: Decimal("0.88"),
                TeamAttitude.MATCH_OF_THE_SEASON.value: Decimal("1.12"),
            },
        )


@dataclass(frozen=True)
class MidfieldRatingContext:
    team_spirit: int | None = None
    attitude: TeamAttitude | str | None = TeamAttitude.NORMAL
    period: MatchPeriod | str = MatchPeriod.START
    coach: str = ""
    model_parameters: MidfieldModelParameters = field(
        default_factory=MidfieldModelParameters.default
    )


@dataclass(frozen=True)
class MidfieldRatingInput:
    lineup: Any
    formation: str = ""
    context: MidfieldRatingContext = field(default_factory=MidfieldRatingContext)


@dataclass(frozen=True)
class PlayerContributionBreakdown:
    player_name: str
    position: str
    order: str
    playmaking: Decimal
    position_weight: Decimal
    order_modifier: Decimal
    form_modifier: Decimal
    stamina_modifier: Decimal
    contribution: Decimal
    warning_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "player_name": self.player_name,
            "position": self.position,
            "order": self.order,
            "playmaking": str(self.playmaking),
            "position_weight": str(self.position_weight),
            "order_modifier": str(self.order_modifier),
            "form_modifier": str(self.form_modifier),
            "stamina_modifier": str(self.stamina_modifier),
            "contribution": str(self.contribution),
            "warning_codes": list(self.warning_codes),
        }


@dataclass(frozen=True)
class ContextModifierBreakdown:
    code: str
    modifier: Decimal
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "modifier": str(self.modifier),
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class PredictionBreakdown:
    player_contributions: tuple[PlayerContributionBreakdown, ...]
    context_modifiers: tuple[ContextModifierBreakdown, ...]
    raw_score: Decimal
    raw_rating: Decimal
    rounded_rating: HattrickRating
    warning_codes: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "player_contributions": [
                item.to_dict() for item in self.player_contributions
            ],
            "context_modifiers": [
                item.to_dict() for item in self.context_modifiers
            ],
            "raw_score": str(self.raw_score),
            "raw_rating": str(self.raw_rating),
            "rounded_rating": self.rounded_rating.to_dict(),
            "warning_codes": list(self.warning_codes),
        }


@dataclass(frozen=True)
class MidfieldPrediction:
    rating: HattrickRating
    raw_rating: Decimal
    confidence: PredictionConfidence
    breakdown: PredictionBreakdown
    model_version: str = MODEL_VERSION

    @property
    def quarter_steps(self) -> int:
        return self.rating.quarter_steps

    def to_dict(self) -> dict:
        return {
            "model_version": self.model_version,
            "rating": self.rating.to_dict(),
            "raw_rating": str(self.raw_rating),
            "confidence": self.confidence.value,
            "breakdown": self.breakdown.to_dict(),
        }
