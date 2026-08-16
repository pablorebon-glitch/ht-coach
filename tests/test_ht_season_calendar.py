from datetime import date

import pytest

from engine.calendar.season_calendar import (
    SeasonCalendarConfig,
    resolve_season_context,
    validate_season_calendar_config,
)
from engine.calendar.season_calendar_repository import SeasonCalendarRepository
from engine.calendar.season_recalculation import (
    preview_recalculation,
    recalculate_season_weeks,
)
from engine.history.provisional_record import find_or_create_provisional_record
from engine.history.repository import HistoricalMatchRepository


def _config():
    return SeasonCalendarConfig(season_number=95, season_start_date="2026-07-27", total_weeks=16)


def test_no_configuration_returns_unconfigured():
    result = resolve_season_context(date(2026, 8, 9), SeasonCalendarConfig())
    assert result.is_known is False
    assert result.confidence == "unconfigured"


def test_configured_monday_resolves_to_week_1():
    result = resolve_season_context(date(2026, 7, 27), _config())
    assert result.season_week.season_number == 95
    assert result.season_week.season_week == 1
    assert result.confidence == "configured"


def test_sunday_remains_in_same_competitive_week():
    result = resolve_season_context(date(2026, 8, 2), _config())
    assert result.season_week.season_week == 1


def test_following_monday_becomes_week_2():
    result = resolve_season_context(date(2026, 8, 3), _config())
    assert result.season_week.season_week == 2


def test_last_week_of_configured_season_resolves_correctly():
    result = resolve_season_context(date(2026, 11, 9), _config())
    assert result.season_week.season_week == 16


def test_date_far_beyond_configured_season_is_unknown():
    result = resolve_season_context(date(2028, 1, 1), _config())
    assert result.is_known is False
    assert result.confidence == "unknown"


def test_date_far_before_configured_season_is_unknown():
    result = resolve_season_context(date(2024, 1, 1), _config())
    assert result.is_known is False


def test_one_season_before_resolves_deterministically():
    result = resolve_season_context(date(2026, 6, 1), _config())
    assert result.season_week.season_number == 94
    assert result.confidence == "inferred_adjacent"


def test_one_season_after_resolves_deterministically():
    result = resolve_season_context(date(2027, 2, 1), _config())
    assert result.season_week.season_number == 96
    assert result.confidence == "inferred_adjacent"


def test_string_date_is_accepted():
    result = resolve_season_context("2026-08-03", _config())
    assert result.season_week.season_week == 2


def test_invalid_date_string_is_unknown():
    result = resolve_season_context("not-a-date", _config())
    assert result.is_known is False
    assert result.confidence == "unknown"


def test_never_calls_datetime_now():
    import inspect

    from engine.calendar import season_calendar as module

    source = inspect.getsource(module)
    assert "datetime.now(" not in source
    assert ".today()" not in source


def test_config_roundtrips_through_repository(tmp_path):
    repository = SeasonCalendarRepository(tmp_path / "season.json")
    config = _config()
    repository.save(config)

    loaded = repository.load()
    assert loaded.season_number == 95
    assert loaded.season_start_date == "2026-07-27"
    assert loaded.total_weeks == 16
    assert loaded.schema_version == 1
    assert loaded.updated_at


def test_config_writes_schema_versioned_canonical_fields(tmp_path):
    repository = SeasonCalendarRepository(tmp_path / "season.json")
    repository.save(_config())

    import json

    payload = json.loads((tmp_path / "season.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["current_season_number"] == 95
    assert payload["current_season_start_date"] == "2026-07-27"
    assert payload["competitive_weeks"] == 16


def test_config_loads_canonical_field_names(tmp_path):
    import json

    path = tmp_path / "season.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "current_season_number": 95,
                "current_season_start_date": "2026-07-27",
                "competitive_weeks": 16,
                "timezone": "America/Argentina/Buenos_Aires",
            }
        ),
        encoding="utf-8",
    )

    loaded = SeasonCalendarRepository(path).load()

    assert loaded.current_season_number == 95
    assert loaded.current_season_start_date == "2026-07-27"
    assert loaded.competitive_weeks == 16
    assert loaded.timezone == "America/Argentina/Buenos_Aires"


def test_validate_config_warns_when_start_date_is_not_monday():
    errors, warnings = validate_season_calendar_config(
        SeasonCalendarConfig(
            season_number=95,
            season_start_date="2026-07-28",
            total_weeks=16,
            timezone="America/Argentina/Buenos_Aires",
        )
    )
    assert errors == ()
    assert warnings == ("season_start_date_not_monday",)


def test_validate_config_rejects_invalid_timezone():
    errors, warnings = validate_season_calendar_config(
        SeasonCalendarConfig(
            season_number=95,
            season_start_date="2026-07-27",
            total_weeks=16,
            timezone="Nowhere/Invalid",
        )
    )
    assert "timezone_invalid" in errors


def test_repository_returns_unconfigured_when_nothing_saved(tmp_path):
    repository = SeasonCalendarRepository(tmp_path / "season.json")
    config = repository.load()
    assert config.is_configured is False


