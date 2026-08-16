"""The official Hattrick player specialties -- typed, localized, and
mapped from whatever raw text a Hattrick CSV export uses (Spanish or
English column values), instead of filtering on ad-hoc free text.
"""
from __future__ import annotations

from enum import Enum


class Specialty(str, Enum):
    NONE = "none"
    QUICK = "quick"
    TECHNICAL = "technical"
    POWERFUL = "powerful"
    UNPREDICTABLE = "unpredictable"
    HEAD = "head"
    RESILIENT = "resilient"

    @classmethod
    def parse(cls, raw_text) -> "Specialty":
        """Maps a raw Hattrick export value (Spanish or English,
        case/accent-insensitive) to its canonical `Specialty`. Unknown
        or empty text maps to `NONE` -- never raises, since a CSV row
        with an unrecognized specialty string is still a usable player
        row, just one without a known specialty."""
        if raw_text is None:
            return cls.NONE
        normalized = _normalize(str(raw_text))
        if not normalized:
            return cls.NONE
        return _RAW_TEXT_TO_SPECIALTY.get(normalized, cls.NONE)


def _normalize(text: str) -> str:
    import unicodedata

    stripped = "".join(
        char for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )
    return stripped.strip().lower()


_RAW_TEXT_TO_SPECIALTY = {
    "rapido": Specialty.QUICK,
    "tecnico": Specialty.TECHNICAL,
    "potente": Specialty.POWERFUL,
    "impredecible": Specialty.UNPREDICTABLE,
    "imprevisible": Specialty.UNPREDICTABLE,
    "cabeceador": Specialty.HEAD,
    "resistente": Specialty.RESILIENT,
    "sin especialidad": Specialty.NONE,
    "ninguna": Specialty.NONE,
    "quick": Specialty.QUICK,
    "technical": Specialty.TECHNICAL,
    "powerful": Specialty.POWERFUL,
    "unpredictable": Specialty.UNPREDICTABLE,
    "head": Specialty.HEAD,
    "head specialist": Specialty.HEAD,
    "resilient": Specialty.RESILIENT,
    "none": Specialty.NONE,
    "no specialty": Specialty.NONE,
}

ORDERED_SPECIALTIES = (
    Specialty.QUICK,
    Specialty.TECHNICAL,
    Specialty.POWERFUL,
    Specialty.UNPREDICTABLE,
    Specialty.HEAD,
    Specialty.RESILIENT,
    Specialty.NONE,
)
