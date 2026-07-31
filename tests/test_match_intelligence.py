import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QApplication = QtWidgets.QApplication
QLabel = QtWidgets.QLabel

from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.controllers.match_intelligence_controller import (
    MatchIntelligenceController,
)
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.services.match_intelligence_service import MatchIntelligenceAppService
from ht_coach_app.views.match_intelligence_page import MatchIntelligencePage
from tests.test_official_rating_pre_post_formats import REAL_HF02_POST, REAL_HF02_PRE

REAL_SAMPLE = """[b]Hit'em up - Torres Futbol Club[/b] [matchid=770131822]

[table]
[tr][th]Defensa[/th][td align=center]4.25[/td][td align=center]7[/td][td align=center]3.75[/td][/tr]
[tr][th]Mediocampo[/th][td colspan=3 align=center]7.25[/td][/tr]
[tr][th]Ataque[/th][td align=center]7.75[/td][td align=center]9.75[/td][td align=center]8[/td][/tr]
[/table]

[b]Formación[/b]: 2-5-3 aceptable (6)
[b]Tácticas[/b]: Atacar por el centro clase mundial (13)
[b]Actitud del equipo[/b]: Normal
[b]Estilo de juego[/b]: 100% ofensivo"""

REAL_SAMPLE_DIFFERENT_MIDFIELD = REAL_SAMPLE.replace("7.25", "7.50")
POST_DIFFERENT_MATCH = """
[b]Other Match[/b] [matchid=999999999]
Midfield: 7.50
Right Defense: 4.25
Central Defense: 7.00
Left Defense: 3.75
Right Attack: 8.00
Central Attack: 9.75
Left Attack: 7.75
"""


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
    return page, controller, service


