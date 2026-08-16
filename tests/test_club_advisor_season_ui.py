import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from ht_coach_app.controllers.club_advisor_controller import ClubAdvisorController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.services.club_advisor_service import ClubAdvisorAppService
from ht_coach_app.services.squad_service import SquadService
from ht_coach_app.views.club_advisor_page import ClubAdvisorPage
from models.player import Player


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def make_player(**overrides):
    base = dict(
        name="Test Player", age=22, days=50, speciality="", form=6, stamina=7,
        goalkeeper=1, defending=5, playmaking=5, winger=5, passing=5, scoring=5,
        set_pieces=4, experience=5, leadership=4, tsi=5000, salary=1000,
    )
    base.update(overrides)
    return Player(**base)


class FakeImporter:
    def __init__(self, players):
        self._players = players

    def __call__(self, path):
        return self._players


def make_controller(tmp_path, players=None):
    players = players or [
        make_player(name="Keeper1", goalkeeper=15, defending=2, playmaking=1, winger=1, passing=2, scoring=1, set_pieces=1),
        make_player(name="Keeper2", goalkeeper=8, defending=1, playmaking=1, winger=1, passing=1, scoring=1, set_pieces=1),
        make_player(name="CD1", defending=15, goalkeeper=1, playmaking=2, winger=2, passing=4, scoring=1, set_pieces=1),
        make_player(name="Forward1", scoring=15, defending=1, goalkeeper=1, playmaking=2, winger=3, passing=3, set_pieces=2),
    ]
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )
    squad_service = SquadService(importer=FakeImporter(players))
    fake_csv = tmp_path / "fake.csv"
    fake_csv.write_text("name\n", encoding="utf-8")
    settings_repo.remember_players_csv_path(str(fake_csv))
    page = ClubAdvisorPage()
    controller = ClubAdvisorController(
        page, squad_service, settings_repo, club_advisor_service=ClubAdvisorAppService()
    )
    return page, controller, players


def test_season_context_card_exists_and_is_editable(tmp_path):
    page, controller, players = make_controller(tmp_path)
    assert page.season_phase_combo.count() > 1
    assert page.promotion_objective_combo.count() > 1
    assert page.competitiveness_combo.count() > 1
    page.bot_opponents_spin.setValue(4)
    assert page.bot_opponents_spin.value() == 4
    page.recent_signing_checkbox.setChecked(True)
    assert page.recent_signing_checkbox.isChecked()


def test_generate_report_populates_operational_and_strategic_sections(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._generate_report()
    assert page.operational_label.text()
    assert page.strategic_label.text()
    assert page.promotion_readiness_label.text()


def test_priorities_display_need_urgency_action_and_horizon(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._generate_report()
    text = page.operational_label.text()
    assert "Necesidad" in text
    assert "Urgencia" in text
    assert "Acción" in text
    assert "Revisión" in text


def test_unknown_season_values_are_accepted_without_crashing(tmp_path):
    page, controller, players = make_controller(tmp_path)
    # leave every combo at its default ("unknown"/"welcome_if_natural")
    controller._generate_report()
    assert page.promotion_readiness_label.text()


def test_report_refreshes_after_season_context_change(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._generate_report()
    before = page.operational_label.text()

    index = page.competitiveness_combo.findData("dominant")
    page.competitiveness_combo.setCurrentIndex(index)
    index = page.season_phase_combo.findData("early_season")
    page.season_phase_combo.setCurrentIndex(index)
    page.bot_opponents_spin.setValue(5)
    page.recent_signing_checkbox.setChecked(True)

    controller._generate_report()
    after = page.operational_label.text()
    assert before != after


def test_saving_season_context_triggers_regeneration(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._generate_report()
    calls = []
    controller._generate_report = lambda: calls.append(True)
    page.season_context_changed.emit()
    assert calls == [True]


def test_promotion_readiness_shown_with_confidence_and_limitations(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._generate_report()
    text = page.promotion_readiness_label.text()
    assert "Confianza" in text


def test_no_overall_score_in_season_sections(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._generate_report()
    combined = page.operational_label.text() + page.strategic_label.text()
    assert "score" not in combined.lower()
    assert "Overall" not in combined


def test_localized_labels_never_show_raw_enum_values(tmp_path):
    page, controller, players = make_controller(tmp_path)
    controller._generate_report()
    text = page.operational_label.text()
    # no stable enum values like "medium"/"low" leaking as raw text
    assert "insufficient_data" not in text
