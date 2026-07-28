from __future__ import annotations

SECTOR_LABELS = {
    "midfield": "Midfield",
    "right_defense": "Right Defense",
    "central_defense": "Central Defense",
    "left_defense": "Left Defense",
    "right_attack": "Right Attack",
    "central_attack": "Central Attack",
    "left_attack": "Left Attack",
}


def format_signed(value, decimals=2):
    """'+0.50' / '-0.25' / '—' for a missing value. Plain formatting
    only — no wording, no explanation, no recommendation."""
    if value is None:
        return "\u2014"
    return f"{value:+.{decimals}f}"


def format_sector_rows(result):
    """[(label, formatted_delta), ...] for each reported sector, in
    the engine's canonical order."""
    return [
        (SECTOR_LABELS.get(sector.sector, sector.sector), format_signed(sector.absolute_delta))
        for sector in result.sectors
    ]


def format_overall_row(result):
    """('Overall', formatted_evolution_score)."""
    return ("Overall", format_signed(result.evolution_score))


def format_evolution_summary(result):
    """Full minimal display payload for a 'Compared with ...' card:
    the sector rows followed by the Overall row, exactly the shape
    shown in the Historical Evolution Engine brief. No text is
    generated beyond the fixed sector labels above."""
    return format_sector_rows(result) + [format_overall_row(result)]
