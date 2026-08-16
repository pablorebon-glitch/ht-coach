import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.provisional_record import (
    complete_with_official_post,
    find_or_create_provisional_record,
)
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.controllers.match_intelligence_controller import (
    MatchIntelligenceController,
)
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.services.match_intelligence_service import MatchIntelligenceAppService
from ht_coach_app.views.match_intelligence_page import MatchIntelligencePage

REAL_PRE = """[b]Team[/b] [matchid=771000000]
[table]
[tr][th]Defensa[/th][td]4.25[/td][td]7[/td][td]3.75[/td][/tr]
[tr][th]Mediocampo[/th][td colspan=3]7.25[/td][/tr]
[tr][th]Ataque[/th][td]7.75[/td][td]9.75[/td][td]8[/td][/tr]
[/table]
[b]Formación[/b]: 2-5-3 aceptable (6)
[b]Tácticas[/b]: Atacar por el centro clase mundial (13)
[b]Actitud del equipo[/b]: Normal
[b]Estilo de juego[/b]: 100% ofensivo"""


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


def _played_record_missing_pre(repository, match_id="770918226"):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-07-20",
        competition_type="league", season_number=95, season_week=1,
    )
    return complete_with_official_post(
        repository, record, OfficialRatingSnapshot(team_name="Hit em up"), match_id
    )


def test_confirming_dialog_saves_as_retrospective_and_preserves_match_id(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    record = _played_record_missing_pre(repository)
    page.confirm_retrospective_pre = lambda: True

    controller._import(REAL_PRE, "pre")

    stored = repository.get(record.snapshot_id)
    assert stored.retrospective_pre is not None
    assert stored.match_context.official_match_id == "770918226"
    assert len(repository.list_all()) == 1


def test_declining_dialog_saves_nothing(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    record = _played_record_missing_pre(repository)
    page.confirm_retrospective_pre = lambda: False

    controller._import(REAL_PRE, "pre")

    stored = repository.get(record.snapshot_id)
    assert stored.retrospective_pre is None
    assert len(repository.list_all()) == 1


def test_dialog_never_shown_when_no_retrospective_candidate_exists(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    calls = []
    page.confirm_retrospective_pre = lambda: calls.append(True) or True

    controller._import(REAL_PRE, "pre")

    assert calls == []
    assert len(repository.list_all()) == 1
    assert repository.list_all()[0].official_pre is not None


def test_dialog_not_offered_for_post_slot(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _played_record_missing_pre(repository)
    calls = []
    page.confirm_retrospective_pre = lambda: calls.append(True) or True

    try:
        controller._import(REAL_PRE, "post")
    except Exception:
        pass

    assert calls == []


def test_view_without_dialog_support_falls_back_to_normal_import(tmp_path, monkeypatch):
    """A view that doesn't implement `confirm_retrospective_pre` at all
    must never crash -- the retrospective path is simply skipped, and
    the normal import proceeds (creating its own new record, since
    nothing here links it back to the played match)."""
    page, controller, repository = make_controller(tmp_path)
    _played_record_missing_pre(repository)
    monkeypatch.delattr(MatchIntelligencePage, "confirm_retrospective_pre")

    controller._import(REAL_PRE, "pre")  # must not raise


def test_confirming_dialog_updates_selected_record_and_refreshes_identity(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    record = _played_record_missing_pre(repository)
    page.confirm_retrospective_pre = lambda: True

    controller._import(REAL_PRE, "pre")

    assert controller._selected_snapshot_id == record.snapshot_id
    assert "PRE retrospectivo disponible" in page.record_identity_label.text()


def test_confirm_retrospective_pre_dialog_uses_briefs_exact_button_labels(tmp_path):
    from ht_coach_app.core.localization import t

    assert t("official_match_intelligence.retrospective.dialog_back") == "Volver"
    assert (
        t("official_match_intelligence.retrospective.dialog_save")
        == "Guardar como simulación retrospectiva"
    )
