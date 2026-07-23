from __future__ import annotations

from decimal import Decimal, InvalidOperation

from engine.hattrick_ratings.models import HattrickRating
from engine.ratings.rating_alignment import HATTRICK_LEVELS, HATTRICK_SUBLEVELS


LEVEL_NAME_TO_INDEX = {value.replace("_", " "): key for key, value in HATTRICK_LEVELS.items()}
SUBLEVEL_NAME_TO_DECIMAL = {
    value.replace("_", " "): key for key, value in HATTRICK_SUBLEVELS.items()
}


def parse_official_rating(value) -> HattrickRating:
    if value is None or value == "":
        raise ValueError("missing official rating")
    if isinstance(value, dict):
        return HattrickRating.from_dict(value)
    text = str(value).strip().lower()
    try:
        decimal = Decimal(text)
        return _rating_from_exact_quarter(decimal)
    except InvalidOperation:
        pass
    return _named_rating(text.replace("-", " "))


def _rating_from_exact_quarter(decimal: Decimal) -> HattrickRating:
    if decimal < 0:
        raise ValueError("official rating cannot be negative")
    quarter_units = decimal * Decimal("4")
    if quarter_units != quarter_units.to_integral_value():
        raise ValueError("official rating must be an exact quarter step")
    return HattrickRating(quarter_steps=int(quarter_units))


def _named_rating(text: str) -> HattrickRating:
    cleaned = text.replace("(", " ").replace(")", " ")
    parts = " ".join(cleaned.split())
    for level_name, level_index in LEVEL_NAME_TO_INDEX.items():
        if not parts.startswith(level_name):
            continue
        sublevel_text = parts[len(level_name):].strip()
        if sublevel_text in SUBLEVEL_NAME_TO_DECIMAL:
            return _rating_from_exact_quarter(
                Decimal(level_index) + SUBLEVEL_NAME_TO_DECIMAL[sublevel_text]
            )
    raise ValueError("unsupported official rating label")
