import pytest
from datetime import datetime

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.calendar import HTCalendarService
from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.provisional_record import (
    complete_with_official_post,
    consolidate_with_official_pre,
    find_or_create_provisional_record,
)
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.controllers.match_intelligence_controller import (
    MatchIntelligenceController,
)
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.services.ht_week_context_provider import (
    get_calendar_service,
    set_calendar_service,
)
from ht_coach_app.services.match_intelligence_service import MatchIntelligenceAppService
from ht_coach_app.views.match_intelligence_page import MatchIntelligencePage


@pytest.fixture(autouse=True)
def _qt_app():
    previous_calendar = get_calendar_service()
    set_calendar_service(
        HTCalendarService(
            clock=lambda: datetime(2026, 8, 3, 12, 0, 0)
        )
    )
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    set_calendar_service(previous_calendar)
    configure_localization("en")


def make_controller(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    service = MatchIntelligenceAppService(repository=repository)
    page = MatchIntelligencePage()
    controller = MatchIntelligenceController(page, service=service)
    return page, controller, repository


def test_selector_shows_canonical_match_identity(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    consolidate_with_official_pre(
        repository, record, OfficialRatingSnapshot(team_name="Hit'em up"), "770918226"
    )
    controller.refresh()

    options = [page.record_selector_combo.itemText(i) for i in range(page.record_selector_combo.count())]
    assert "Hit'em up vs. CA Chaco" in options


def test_selector_never_includes_a_status_word(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    consolidated = consolidate_with_official_pre(
        repository, record, OfficialRatingSnapshot(team_name="Hit'em up"), "770918226"
    )
    complete_with_official_post(
        repository, consolidated, OfficialRatingSnapshot(team_name="Hit'em up"), "770918226"
    )
    controller.refresh()

    options = [page.record_selector_combo.itemText(i) for i in range(page.record_selector_combo.count())]
    forbidden_words = ["Completo", "PRE oficial importado", "Planificado", "Incompleto", "POST"]
    for option in options:
        for word in forbidden_words:
            assert word not in option


def test_selector_uses_default_team_identity_when_team_name_unknown(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    find_or_create_provisional_record(
        repository, opponent_name="Torres FC", match_date="2026-08-16",
        competition_type="league", season_number=95, season_week=3,
    )
    controller.refresh()

    options = [page.record_selector_combo.itemText(i) for i in range(page.record_selector_combo.count())]
    assert "Hit'em up vs. Torres FC" in options


def test_metadata_shown_separately_below_the_selector(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    consolidate_with_official_pre(
        repository, record, OfficialRatingSnapshot(team_name="Hit'em up"), "770918226"
    )
    controller._select_record(record.snapshot_id)

    text = page.record_identity_label.text()
    assert "Temporada HT 95" in text
    assert "Semana competitiva 2" in text
    assert "2026-08-09" in text
    assert "Liga" in text
    assert "770918226" in text
    assert "PRE oficial importado" in text


def test_multiple_records_produce_distinct_readable_options(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    find_or_create_provisional_record(
        repository, opponent_name="Santa Cruz Club", match_date="2026-07-26",
        competition_type="friendly", season_number=95, season_week=1,
    )
    find_or_create_provisional_record(
        repository, opponent_name="pata2008", match_date="2026-08-02",
        competition_type="cup", season_number=95, season_week=1,
    )
    controller.refresh()

    options = [page.record_selector_combo.itemText(i) for i in range(page.record_selector_combo.count())]
    assert len(options) == 3
    assert len(set(options)) == 3
