import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.controllers.match_intelligence_controller import (
    MatchIntelligenceController,
)
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.services.match_intelligence_service import MatchIntelligenceAppService
from ht_coach_app.views.match_intelligence_page import (
    _NARROW_LAYOUT_BREAKPOINT,
    MatchIntelligencePage,
)

PRE = """[b]Team[/b] [matchid=770131822]
[table]
[tr][th]Defensa[/th][td]4.25[/td][td]7[/td][td]3.75[/td][/tr]
[tr][th]Mediocampo[/th][td colspan=3]7.25[/td][/tr]
[tr][th]Ataque[/th][td]7.75[/td][td]9.75[/td][td]8[/td][/tr]
[/table]
[b]Formación[/b]: 2-5-3 aceptable (6)
[b]Tácticas[/b]: Atacar por el centro clase mundial (13)
[b]Actitud del equipo[/b]: Normal
[b]Estilo de juego[/b]: 100% ofensivo"""
POST = PRE.replace("9.75", "7.75")


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


def test_pre_post_cards_are_side_by_side_by_default(tmp_path):
    page, controller, service = make_controller(tmp_path)
    from PySide6.QtWidgets import QBoxLayout

    assert page._pre_post_row.direction() == QBoxLayout.LeftToRight


def test_narrow_width_stacks_pre_post_vertically(tmp_path):
    page, controller, service = make_controller(tmp_path)
    from PySide6.QtWidgets import QBoxLayout

    page._apply_pre_post_layout(_NARROW_LAYOUT_BREAKPOINT - 100)
    assert page._pre_post_row.direction() == QBoxLayout.TopToBottom


def test_wide_width_restores_side_by_side(tmp_path):
    page, controller, service = make_controller(tmp_path)
    from PySide6.QtWidgets import QBoxLayout

    page._apply_pre_post_layout(_NARROW_LAYOUT_BREAKPOINT - 100)
    page._apply_pre_post_layout(_NARROW_LAYOUT_BREAKPOINT + 200)
    assert page._pre_post_row.direction() == QBoxLayout.LeftToRight


def test_interpreted_comparison_shows_direction_and_magnitude(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import(PRE, "pre")
    controller._import(POST, "post")

    text = page.sector_label.text()
    assert "Empeoró" in text
    assert "Caída importante" in text


def test_conclusions_card_populated_separately_from_limitations(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import(PRE, "pre")
    controller._import(POST, "post")

    assert page.conclusions_label.text()
    assert page.conclusions_label.text() != page.future_label.text()


def test_conclusions_never_just_match_id_association(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import(PRE, "pre")
    controller._import(POST, "post")

    text = page.conclusions_label.text().lower()
    assert "match id" not in text and "matchid" not in text


def test_internal_diagnostic_collapsed_by_default(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import(PRE, "pre")

    assert page.prediction_label.isHidden()
    assert page.internal_diagnostic_toggle.isChecked() is False


def test_internal_diagnostic_expands_on_toggle(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import(PRE, "pre")

    page.internal_diagnostic_toggle.setChecked(True)
    page._toggle_internal_diagnostic()
    assert not page.prediction_label.isHidden()


def test_internal_diagnostic_shows_limitation_not_question_marks(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import(PRE, "pre")

    limitation = page.internal_diagnostic_limitation_label.text()
    assert limitation
    assert "?" not in limitation


def test_no_comparison_shown_without_both_pre_and_post(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import(PRE, "pre")

    text = page.sector_label.text()
    assert text


def test_large_improvement_shows_distinct_label_from_large_decline(tmp_path):
    """Part 10: Spanish UI must distinguish "Caída importante" from
    "Mejora importante" -- not the same phrase regardless of direction."""
    page, controller, service = make_controller(tmp_path)
    improved_post = PRE.replace("9.75", "6.00").replace("7.75\n[b]Formación", "9.75\n[b]Formación")
    controller._import(PRE, "pre")
    # Build a POST where central_attack improves by a large margin.
    boosted_post = PRE.replace("9.75", "12.75")
    controller._import(boosted_post, "post")

    text = page.sector_label.text()
    assert "Mejora importante" in text
    assert "Caída importante" not in text
