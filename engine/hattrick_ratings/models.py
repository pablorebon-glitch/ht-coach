from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

from engine.ratings.rating_alignment import HATTRICK_LEVELS, HATTRICK_SUBLEVELS


QUARTER = Decimal("0.25")


class PredictionConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCALIBRATED = "uncalibrated"


@dataclass(frozen=True)
class HattrickRatingLevel:
    index: int
    name: str


@dataclass(frozen=True)
class HattrickSublevel:
    decimal: Decimal
    name: str


@dataclass(frozen=True)
class HattrickRating:
    quarter_steps: int

    def __post_init__(self):
        if self.quarter_steps < 0:
            raise ValueError("Hattrick rating cannot be negative")

    @classmethod
    def from_decimal(cls, value) -> "HattrickRating":
        decimal = Decimal(str(value))
        if decimal < 0:
            raise ValueError("Hattrick rating cannot be negative")
        quarter_steps = int(
            (decimal / QUARTER).to_integral_value(rounding=ROUND_HALF_UP)
        )
        return cls(quarter_steps=quarter_steps)

    @property
    def decimal(self) -> Decimal:
        return (Decimal(self.quarter_steps) * QUARTER).quantize(QUARTER)

    @property
    def level(self) -> HattrickRatingLevel | None:
        index = int(self.decimal.to_integral_value(rounding="ROUND_FLOOR"))
        name = HATTRICK_LEVELS.get(index)
        if name is None:
            return None
        return HattrickRatingLevel(index=index, name=name)

    @property
    def sublevel(self) -> HattrickSublevel | None:
        level_index = int(self.decimal.to_integral_value(rounding="ROUND_FLOOR"))
        fraction = (self.decimal - Decimal(level_index)).quantize(Decimal("0.01"))
        name = HATTRICK_SUBLEVELS.get(fraction)
        if name is None:
            return None
        return HattrickSublevel(decimal=fraction, name=name)

    def display_decimal(self) -> str:
        return f"{self.decimal:.2f} HT"

    def display_name(self) -> str:
        level = self.level
        sublevel = self.sublevel
        if level is None or sublevel is None:
            return self.display_decimal()
        return f"{level.name.replace('_', ' ')} ({sublevel.name.replace('_', ' ')})"

    def to_dict(self) -> dict:
        return {
            "quarter_steps": self.quarter_steps,
            "decimal": str(self.decimal),
            "display": self.display_decimal(),
            "level": self.level.name if self.level else "",
            "sublevel": self.sublevel.name if self.sublevel else "",
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HattrickRating":
        return cls(quarter_steps=int(data["quarter_steps"]))
