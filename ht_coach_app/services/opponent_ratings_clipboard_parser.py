import html
import re
import unicodedata
from dataclasses import dataclass, field

from ht_coach_app.services.opponent_service import HATTRICK_SECTOR_ORDER


MAX_CLIPBOARD_LENGTH = 20000

SECTION_INDIRECT = "indirect"
SECTION_AVERAGES = "averages"
SECTION_IGNORED = "ignored"

MAIN_ALIASES = {
    "midfield": "midfield",
    "mediocampo": "midfield",
    "right defense": "right_defense",
    "defensa derecha": "right_defense",
    "central defense": "central_defense",
    "defensa central": "central_defense",
    "left defense": "left_defense",
    "defensa izquierda": "left_defense",
    "right attack": "right_attack",
    "ataque derecho": "right_attack",
    "central attack": "central_attack",
    "ataque central": "central_attack",
    "left attack": "left_attack",
    "ataque izquierdo": "left_attack",
}

INDIRECT_ALIASES = {
    "defense": "indirect_defense",
    "defence": "indirect_defense",
    "defensa": "indirect_defense",
    "attack": "indirect_attack",
    "ataque": "indirect_attack",
}

SECTION_ALIASES = {
    "indirect set pieces": SECTION_INDIRECT,
    "indirect set pieces ratings": SECTION_INDIRECT,
    "set pieces": SECTION_INDIRECT,
    "tiro indirecto": SECTION_INDIRECT,
    "game plan": SECTION_IGNORED,
    "plan de juego": SECTION_IGNORED,
    "average ratings": SECTION_AVERAGES,
    "calificaciones medias": SECTION_AVERAGES,
}


@dataclass(frozen=True)
class OpponentRatingsClipboardResult:
    team_name: str = ""
    team_id: str = ""
    match_id: str = ""
    ratings: dict = field(default_factory=dict)
    descriptive_labels: dict = field(default_factory=dict)
    warnings: tuple = ()
    ignored_sections: tuple = ()
    source_language: str = "unknown"
    success: bool = False
    error_key: str = ""


def parse_opponent_ratings_clipboard(text):
    raw_text = str(text or "").strip()
    if not raw_text:
        return _error("opponents.clipboard.error.empty")
    if len(raw_text) > MAX_CLIPBOARD_LENGTH:
        return _error("opponents.clipboard.error.too_large")

    match_id = _first_group(r"\[matchid=(\d+)\]", raw_text)
    team_id = _first_group(r"\[teamid=(\d+)\]", raw_text)
    team_name = _extract_team_name(raw_text)

    ratings = {}
    labels = {}
    warnings = []
    ignored_sections = []
    source_language = "unknown"
    section = ""

    for row in _rows(raw_text):
        cells = _cells(row)
        if not cells:
            continue

        first = _clean_cell(cells[0])
        normalized_first = _normalize_label(first)
        if not normalized_first:
            continue

        first_attributes = cells[0][0] if isinstance(cells[0], tuple) else ""
        if len(cells) == 1 or "colspan" in first_attributes.lower():
            mapped_section = SECTION_ALIASES.get(normalized_first)
            if mapped_section:
                section = mapped_section
                ignored_sections.append(mapped_section)
            continue

        if section == SECTION_AVERAGES:
            continue

        field_name = None
        if section == SECTION_INDIRECT:
            field_name = INDIRECT_ALIASES.get(normalized_first)
        if field_name is None and section != SECTION_INDIRECT:
            field_name = MAIN_ALIASES.get(normalized_first)
        if field_name is None:
            continue

        source_language = _detect_language(normalized_first, source_language)
        numeric_text = _clean_cell(cells[-1])
        value = _parse_decimal(numeric_text)
        if value is None:
            warnings.append(f"invalid_numeric:{field_name}")
            continue

        if field_name in ratings:
            if ratings[field_name] == value:
                continue
            warnings.append(f"conflicting_duplicate:{field_name}")
            continue

        ratings[field_name] = value
        if len(cells) >= 3:
            label = _clean_cell(cells[1])
            if label:
                labels[field_name] = label

    missing_main = [
        field_name
        for field_name in HATTRICK_SECTOR_ORDER[:7]
        if field_name not in ratings
    ]
    missing_optional = [
        field_name
        for field_name in HATTRICK_SECTOR_ORDER[7:]
        if field_name not in ratings
    ]
    warnings.extend(f"missing:{field_name}" for field_name in missing_main)
    warnings.extend(f"missing_optional:{field_name}" for field_name in missing_optional)

    if not ratings:
        return OpponentRatingsClipboardResult(
            team_name=team_name,
            team_id=team_id,
            match_id=match_id,
            warnings=tuple(warnings),
            ignored_sections=tuple(dict.fromkeys(ignored_sections)),
            source_language=source_language,
            success=False,
            error_key="opponents.clipboard.error.no_ratings",
        )

    return OpponentRatingsClipboardResult(
        team_name=team_name,
        team_id=team_id,
        match_id=match_id,
        ratings=ratings,
        descriptive_labels=labels,
        warnings=tuple(warnings),
        ignored_sections=tuple(dict.fromkeys(ignored_sections)),
        source_language=source_language,
        success=True,
        error_key="",
    )


def _error(error_key):
    return OpponentRatingsClipboardResult(
        success=False,
        error_key=error_key,
    )


def _rows(text):
    matches = re.findall(r"\[tr[^\]]*\](.*?)\[/tr\]", text, flags=re.I | re.S)
    if matches:
        return matches
    return [text]


def _cells(row):
    return re.findall(r"\[(?:th|td)([^\]]*)\](.*?)\[/(?:th|td)\]", row, flags=re.I | re.S)


def _clean_cell(cell):
    if isinstance(cell, tuple):
        cell = cell[1]
    text = re.sub(r"\[[^\]]+\]", "", str(cell), flags=re.S)
    text = html.unescape(text)
    return " ".join(text.split()).strip()


def _normalize_label(value):
    text = _clean_cell(value).casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(text.split())


def _parse_decimal(value):
    text = _clean_cell(value).replace(",", ".")
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _first_group(pattern, text):
    match = re.search(pattern, text, flags=re.I)
    return match.group(1) if match else ""


def _extract_team_name(text):
    match = re.search(
        r"\[th[^\]]*colspan=2[^\]]*\](.*?)\[/th\]",
        text,
        flags=re.I | re.S,
    )
    if not match:
        return ""
    name = re.sub(r"\[teamid=\d+\]", "", match.group(1), flags=re.I)
    return _clean_cell(name)


def _detect_language(normalized_label, current):
    if normalized_label in {
        "mediocampo",
        "defensa derecha",
        "defensa central",
        "defensa izquierda",
        "ataque derecho",
        "ataque central",
        "ataque izquierdo",
        "defensa",
        "ataque",
    }:
        return "es"
    if current == "unknown":
        return "en"
    return current
