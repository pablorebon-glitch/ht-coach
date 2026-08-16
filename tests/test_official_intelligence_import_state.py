import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from datetime import date, timedelta

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
from ht_coach_app.services.match_intelligence_service import MatchIntelligenceAppService
from ht_coach_app.views.match_intelligence_page import MatchIntelligencePage


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def make_controller(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    service = MatchIntelligenceAppService(repository=repository)
    page = MatchIntelligencePage()
    controller = MatchIntelligenceController(page, service=service)
    return page, controller, repository


def test_no_evidence_defaults_to_pre_with_no_hint(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    record = find_or_create_provisional_record(
        repository, opponent_name="New Match", match_date="2026-09-01", competition_type="league"
    )
    controller._select_record(record.snapshot_id)

    default_slot, hint = controller._import_dialog_defaults()

    assert default_slot == "pre"
    assert hint == ""


def test_pre_exists_prioritizes_post_import(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    record = find_or_create_provisional_record(
        repository, opponent_name="PRE Only", match_date="2026-09-05", competition_type="league"
    )
    record = consolidate_with_official_pre(repository, record, OfficialRatingSnapshot(), "1")
    controller._select_record(record.snapshot_id)

    default_slot, hint = controller._import_dialog_defaults()

    assert default_slot == "post"
    assert hint


def test_post_only_future_match_offers_normal_pre(tmp_path):
    future = (date.today() + timedelta(days=5)).isoformat()
    page, controller, repository = make_controller(tmp_path)
    record = find_or_create_provisional_record(
        repository, opponent_name="Post Future", match_date=future, competition_type="league"
    )
    record = complete_with_official_post(repository, record, OfficialRatingSnapshot(), "3")
    controller._select_record(record.snapshot_id)

    default_slot, hint = controller._import_dialog_defaults()

    assert default_slot == "pre"
    assert "retrospectiv" not in hint.lower()


def test_post_only_past_match_hints_retrospective_flow(tmp_path):
    past = (date.today() - timedelta(days=5)).isoformat()
    page, controller, repository = make_controller(tmp_path)
    record = find_or_create_provisional_record(
        repository, opponent_name="Post Past", match_date=past, competition_type="league"
    )
    record = complete_with_official_post(repository, record, OfficialRatingSnapshot(), "4")
    controller._select_record(record.snapshot_id)

    default_slot, hint = controller._import_dialog_defaults()

    assert default_slot == "pre"
    assert "retrospectiv" in hint.lower()


def test_complete_record_hints_confirmation_required_before_overwrite(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    record = find_or_create_provisional_record(
        repository, opponent_name="Complete Match", match_date="2026-09-10", competition_type="league"
    )
    record = consolidate_with_official_pre(repository, record, OfficialRatingSnapshot(), "5")
    record = complete_with_official_post(repository, record, OfficialRatingSnapshot(), "5")
    controller._select_record(record.snapshot_id)

    default_slot, hint = controller._import_dialog_defaults()

    assert "confirmaci" in hint.lower() or "confirm" in hint.lower()


def test_no_selection_falls_back_to_pre_default(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    default_slot, hint = controller._import_dialog_defaults()
    assert default_slot == "pre"


def test_import_dialog_widget_respects_default_slot():
    from ht_coach_app.widgets.match_intelligence_import_dialog import (
        MatchIntelligenceImportDialog,
    )

    dialog = MatchIntelligenceImportDialog(default_slot="post", hint_text="test hint")
    assert dialog.slot() == "post"
    dialog_pre = MatchIntelligenceImportDialog(default_slot="pre")
    assert dialog_pre.slot() == "pre"


def test_import_dialog_shows_hint_label_only_when_provided():
    from ht_coach_app.widgets.match_intelligence_import_dialog import (
        MatchIntelligenceImportDialog,
    )

    with_hint = MatchIntelligenceImportDialog(hint_text="some hint")
    without_hint = MatchIntelligenceImportDialog(hint_text="")
    assert with_hint.layout().count() > without_hint.layout().count()
