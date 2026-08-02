import pytest

from engine.history.provisional_record import find_or_create_provisional_record
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.services.match_display_formatter import (
    format_match_identity,
    format_match_selector_option,
)


def test_home_venue_shows_our_team_first():
    assert format_match_identity("Hit'em up", "pata2008", "home") == "Hit'em up vs. pata2008"


def test_away_venue_shows_opponent_first():
    assert format_match_identity("Hit'em up", "pata2008", "away") == "pata2008 vs. Hit'em up"


def test_neutral_venue_appends_qualifier():
    assert format_match_identity("Hit'em up", "pata2008", "neutral") == "Hit'em up vs. pata2008 \u00b7 Neutral"


def test_unknown_venue_defaults_to_our_team_first_no_qualifier():
    assert format_match_identity("Hit'em up", "pata2008", "unknown") == "Hit'em up vs. pata2008"


def test_venue_role_accepts_enum_like_objects():
    class FakeEnum:
        value = "away"

    assert format_match_identity("Hit'em up", "pata2008", FakeEnum()) == "pata2008 vs. Hit'em up"


def test_identity_never_infers_venue_from_string_order():
    assert format_match_identity("pata2008", "Hit'em up") == "pata2008 vs. Hit'em up"


def test_missing_names_use_placeholder_never_crash():
    assert format_match_identity("", "", "home") == "? vs. ?"


def test_selector_option_matches_briefs_own_example():
    assert format_match_selector_option("Hit'em up", "pata2008") == "pata2008 - Hit'em up"


def test_selector_option_never_duplicates_fragments():
    result = format_match_selector_option("Hit'em up", "pata2008")
    assert result.count("Hit'em up") == 1
    assert result.count("pata2008") == 1


def test_selector_option_falls_back_to_opponent_only_when_team_unknown():
    assert format_match_selector_option("", "pata2008") == "pata2008"


def test_selector_option_never_produces_the_briefs_own_bug_example():
    result = format_match_selector_option("Hit'em up", "pata2008")
    assert result != "pata2008 - Hit'em up - pata2008 - Hit'em up"
    assert result.count(" - ") == 1


@pytest.fixture()
def repository(tmp_path):
    return HistoricalMatchRepository(tmp_path / "snapshots.json")


def test_venue_role_persists_on_the_canonical_record(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="pata2008", match_date="2026-08-09",
        competition_type="league", home_away="home",
    )
    assert record.match_context.home_away.value == "home"


def test_venue_role_defaults_to_unknown_when_not_provided(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="pata2008", match_date="2026-08-09",
        competition_type="league",
    )
    assert record.match_context.home_away.value == "unknown"


def test_venue_role_never_guessed_from_empty_string(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="pata2008", match_date="2026-08-09",
        competition_type="league", home_away="",
    )
    assert record.match_context.home_away.value == "unknown"


def test_match_page_venue_role_selector(monkeypatch):
    import pytest as _pytest

    QApplication = _pytest.importorskip("PySide6.QtWidgets").QApplication
    QApplication.instance() or QApplication([])

    from ht_coach_app.views.match_page import MatchPage

    page = MatchPage()
    assert page.venue_role() == "unknown"

    page.set_venue_role("home")
    assert page.venue_role() == "home"

    page.set_venue_role("away")
    assert page.venue_role() == "away"

    page.set_venue_role("neutral")
    assert page.venue_role() == "neutral"


def test_match_page_venue_role_all_four_options_present():
    import pytest as _pytest

    QApplication = _pytest.importorskip("PySide6.QtWidgets").QApplication
    QApplication.instance() or QApplication([])

    from ht_coach_app.views.match_page import MatchPage

    page = MatchPage()
    values = {page.venue_role_combo.itemData(i) for i in range(page.venue_role_combo.count())}
    assert values == {"home", "away", "neutral", "unknown"}
