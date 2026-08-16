from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

from engine.history.official_ratings.models import OfficialRatingSnapshot, RatedAttribute
from engine.history.official_ratings.tactic_catalog import find_tactic_alias_prefix
from engine.history.official_ratings.validation import OfficialRatingParsingError

# ---------------------------------------------------------------------------
# CALIBRATION NOTE (updated after a real sample)
#
# This parser has been calibrated against a real "Copy Ratings" paste from a
# live Hattrick account. The actual export is BBCode: a header line with the
# team name and [matchid=...], a [table] block with one row per sector
# (Defense/Midfield/Attack, each row holding left/center/right as separate
# [td] cells, or a single colspan=3 cell for Midfield), followed by plain
# [b]Label[/b]: value lines for Formation, Tactic, Team Attitude and Style.
#
# It remains tolerant beyond that one sample: keyword matching accepts
# several English/Spanish variants, accent-insensitive comparison, and any
# line it still can't place is preserved in `unparsed_lines` rather than
# failing the import. Fields not present in the calibration sample
# (Formation Experience, Average rating, Indirect Set Pieces) are still
# supported via the same "[b]Label[/b]: value" line pattern, since Hattrick
# is known to include them in some export states.
# ---------------------------------------------------------------------------

_BOLD_TAG = re.compile(r"\[/?b\]", re.IGNORECASE)
_HEADER_LINE = re.compile(
    r"\[b\](?P<team>.*?)\[/b\]\s*(?:\[matchid=(?P<match_id>\d+)\])?", re.IGNORECASE
)
_MATCH_ID = re.compile(r"\[matchid=(?P<match_id>\d+)\]", re.IGNORECASE)
_TABLE_BLOCK = re.compile(r"\[table\](?P<body>.*?)\[/table\]", re.IGNORECASE | re.DOTALL)
_TABLE_ROW = re.compile(r"\[tr\](?P<row>.*?)\[/tr\]", re.IGNORECASE | re.DOTALL)
_TABLE_HEADER_CELL = re.compile(r"\[th\](?P<label>.*?)\[/th\]", re.IGNORECASE | re.DOTALL)
_TABLE_HEADER_CELL_ANY = re.compile(r"\[th[^\]]*\](?P<label>.*?)\[/th\]", re.IGNORECASE | re.DOTALL)
_TABLE_DATA_CELL = re.compile(r"\[td[^\]]*\](?P<value>.*?)\[/td\]", re.IGNORECASE | re.DOTALL)

# A "quality word (number)" fragment, e.g. "excellent (8)", "clase mundial
# (13)". Either half may be missing.
_QUALITY_NUMBER = re.compile(
    r"(?P<quality>[A-Za-zÁÉÍÓÚáéíóúñÑ%/ -]+?)?\s*\(?\s*(?P<level>-?\d+(?:[.,]\d+)?)?\s*\)?\s*$"
)

_FORMATION_TOKEN = re.compile(r"(?P<formation>\d(?:-\d){2,4})\s*(?P<rest>.*)$")
_FLOAT = re.compile(r"-?\d+(?:[.,]\d+)?")


def _strip_bbcode(text):
    return re.sub(r"\[[^\]]*\]", "", text)


def _repair_common_mojibake(text):
    replacements = {
        "Ã¡": "á",
        "Ã©": "é",
        "Ã­": "í",
        "Ã³": "ó",
        "Ãº": "ú",
        "Ã±": "ñ",
        "Ã": "Á",
        "Ã‰": "É",
        "Ã": "Í",
        "Ã“": "Ó",
        "Ãš": "Ú",
        "Ã‘": "Ñ",
    }
    for broken, fixed in replacements.items():
        text = text.replace(broken, fixed)
    return text