@pytest.fixture()
def repository(tmp_path):
    return HistoricalMatchRepository(tmp_path / "snapshots.json")


def test_auto_fill_only_touches_records_with_no_existing_value(repository):
    r1 = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    r2 = find_or_create_provisional_record(
        repository, opponent_name="Torres FC", match_date="2026-08-03",
        competition_type="league", season_number=90, season_week=1,
    )

    report = recalculate_season_weeks(repository, _config(), force=False)

    assert report.updated_count == 1
    assert repository.get(r1.snapshot_id).ht_season_number == 95
    assert repository.get(r2.snapshot_id).ht_season_number == 90


def test_forced_recalculation_overwrites_existing_values(repository):
    r2 = find_or_create_provisional_record(
        repository, opponent_name="Torres FC", match_date="2026-08-03",
        competition_type="league", season_number=90, season_week=1,
    )

    report = recalculate_season_weeks(repository, _config(), force=True)

    assert report.updated_count == 1
    assert repository.get(r2.snapshot_id).ht_season_number == 95
    assert repository.get(r2.snapshot_id).ht_season_week == 2


def test_recalculation_skips_records_with_no_date(repository):
    from engine.history.models import HistoricalMatchSnapshot, MatchContext

    repository.save(HistoricalMatchSnapshot(snapshot_id="no-date", match_context=MatchContext()))

    report = recalculate_season_weeks(repository, _config(), force=True)

    assert report.updated_count == 0


def test_recalculation_reports_records_it_could_not_resolve(repository):
    find_or_create_provisional_record(
        repository, opponent_name="Far Future Rival", match_date="2030-01-01", competition_type="league"
    )

    report = recalculate_season_weeks(repository, _config(), force=True)

    assert report.updated_count == 0
    assert len(report.skipped_unknown) == 1


def test_preview_never_mutates_anything(repository):
    r2 = find_or_create_provisional_record(
        repository, opponent_name="Torres FC", match_date="2026-08-03",
        competition_type="league", season_number=90, season_week=1,
    )

    preview_recalculation(repository, _config())

    assert repository.get(r2.snapshot_id).ht_season_number == 90


def test_preview_reports_how_many_records_would_change(repository):
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    find_or_create_provisional_record(
        repository, opponent_name="Torres FC", match_date="2030-01-01", competition_type="league"
    )

    preview = preview_recalculation(repository, _config())

    assert len(preview) == 1


def test_settings_page_season_calendar_form_populates(tmp_path):
    import pytest as _pytest

    QApplication = _pytest.importorskip("PySide6.QtWidgets").QApplication
    QApplication.instance() or QApplication([])

    from ht_coach_app.views.settings_page import SettingsPage

    page = SettingsPage()
    config = SeasonCalendarConfig(season_number=95, season_start_date="2026-07-27", total_weeks=16)
    page.set_season_calendar_config(config)

    assert page.season_number_spin.value() == 95
    assert page.season_start_date_edit.date().toString("yyyy-MM-dd") == "2026-07-27"
    assert page.season_total_weeks_spin.value() == 16


def test_settings_page_save_emits_current_form_values(tmp_path):
    import pytest as _pytest

    QApplication = _pytest.importorskip("PySide6.QtWidgets").QApplication
    QApplication.instance() or QApplication([])

    from PySide6.QtCore import QDate

    from ht_coach_app.views.settings_page import SettingsPage

    page = SettingsPage()
    page.season_number_spin.setValue(95)
    page.season_start_date_edit.setDate(QDate(2026, 7, 27))
    page.season_total_weeks_spin.setValue(16)

    calls = []
    page.season_calendar_save_requested.connect(lambda *args: calls.append(args))
    page._emit_season_calendar_save()

    assert calls == [(95, "2026-07-27", 16)]


def test_settings_page_cancel_reverts_unsaved_edits(tmp_path):
    import pytest as _pytest

    QApplication = _pytest.importorskip("PySide6.QtWidgets").QApplication
    QApplication.instance() or QApplication([])

    from ht_coach_app.views.settings_page import SettingsPage

    page = SettingsPage()
    config = SeasonCalendarConfig(season_number=95, season_start_date="2026-07-27", total_weeks=16)
    page.set_season_calendar_config(config)

    page.season_number_spin.setValue(99)  # unsaved edit
    page._reload_season_calendar_form()

    assert page.season_number_spin.value() == 95


def test_full_config_to_recalculation_flow(tmp_path):
    """End-to-end: save a config through the page, then use it to
    recalculate real records in the repository."""
    repository_path = tmp_path / "season.json"
    season_repository = SeasonCalendarRepository(repository_path)
    season_repository.save(
        SeasonCalendarConfig(season_number=95, season_start_date="2026-07-27", total_weeks=16)
    )

    history_repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    find_or_create_provisional_record(
        history_repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )

    config = season_repository.load()
    report = recalculate_season_weeks(history_repository, config, force=False)

    assert report.updated_count == 1
    updated = history_repository.list_all()[0]
    assert updated.ht_season_number == 95
    assert updated.ht_season_week == 2
