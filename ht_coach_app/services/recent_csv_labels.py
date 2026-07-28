import re
from datetime import date
from pathlib import Path

# Hattrick's own export always names the file "players_D_M_YYYY..."
# (day/month without leading zeros), e.g. "players_27_7_2026, 10_21_35.csv"
# or "players_27_7_2026__10_21_35.csv" depending on the browser.
_FILENAME_DATE_PATTERN = re.compile(
    r"players[_\s]*(\d{1,2})[_\s]+(\d{1,2})[_\s]+(\d{4})"
)

_WEEKDAY_NAMES_ES = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
]

_WEEKDAY_NAMES_EN = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def parse_csv_export_date(path):
    """Extracts the export date embedded in Hattrick's default players.csv
    filename. Returns a `date` or None if the filename doesn't match the
    expected pattern (e.g. the user renamed the file)."""
    name = Path(str(path or "")).name
    match = _FILENAME_DATE_PATTERN.search(name)
    if not match:
        return None

    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def format_recent_csv_label(path, language="es"):
    """Human-friendly label for a recent players.csv entry, e.g.
    'Lunes 2707'. Falls back to the bare filename when the date can't be
    parsed out of it."""
    parsed = parse_csv_export_date(path)
    if parsed is None:
        return Path(str(path or "")).name or str(path or "")

    weekday_names = (
        _WEEKDAY_NAMES_ES if language != "en" else _WEEKDAY_NAMES_EN
    )
    weekday = weekday_names[parsed.weekday()]
    return f"{weekday} {parsed.day:02d}{parsed.month:02d}"
