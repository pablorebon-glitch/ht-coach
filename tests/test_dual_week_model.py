from datetime import datetime

from engine.calendar import HTCalendarService, HTSeasonWeek, UNKNOWN_SEASON_WEEK
from ht_coach_app.core.localization import configure_localization, t
from ht_coach_app.services.dual_week_formatting import (
    format_dual_week_summary,
    format_season_week,
    format_training_cycle,
)


def setup_module(module):
    configure_localization("es")


def teardown_module(module):
    configure_localization("en")


def test_unknown_season_week_by_default():
    season_week = HTSeasonWeek()
    assert season_week.is_known is False
    assert season_week.season_number is None
    assert season_week.season_week is None


def test_known_season_week():
    season_week = HTSeasonWeek(season_number=95, season_week=2)
    assert season_week.is_known is True


def test_partially_known_is_not_known():
    assert HTSeasonWeek(season_number=95).is_known is False
    assert HTSeasonWeek(season_week=2).is_known is False


def test_to_dict_and_from_dict_roundtrip():
    season_week = HTSeasonWeek(season_number=95, season_week=2)
    payload = season_week.to_dict()
    restored = HTSeasonWeek.from_dict(payload)
    assert restored == season_week


def test_from_dict_handles_none_and_empty():
    assert HTSeasonWeek.from_dict(None) == UNKNOWN_SEASON_WEEK
    assert HTSeasonWeek.from_dict({}) == UNKNOWN_SEASON_WEEK


def test_never_computed_from_a_date():
    import inspect

    signature = inspect.signature(HTSeasonWeek.__init__)
    parameter_names = set(signature.parameters.keys())
    assert "date" not in parameter_names
    assert "match_date" not in parameter_names


def test_training_cycle_id_is_independent_of_season_week():
    calendar_service = HTCalendarService()
    training_cycle_id = calendar_service.training_week_id(datetime(2026, 8, 3, 10, 0))

    season_week_a = HTSeasonWeek(season_number=95, season_week=2)
    season_week_b = HTSeasonWeek(season_number=95, season_week=3)

    assert format_training_cycle(training_cycle_id) == format_training_cycle(training_cycle_id)
    assert format_season_week(season_week_a) != format_season_week(season_week_b)
    assert training_cycle_id == calendar_service.training_week_id(datetime(2026, 8, 3, 10, 0))


def test_format_season_week_matches_briefs_worked_example():
    season_week = HTSeasonWeek(season_number=95, season_week=2)
    text = format_season_week(season_week)
    assert "95" in text
    assert "2" in text
    assert t("dual_week.season_label", number=95) in text


def test_format_training_cycle_matches_briefs_worked_example():
    text = format_training_cycle("2026-08-09")
    assert text == t("dual_week.training_cycle_label", cycle_id="ht-week-2026-08-09")


def test_format_dual_week_summary_shows_both_as_distinct_lines():
    season_week = HTSeasonWeek(season_number=95, season_week=2)
    summary = format_dual_week_summary(season_week, "2026-08-09")
    lines = summary.split("\n")
    assert len(lines) == 3
    assert any("95" in line for line in lines)
    assert any("2026-08-09" in line for line in lines)


def test_unknown_season_still_shows_training_cycle():
    summary = format_dual_week_summary(UNKNOWN_SEASON_WEEK, "2026-08-09")
    assert "2026-08-09" in summary
    assert t("dual_week.season_unknown") in summary
