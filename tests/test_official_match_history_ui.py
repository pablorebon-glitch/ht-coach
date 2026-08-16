import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.provisional_record import (
    consolidate_with_official_pre,
    find_or_create_provisional_record,
)
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.controllers.match_intelligence_controller import (
    MatchIntelligenceController,
)
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.services.match_intelligence_service import MatchIntelligenceAppService
from ht_coach_app.views.match_intelligence_page import MatchIntelligencePage


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def _seed(repository):
    r1 = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09",
        competition_type="league", season_number=95, season_week=2,
    )
    consolidate_with_official_pre(
        repository, r1, OfficialRatingSnapshot(team_name="Hit em up"), "770918226"
    )
    r2 = find_or_create_provisional_record(
        repository, opponent_name="Torres FC", match_date="2026-08-02",
        competition_type="league", season_number=95, season_week=1,
    )
    r3 = find_or_create_provisional_record(
        repository, opponent_name="Boca Deportivo", match_date="2026-07-20",
        competition_type="cup", season_number=94, season_week=16,
    )
    return r1, r2, r3


def make_controller(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    service = MatchIntelligenceAppService(repository=repository)
    page = MatchIntelligencePage()
    controller = MatchIntelligenceController(page, service=service)
    return page, controller, repository


def test_season_filter_lists_distinct_seasons(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _seed(repository)
    controller.refresh()

    seasons = [page.season_filter_combo.itemData(i) for i in range(page.season_filter_combo.count())]
    assert None in seasons
    assert 95 in seasons
    assert 94 in seasons


def test_record_selector_shows_all_records_for_active_filter(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _seed(repository)
    controller.refresh()

    assert page.record_selector_combo.count() == 3


def test_changing_season_filter_narrows_record_options(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _seed(repository)
    controller.refresh()

    controller._change_season_filter(95)

    assert page.record_selector_combo.count() == 2


def test_record_identity_matches_briefs_worked_example(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    r1, r2, r3 = _seed(repository)
    controller._select_record(r1.snapshot_id)

    text = page.record_identity_label.text()
    assert "CA Chaco" in text
    assert "Temporada HT 95" in text
    assert "Semana competitiva 2" in text
    assert "770918226" in text
    assert "PRE oficial importado" in text


def test_navigate_previous_moves_to_older_record_in_active_filter(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    r1, r2, r3 = _seed(repository)
    controller._change_season_filter(95)
    controller._select_record(r1.snapshot_id)  # r1 (CA Chaco, 08/09) is the newest

    controller._navigate_record("previous")

    assert controller._selected_snapshot_id == r2.snapshot_id  # Torres FC, 08/02, older


def test_navigate_next_moves_to_newer_record_in_active_filter(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    r1, r2, r3 = _seed(repository)
    controller._change_season_filter(95)
    controller._select_record(r2.snapshot_id)  # r2 (Torres FC, 08/02) is the oldest of the two

    controller._navigate_record("next")

    assert controller._selected_snapshot_id == r1.snapshot_id  # CA Chaco, 08/09, newer


def test_navigate_never_crosses_active_season_filter(tmp_path):
    """Starting at the oldest record *within* season 95, clicking
    "previous" (older) must never cross into season 94 -- it must stay
    put instead."""
    page, controller, repository = make_controller(tmp_path)
    r1, r2, r3 = _seed(repository)
    controller._change_season_filter(95)
    controller._select_record(r2.snapshot_id)  # oldest within the season-95 filter

    controller._navigate_record("previous")

    assert controller._selected_snapshot_id == r2.snapshot_id


def test_selecting_a_record_from_dropdown_refreshes_identity(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    r1, r2, r3 = _seed(repository)

    controller._select_record(r2.snapshot_id)

    assert "Torres FC" in page.record_identity_label.text()


def test_navigation_buttons_reflect_position_in_filtered_list(tmp_path):
    """r1 (CA Chaco, 08/09) is the newest record in the season-95
    filter: there's an older record to move to (previous is enabled),
    but nothing newer (next is disabled)."""
    page, controller, repository = make_controller(tmp_path)
    r1, r2, r3 = _seed(repository)
    controller._change_season_filter(95)
    controller._select_record(r1.snapshot_id)

    assert page.record_nav_previous_button.isEnabled() is True
    assert page.record_nav_next_button.isEnabled() is False
