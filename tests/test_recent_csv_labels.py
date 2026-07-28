from datetime import date

from ht_coach_app.services.recent_csv_labels import (
    format_recent_csv_label,
    parse_csv_export_date,
)


def test_parses_comma_separated_hattrick_filename():
    assert parse_csv_export_date(
        "players_27_7_2026, 10_21_35.csv"
    ) == date(2026, 7, 27)


def test_parses_double_underscore_hattrick_filename():
    assert parse_csv_export_date(
        "players_27_7_2026__10_21_35.csv"
    ) == date(2026, 7, 27)


def test_parses_full_windows_path():
    assert parse_csv_export_date(
        r"C:\Users\pablo\Downloads\players_27_7_2026, 10_21_35.csv"
    ) == date(2026, 7, 27)


def test_returns_none_for_unrecognized_filename():
    assert parse_csv_export_date("my_renamed_export.csv") is None


def test_label_format_matches_weekday_and_ddmm():
    # July 27, 2026 is a Monday.
    label = format_recent_csv_label("players_27_7_2026, 10_21_35.csv")
    assert label == "Lunes 2707"


def test_label_falls_back_to_filename_when_unparseable():
    label = format_recent_csv_label("my_renamed_export.csv")
    assert label == "my_renamed_export.csv"


def test_label_respects_english_language():
    label = format_recent_csv_label(
        "players_27_7_2026, 10_21_35.csv", language="en"
    )
    assert label == "Monday 2707"