def _normalize(text):
    """Lowercased, accent-stripped, whitespace-collapsed — used only for
    keyword comparison, never for anything that gets stored."""
    text = unicodedata.normalize("NFKD", _repair_common_mojibake(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.lower().split())


def _to_float(text):
    if text is None:
        return None
    text = text.strip().replace(",", ".").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _first_float(text):
    match = _FLOAT.search(text)
    return _to_float(match.group(0)) if match else None


def _split_label_value(line, keywords):
    """If `line` starts with one of `keywords` (accent/case-insensitive,
    optionally followed by ':'), return the remaining text after the
    keyword, taken from the *original* (non-normalized) line so accents
    and casing in the value are preserved. Keywords are tried
    longest-first so a short prefix never eats into a longer, more
    specific one that happens to share it."""
    normalized_line = _normalize(line)
    repaired_line = _repair_common_mojibake(line.strip())
    for keyword in sorted(keywords, key=len, reverse=True):
        normalized_keyword = _normalize(keyword)
        if normalized_line.startswith(normalized_keyword):
            remainder = repaired_line[len(keyword):]
            remainder = remainder.lstrip(":").strip()
            return remainder
    return None


def _parse_rated_attribute(label, remainder, known_prefixes=()):
    """Splits `remainder` into (leading free-text, quality, level). If
    `known_prefixes` is given (e.g. Hattrick's fixed tactic-name list),
    the longest matching known prefix is pulled out as `label` and only
    the rest is treated as quality/level — this is what correctly
    splits "Atacar por el centro clase mundial (13)" into the tactic
    name and its separate quality/level, since both are free-text
    phrases with no delimiter between them."""
    matched_prefix = ""
    working_text = remainder
    if known_prefixes:
        normalized_remainder = _normalize(remainder)
        for prefix in sorted(known_prefixes, key=len, reverse=True):
            normalized_prefix = _normalize(prefix)
            if normalized_remainder.startswith(normalized_prefix):
                matched_prefix = remainder.strip()[: len(prefix)].strip()
                working_text = remainder.strip()[len(prefix):].strip()
                break

    match = _QUALITY_NUMBER.match(working_text)
    quality = (match.group("quality") or "").strip() if match else working_text.strip()
    level = _to_float(match.group("level")) if match else None
    return RatedAttribute(
        label=matched_prefix or label,
        quality=quality,
        level=level,
        raw_text=remainder.strip(),
    )


# Keyword variants per field, most specific first (also re-sorted by length
# internally, so order here only matters for readability).
_SECTOR_ROW_KEYWORDS = {
    "defense": ("defense", "defensa"),
    "midfield": ("midfield", "mediocampo", "medio campo"),
    "attack": ("attack", "ataque"),
}
_INDIRECT_DEFENSE_KEYWORDS = (
    "indirect free kicks (defense)",
    "indirect set pieces (defense)",
    "jugadas a balon parado indirectas (defensa)",
    "jugadas de pizarra indirectas (defensa)",
)
_INDIRECT_ATTACK_KEYWORDS = (
    "indirect free kicks (attack)",
    "indirect set pieces (attack)",
    "jugadas a balon parado indirectas (ataque)",
    "jugadas de pizarra indirectas (ataque)",
)

_TACTIC_KEYWORDS = ("tactic type", "game plan", "tactics", "tactic", "tacticas", "tactica", "plan de juego")
_TACTIC_LEVEL_KEYWORDS = ("tactic level", "tactic skill", "nivel de tactica", "nivel tactico")
_FORMATION_KEYWORDS = ("formation", "formacion")
_FORMATION_EXPERIENCE_KEYWORDS = (
    "formation experience",
    "experiencia de formacion",
    "experiencia con la formacion",
)
_TEAM_ATTITUDE_KEYWORDS = (
    "hidden team attitude", "team attitude", "actitud del equipo", "actitud oculta", "actitud",
)
_STYLE_KEYWORDS = ("style of play", "playing style", "style", "estilo de juego", "estilo")
_AVERAGE_KEYWORDS = (
    "average ratings", "average rating", "average", "promedio", "calificacion promedio",
    "calificaciones promedio",
)

# Fallback for sector values when no [table] block is present at all, or a
# sector wasn't found inside it (e.g. a manually retyped or differently
# formatted export): plain "Label: value" lines, one per sub-sector.
_LEGACY_SECTOR_LINE_KEYWORDS = {
    "left_defense": ("left defense", "defensa izquierda", "defensa izq"),
    "central_defense": ("central defense", "defensa central"),
    "right_defense": ("right defense", "defensa derecha", "defensa der"),
    "midfield": ("midfield", "mediocampo", "medio campo"),
    "left_attack": ("left attack", "ataque izquierdo", "ataque izq"),
    "central_attack": ("central attack", "ataque central"),
    "right_attack": ("right attack", "ataque derecho", "ataque der"),
}

_DETAILED_TABLE_CORE_LABELS = {
    "mediocampo": "midfield",
    "midfield": "midfield",
    "defensa derecha": "right_defense",
    "right defense": "right_defense",
    "defensa central": "central_defense",
    "central defense": "central_defense",
    "defensa izquierda": "left_defense",
    "left defense": "left_defense",
    "ataque derecho": "right_attack",
    "right attack": "right_attack",
    "ataque central": "central_attack",
    "central attack": "central_attack",
    "ataque izquierdo": "left_attack",
    "left attack": "left_attack",
}


COMPACT_PRE = "COMPACT_PRE"
DETAILED_POST = "DETAILED_POST"


def detect_format(raw_text):
    """Automatic format detection between the two confirmed/expected
    Hattrick "Copy Ratings" shapes:

    - COMPACT_PRE: the BBCode `[table]` layout confirmed against a real
      pre-match sample in Alpha 0.5.9.0 (one row per sector, left/
      center/right as separate `[td]` cells).
    - DETAILED_POST: a plain labeled-line layout (no `[table]` block),
      matching the field list Hattrick's detailed post-match summary is
      documented to include (Midfield, Right/Central/Left Defense,
      Right/Central/Left Attack, Indirect Set Pieces, Game Plan,
      Average Ratings, Hidden Team Attitude, Tactic, Tactic Level,
      Playing Style).

    This is purely informational/testable -- `parse_official_ratings`
    itself doesn't branch on the result, since its line-based fallback
    parsing already tolerates both shapes; `detect_format` exists so
    callers and tests can assert which shape was actually recognized.
    """
    table_match = _TABLE_BLOCK.search(raw_text or "")
    if table_match and not _is_detailed_post_table(table_match.group("body")):
        return COMPACT_PRE
    return DETAILED_POST


def _extract_header(raw_text):
    match = _HEADER_LINE.search(raw_text)
    if match:
        team_name = _strip_bbcode(match.group("team") or "").strip()
        match_id = match.group("match_id") or ""
        return team_name, match_id

    match_id_match = _MATCH_ID.search(raw_text)
    match_id = match_id_match.group("match_id") if match_id_match else ""
    team_name = ""
    table_match = _TABLE_BLOCK.search(raw_text)
    if table_match:
        first_row = _TABLE_ROW.search(table_match.group("body"))
        if first_row:
            headers = [
                _strip_bbcode(header).strip()
                for header in _TABLE_HEADER_CELL_ANY.findall(first_row.group("row"))
            ]
            team_name = next(
                (
                    header for header in headers
                    if header and not _normalize(header).isdigit()
                ),
                "",
            )
    return team_name, match_id


def _is_detailed_post_table(table_body):
    labels = [
        _normalize(_strip_bbcode(label))
        for row in _TABLE_ROW.findall(table_body or "")
        for label in _TABLE_HEADER_CELL_ANY.findall(row)
    ]
    detailed_sector_labels = set(_DETAILED_TABLE_CORE_LABELS) - {"mediocampo", "midfield"}
    return any(label in detailed_sector_labels for label in labels) or any(
        label in {"tiro indirecto", "indirect set pieces", "plan de juego", "game plan"}
        for label in labels
    )


def _last_float(values):
    for value in reversed(values):
        parsed = _first_float(value)
        if parsed is not None:
            return parsed
    return None


def _extract_detailed_table(table_body):
    values = {}
    synthesized_lines = []
    section = ""

    for row_match in _TABLE_ROW.finditer(table_body):
        row = row_match.group("row")
        headers = [_strip_bbcode(cell).strip() for cell in _TABLE_HEADER_CELL_ANY.findall(row)]
        cells = [_strip_bbcode(cell).strip() for cell in _TABLE_DATA_CELL.findall(row)]
        if not headers:
            continue

        label = headers[0]
        normalized_label = _normalize(label)
        normalized_cells = [_normalize(cell) for cell in cells]

        if not cells:
            if normalized_label in {
                "tiro indirecto",
                "indirect set pieces",
                "plan de juego",
                "game plan",
                "calificaciones medias",
                "average ratings",
            }:
                section = normalized_label
            continue

        value = _last_float(cells)
        if section in {"tiro indirecto", "indirect set pieces"}:
            if normalized_label in {"defensa", "defense"} and value is not None:
                values["indirect_defense"] = value
            elif normalized_label in {"ataque", "attack"} and value is not None:
                values["indirect_attack"] = value
            continue

        if section in {"calificaciones medias", "average ratings"}:
            if normalized_label in {"promedio total", "total average", "average rating"}:
                values["average_rating"] = value
            continue

        mapped_sector = _DETAILED_TABLE_CORE_LABELS.get(normalized_label)
        if mapped_sector and value is not None:
            values[mapped_sector] = value
            continue

        if normalized_label in {"actitud del equipo", "team attitude", "hidden team attitude"}:
            synthesized_lines.append(f"{label}: {' '.join(cells).strip()}")
        elif normalized_label in {"tactica", "tactics", "tactic"}:
            synthesized_lines.append(f"{label}: {' '.join(cells).strip()}")
        elif normalized_label in {"nivel de tactica", "tactic level", "tactic skill"}:
            synthesized_lines.append(f"{label}: {' '.join(cells).strip()}")
        elif normalized_label in {"estilo de juego", "style of play", "playing style"}:
            synthesized_lines.append(f"{label}: {' '.join(cells).strip()}")
        elif "oculta" in normalized_cells or "hidden" in normalized_cells:
            synthesized_lines.append(f"{label}: {' '.join(cells).strip()}")

    return values, "\n".join(synthesized_lines)


def _extract_table_sectors(raw_text):
    """Parses a [table]...[/table] block (if present) into
    {sector_name: value}. Each row's [th] label decides whether it's a
    defense/midfield/attack row; its [td] cells are read left-to-right
    as (left, central, right), or as a single shared value when there's
    only one cell (Hattrick uses colspan=3 for Midfield, which has no
    left/right split)."""
    values = {}
    table_match = _TABLE_BLOCK.search(raw_text)
    if not table_match:
        return values, raw_text

    body = table_match.group("body")
    if _is_detailed_post_table(body):
        values, synthesized_lines = _extract_detailed_table(body)
        if "average_rating" in values:
            average = values.pop("average_rating")
            synthesized_lines = "\n".join(
                line for line in (
                    synthesized_lines,
                    f"Average Ratings: {average}",
                )
                if line
            )
        remaining_text = raw_text[: table_match.start()] + raw_text[table_match.end():]
        return values, "\n".join(part for part in (remaining_text, synthesized_lines) if part)

    for row_match in _TABLE_ROW.finditer(body):
        row = row_match.group("row")
        header_match = _TABLE_HEADER_CELL.search(row)
        if not header_match:
            continue
        label = _strip_bbcode(header_match.group("label")).strip()
        normalized_label = _normalize(label)

        cells = [_strip_bbcode(cell).strip() for cell in _TABLE_DATA_CELL.findall(row)]
        cell_values = [_to_float(cell) for cell in cells]
        cell_values = [value for value in cell_values if value is not None]
        if not cell_values:
            continue

        sector_kind = next(
            (
                kind for kind, keywords in _SECTOR_ROW_KEYWORDS.items()
                if any(normalized_label.startswith(_normalize(k)) for k in keywords)
            ),
            None,
        )
        if sector_kind is None:
            continue

        if sector_kind == "midfield":
            values["midfield"] = cell_values[0]
        elif len(cell_values) >= 3:
            prefix = "left" if sector_kind == "defense" else "left"
            values[f"left_{sector_kind}"] = cell_values[0]
            values[f"central_{sector_kind}"] = cell_values[1]
            values[f"right_{sector_kind}"] = cell_values[2]
        elif len(cell_values) == 1:
            # A single shared value for defense/attack (some export
            # states may collapse this the same way Midfield always
            # does) -- store it as the central value only, since
            # there's no way to know it's meant to be split evenly.
            values[f"central_{sector_kind}"] = cell_values[0]

    remaining_text = raw_text[: table_match.start()] + raw_text[table_match.end():]
    return values, remaining_text


def parse_official_ratings(raw_text, *, captured_at=None, language=""):
    """Parses Hattrick's "Copy Ratings" text (BBCode, as copied from the
    Match Order page) into an OfficialRatingSnapshot.

    Unknown lines never fail parsing -- they're preserved in
    `unparsed_lines` so the caller can show a data-quality note instead
    of silently dropping them. Only a structurally empty/unusable input
    raises `OfficialRatingParsingError`.
    """
    if raw_text is None or not raw_text.strip():
        raise OfficialRatingParsingError("empty_copy_ratings_text")

    team_name, match_id = _extract_header(raw_text)
    sector_values, remaining_text = _extract_table_sectors(raw_text)

    lines = [_strip_bbcode(line).strip() for line in remaining_text.splitlines()]
    lines = [line for line in lines if line]

    formation = RatedAttribute()
    formation_experience = RatedAttribute()
    tactic_name = ""
    tactic_quality = ""
    tactic_level = None
    tactic_raw_parts = []
    canonical_tactic_value = ""
    team_attitude = ""
    style = ""
    average_rating = None
    unparsed_lines = []
    warnings = []

    for line in lines:
        # Skip the header line itself (team name / matchid), already
        # extracted separately above. By this point BBCode tags have
        # already been stripped from `line`, so the header line is just
        # the bare team name.
        if team_name and line.strip() == team_name:
            continue

        matched = False

        formation_token_match = _FORMATION_TOKEN.search(line)
        formation_remainder = _split_label_value(line, _FORMATION_KEYWORDS)
        if not matched and formation_remainder is not None:
            token_match = _FORMATION_TOKEN.search(formation_remainder)
            if token_match:
                rest = token_match.group("rest")
                parsed_rest = _QUALITY_NUMBER.match(rest) if rest else None
                formation = RatedAttribute(
                    label=token_match.group("formation"),
                    quality=(parsed_rest.group("quality") or "").strip() if parsed_rest else "",
                    level=_to_float(parsed_rest.group("level")) if parsed_rest else None,
                    raw_text=line,
                )
                matched = True

        if not matched:
            remainder = _split_label_value(line, _FORMATION_EXPERIENCE_KEYWORDS)
            if remainder is not None:
                formation_experience = _parse_rated_attribute("formation_experience", remainder)
                matched = True

        if not matched:
            remainder = _split_label_value(line, _TACTIC_LEVEL_KEYWORDS)
            if remainder is not None:
                parsed = _parse_rated_attribute("tactic_level", remainder)
                tactic_quality = tactic_quality or parsed.quality
                tactic_level = parsed.level if parsed.level is not None else tactic_level
                tactic_raw_parts.append(line)
                matched = True

        if not matched:
            remainder = _split_label_value(line, _TACTIC_KEYWORDS)
            if remainder is not None:
                alias_match = find_tactic_alias_prefix(remainder)
                if alias_match is not None:
                    matched_text, canonical = alias_match
                    working_text = remainder.strip()[len(matched_text):].strip()
                    quality_match = _QUALITY_NUMBER.match(working_text)
                    tactic_name = matched_text or tactic_name
                    canonical_tactic_value = canonical.value if canonical else ""
                    tactic_quality = (
                        (quality_match.group("quality") or "").strip()
                        if quality_match
                        else working_text
                    ) or tactic_quality
                    parsed_level = (
                        _to_float(quality_match.group("level")) if quality_match else None
                    )
                    tactic_level = tactic_level if tactic_level is not None else parsed_level
                else:
                    parsed = _parse_rated_attribute("tactic", remainder)
                    tactic_name = parsed.label or tactic_name
                    tactic_quality = parsed.quality or tactic_quality
                    tactic_level = tactic_level if tactic_level is not None else parsed.level
                    warnings.append("official_rating.warning.unsupported_tactic")
                tactic_raw_parts.append(line)
                matched = True

        if not matched:
            remainder = _split_label_value(line, _TEAM_ATTITUDE_KEYWORDS)
            if remainder is not None:
                team_attitude = remainder.strip()
                matched = True

        if not matched:
            remainder = _split_label_value(line, _STYLE_KEYWORDS)
            if remainder is not None:
                style = remainder.strip()
                matched = True

        if not matched:
            remainder = _split_label_value(line, _AVERAGE_KEYWORDS)
            if remainder is not None:
                average_rating = _first_float(remainder)
                matched = True

        if not matched:
            remainder = _split_label_value(line, _INDIRECT_DEFENSE_KEYWORDS)
            if remainder is not None:
                value = _first_float(remainder)
                if value is not None:
                    sector_values["indirect_defense"] = value
                    matched = True

        if not matched:
            remainder = _split_label_value(line, _INDIRECT_ATTACK_KEYWORDS)
            if remainder is not None:
                value = _first_float(remainder)
                if value is not None:
                    sector_values["indirect_attack"] = value
                    matched = True

        if not matched:
            for sector, keywords in _LEGACY_SECTOR_LINE_KEYWORDS.items():
                if sector in sector_values:
                    continue
                remainder = _split_label_value(line, keywords)
                if remainder is not None:
                    value = _first_float(remainder)
                    if value is not None:
                        sector_values[sector] = value
                        matched = True
                    break

        if not matched:
            unparsed_lines.append(line)

    from engine.history.enums import HistoricalRatingSource
    from engine.history.models import SectorRatings

    ratings = SectorRatings(
        source=HistoricalRatingSource.HATTRICK_OFFICIAL,
        left_defense=sector_values.get("left_defense"),
        central_defense=sector_values.get("central_defense"),
        right_defense=sector_values.get("right_defense"),
        midfield=sector_values.get("midfield"),
        left_attack=sector_values.get("left_attack"),
        central_attack=sector_values.get("central_attack"),
        right_attack=sector_values.get("right_attack"),
        indirect_defense=sector_values.get("indirect_defense"),
        indirect_attack=sector_values.get("indirect_attack"),
    )

    tactic = RatedAttribute(
        label=tactic_name,
        quality=tactic_quality,
        level=tactic_level,
        raw_text=" | ".join(tactic_raw_parts),
    )

    return OfficialRatingSnapshot(
        ratings=ratings,
        formation=formation,
        formation_experience=formation_experience,
        tactic=tactic,
        team_attitude=team_attitude,
        style=style,
        average_rating=average_rating,
        captured_at=captured_at or datetime.now(timezone.utc).isoformat(),
        language=language,
        raw_text=raw_text,
        unparsed_lines=tuple(unparsed_lines),
        team_name=team_name,
        hattrick_match_id=match_id,
        canonical_tactic=canonical_tactic_value,
        warnings=tuple(warnings),
        detected_format=detect_format(raw_text),
    )


def parse_official_pre_ratings(raw_text, *, captured_at=None, language=""):
    snapshot = parse_official_ratings(
        raw_text,
        captured_at=captured_at,
        language=language,
    )
    return snapshot


def parse_official_post_ratings(raw_text, *, captured_at=None, language=""):
    snapshot = parse_official_ratings(
        raw_text,
        captured_at=captured_at,
        language=language,
    )
    return snapshot
