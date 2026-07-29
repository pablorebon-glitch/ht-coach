from __future__ import annotations


def _format_number(value):
    if value is None:
        return "?"
    return f"{value:.2f}"


def format_sector_band(left, central, right):
    """"4.25 | 7.00 | 3.75" — the standard three-number Hattrick sector
    band. Any missing side shows "?" rather than a guessed number."""
    return " | ".join(_format_number(value) for value in (left, central, right))


def format_rated_attribute(attribute):
    """"2-5-3 excellent (8)" / "Attack in the middle world class (13)" —
    a RatedAttribute's label (if any), quality word and numeric level,
    only including the parts that are actually present."""
    if attribute is None:
        return ""
    parts = [part for part in (attribute.label, attribute.quality) if part]
    text = " ".join(parts)
    if attribute.level is not None:
        level_text = f"({attribute.level:g})"
        text = f"{text} {level_text}".strip()
    return text


def format_hattrick_notation(ratings, formation=None, tactic=None, team_attitude=""):
    """Renders a SectorRatings-like object plus optional formation/tactic
    RatedAttributes into the exact multi-line Hattrick-style summary
    requested for the Match page:

        Defense
        4.25 | 7.00 | 3.75

        Midfield
        7.25

        Attack
        7.75 | 9.75 | 8.00

        Formation
        2-5-3 excellent (8)

        Tactic
        Attack in the Middle world class (13)

        Team Attitude
        Normal

    Sections with nothing to show (e.g. no formation captured) are
    omitted rather than printed empty.
    """
    lines = []

    lines.append("Defense")
    lines.append(
        format_sector_band(ratings.left_defense, ratings.central_defense, ratings.right_defense)
    )
    lines.append("")

    lines.append("Midfield")
    lines.append(_format_number(ratings.midfield))
    lines.append("")

    lines.append("Attack")
    lines.append(
        format_sector_band(ratings.left_attack, ratings.central_attack, ratings.right_attack)
    )

    if formation is not None:
        formatted = format_rated_attribute(formation)
        if formatted:
            lines.append("")
            lines.append("Formation")
            lines.append(formatted)

    if tactic is not None:
        formatted = format_rated_attribute(tactic)
        if formatted:
            lines.append("")
            lines.append("Tactic")
            lines.append(formatted)

    if team_attitude:
        lines.append("")
        lines.append("Team Attitude")
        lines.append(team_attitude)

    return "\n".join(lines)


# Whether HT Coach's own predicted-rating scale is confirmed to align with
# Hattrick's official scale is explicitly *not yet established* -- see
# docs/OFFICIAL_RATING_WORKFLOW.md. Until a dedicated rating-alignment sprint
# confirms it, comparisons never subtract one from the other; showing a
# "difference" number would silently imply an equivalence that hasn't been
# verified.
SCALES_CONFIRMED_COMPATIBLE = False


def format_prediction_vs_official_comparison(comparison):
    """Renders the compact "HT Coach estimate vs. Official Hattrick PRE"
    table requested for the Match page. Per SCALES_CONFIRMED_COMPATIBLE,
    this never computes or displays a numeric delta today -- only the
    two raw values side by side, plus an explicit compatibility-
    limitation note instead of a difference column. When scale
    alignment is eventually confirmed, only this function (and the
    SCALES_CONFIRMED_COMPATIBLE flag) need to change; callers don't."""
    rows = []
    for sector in comparison.sectors:
        rows.append(
            (
                sector.sector,
                _format_number(sector.predicted_value),
                _format_number(sector.official_pre_value),
                (
                    _format_number(sector.predicted_vs_pre_delta)
                    if SCALES_CONFIRMED_COMPATIBLE
                    else None
                ),
            )
        )
    return rows