def test_latest_snapshot_is_none_when_nothing_imported(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    service = MatchIntelligenceAppService(repository=repository)
    assert service.latest_snapshot_with_official_data() is None


def test_import_ratings_then_latest_snapshot_reflects_it(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    service = MatchIntelligenceAppService(repository=repository)
    service.import_ratings(REAL_SAMPLE, slot="pre")
    snapshot = service.latest_snapshot_with_official_data()
    assert snapshot.official_pre.ratings.midfield == 7.25


def test_format_official_summary_matches_hattrick_notation(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    service = MatchIntelligenceAppService(repository=repository)
    service.import_ratings(REAL_SAMPLE, slot="pre")
    snapshot = service.latest_snapshot_with_official_data()
    text = service.format_official_summary(snapshot.official_pre)
    assert "4.25 | 7.00 | 3.75" in text


def test_prediction_comparison_rows_cover_seven_sectors(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    service = MatchIntelligenceAppService(repository=repository)
    service.import_ratings(REAL_SAMPLE, slot="pre")
    snapshot = service.latest_snapshot_with_official_data()
    rows = service.prediction_comparison_rows(snapshot)
    assert len(rows) == 7


def test_scales_not_confirmed_compatible():
    repository_free_service = MatchIntelligenceAppService(repository=None)
    assert repository_free_service.scales_confirmed_compatible is False


def test_empty_state_shown_with_no_data(tmp_path):
    page, controller, service = make_controller(tmp_path)
    assert page.empty_state_label.isVisible() or not page._sections_container.isVisible()


def t_not_imported(page):
    from ht_coach_app.core.localization import t

    return t("official_match_intelligence.not_imported")


def test_importing_pre_populates_pre_section_only(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import(REAL_SAMPLE, "pre")

    assert "4.25 | 7.00 | 3.75" in page.pre_label.text()
    assert page.post_label.text() == t_not_imported(page)


def test_spanish_match_intelligence_uses_localized_sections_and_missing_post(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import(REAL_SAMPLE, "pre")

    texts = "\n".join(label.text() for label in page.findChildren(QLabel))

    assert "PRE oficial" in texts
    assert "POST oficial" in texts
    assert "Comparación" in texts
    assert "Conclusiones" in texts
    assert "Aún no se importó el resumen POST." in page.sector_label.text()
    assert "Official PRE" not in texts
    assert "Official POST" not in texts
    assert "POST ? | -" not in texts


def test_importing_post_populates_post_section(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import(REAL_SAMPLE, "pre")
    controller._import(REAL_SAMPLE_DIFFERENT_MIDFIELD, "post")

    assert "4.25 | 7.00 | 3.75" in page.pre_label.text()
    assert "7.50" in page.post_label.text()


def test_post_with_different_match_id_prompts_manual_confirmation(tmp_path, monkeypatch):
    page, controller, service = make_controller(tmp_path)
    controller._import(REAL_SAMPLE, "pre")

    from ht_coach_app.widgets.match_id_mismatch_dialog import MatchIdMismatchDialog

    prompts = []
    monkeypatch.setattr(
        MatchIdMismatchDialog,
        "request_match_id",
        staticmethod(lambda pre, post, parent=None: prompts.append((pre, post)) or None),
    )

    controller._import(POST_DIFFERENT_MATCH, "post")

    snapshot = service.latest_snapshot_with_official_data()
    assert prompts == [("770131822", "999999999")]
    assert snapshot.official_pre is not None
    assert snapshot.official_post is None


def test_real_post_parses_before_match_id_mismatch_dialog(tmp_path, monkeypatch):
    page, controller, service = make_controller(tmp_path)
    controller._import(REAL_HF02_PRE, "pre")

    from ht_coach_app.widgets.match_id_mismatch_dialog import MatchIdMismatchDialog

    prompts = []
    monkeypatch.setattr(
        MatchIdMismatchDialog,
        "request_match_id",
        staticmethod(lambda pre, post, parent=None: prompts.append((pre, post)) or None),
    )

    controller._import(REAL_HF02_POST, "post")

    snapshot = service.latest_snapshot_with_official_data()
    assert prompts == [("770918226", "770725689")]
    assert snapshot.official_pre is not None
    assert snapshot.official_post is None
    assert "faltan sectores" not in page.empty_state_label.text().lower()


def test_editing_mismatched_match_id_associates_pre_and_post(tmp_path, monkeypatch):
    page, controller, service = make_controller(tmp_path)
    controller._import(REAL_SAMPLE, "pre")

    from ht_coach_app.widgets.match_id_mismatch_dialog import MatchIdMismatchDialog

    monkeypatch.setattr(
        MatchIdMismatchDialog,
        "request_match_id",
        staticmethod(lambda pre, post, parent=None: pre),
    )

    controller._import(POST_DIFFERENT_MATCH, "post")

    snapshot = service.latest_snapshot_with_official_data()
    assert snapshot.official_pre.hattrick_match_id == "770131822"
    assert snapshot.official_post.hattrick_match_id == "770131822"
    assert snapshot.provenance.imported_match_id == "770131822"


def test_apply_with_equal_ids_commits_pending_post_and_refreshes_ui(tmp_path, monkeypatch):
    page, controller, service = make_controller(tmp_path)
    controller._import(REAL_HF02_PRE, "pre")

    from ht_coach_app.widgets.match_id_mismatch_dialog import MatchIdMismatchDialog

    monkeypatch.setattr(
        MatchIdMismatchDialog,
        "request_match_id",
        staticmethod(lambda pre, post, parent=None: pre),
    )

    controller._import(REAL_HF02_POST, "post")

    snapshot = service.latest_snapshot_with_official_data()
    assert snapshot.official_post is not None
    assert snapshot.official_post.hattrick_match_id == snapshot.official_pre.hattrick_match_id
    assert "6.00" in page.post_label.text()
    assert "PRE" in page.sector_label.text()
    assert "POST" in page.sector_label.text()


def test_controller_receives_corrected_id_once_for_pending_post(tmp_path, monkeypatch):
    class CountingService(MatchIntelligenceAppService):
        def __init__(self, repository):
            super().__init__(repository=repository)
            self.associations = []

        def associate_post_after_match_id_confirmation(self, *args, **kwargs):
            self.associations.append((args, kwargs))
            return super().associate_post_after_match_id_confirmation(*args, **kwargs)

    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    service = CountingService(repository)
    page = MatchIntelligencePage()
    controller = MatchIntelligenceController(page, service=service)
    controller._import(REAL_HF02_PRE, "pre")

    from ht_coach_app.widgets.match_id_mismatch_dialog import MatchIdMismatchDialog

    monkeypatch.setattr(
        MatchIdMismatchDialog,
        "request_match_id",
        staticmethod(lambda pre, post, parent=None: "770918226"),
    )

    controller._import(REAL_HF02_POST, "post")

    assert len(service.associations) == 1
    args, kwargs = service.associations[0]
    assert args[2] == "770918226"
    snapshot = service.latest_snapshot_with_official_data()
    assert snapshot.official_post is not None


def test_scale_limitation_note_shown_never_a_misleading_delta(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import(REAL_SAMPLE, "pre")

    limitation_text = page.internal_diagnostic_limitation_label.text()
    assert "escala" in limitation_text.lower() or "scale" in limitation_text.lower()

    text = page.prediction_label.text()
    assert "| -" in text or text.count("|") >= 7


def test_replacing_pre_requires_confirmation(tmp_path, monkeypatch):
    page, controller, service = make_controller(tmp_path)
    controller._import(REAL_SAMPLE, "pre")

    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.No))
    controller._import(REAL_SAMPLE_DIFFERENT_MIDFIELD, "pre")

    snapshot = service.latest_snapshot_with_official_data()
    assert snapshot.official_pre.ratings.midfield == 7.25


def test_confirming_replace_overwrites_pre(tmp_path, monkeypatch):
    page, controller, service = make_controller(tmp_path)
    controller._import(REAL_SAMPLE, "pre")

    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    controller._import(REAL_SAMPLE_DIFFERENT_MIDFIELD, "pre")

    snapshot = service.latest_snapshot_with_official_data()
    assert snapshot.official_pre.ratings.midfield == 7.50


def test_refresh_reflects_import_made_through_the_shared_service(tmp_path):
    page, controller, service = make_controller(tmp_path)
    service.import_ratings(REAL_SAMPLE, slot="pre")

    controller.refresh()
    assert "4.25 | 7.00 | 3.75" in page.pre_label.text()


def test_show_event_triggers_refresh(tmp_path):
    page, controller, service = make_controller(tmp_path)
    service.import_ratings(REAL_SAMPLE, slot="pre")

    from PySide6.QtGui import QShowEvent

    page.showEvent(QShowEvent())
    assert "4.25 | 7.00 | 3.75" in page.pre_label.text()


def test_not_yet_available_section_present_and_labeled():
    page = MatchIntelligencePage()
    assert page.future_label.text()


def test_no_match_history_style_dashboard_or_chart_widgets():
    page = MatchIntelligencePage()
    forbidden_attrs = ("chart_widget", "gauge_widget", "plot_widget")
    for attr in forbidden_attrs:
        assert not hasattr(page, attr)


def test_match_intelligence_reuses_official_rating_import_service():
    import inspect

    from ht_coach_app.services import match_intelligence_service

    source = inspect.getsource(match_intelligence_service)
    assert "OfficialRatingImportService" in source
    assert "parse_official_ratings" not in source
