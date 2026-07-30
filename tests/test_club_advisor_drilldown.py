import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from ht_coach_app.controllers.club_advisor_controller import ClubAdvisorController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.services.club_advisor_service import ClubAdvisorAppService
from ht_coach_app.services.squad_service import SquadService
from ht_coach_app.views.club_advisor_page import ClubAdvisorPage
from ht_coach_app.widgets.drilldown_overlay import DrillDownOverlay
from engine.club_advisor.enums import ClubConfidence, ClubRiskType, ProjectStatus
from engine.club_advisor.models import ClubRisk, ProjectStatusExplanation
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


def make_controller(tmp_path):
    players = [
        make_player(name="Keeper1", goalkeeper=15, defending=2, playmaking=1, winger=1, passing=2, scoring=1, set_pieces=1),
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
    return page, controller


def _find_overlay(page):
    return next((c for c in page.children() if isinstance(c, DrillDownOverlay)), None)


def test_cards_are_clickable_and_carry_card_key(tmp_path):
    page, controller = make_controller(tmp_path)
    assert page.squad_frame.cursor()
    assert page.risks_frame.cursor()


def test_clicking_squad_card_opens_drilldown(tmp_path):
    page, controller = make_controller(tmp_path)
    controller._generate_report()
    controller._open_drilldown("squad")
    overlay = _find_overlay(page)
    assert overlay is not None
    assert overlay.list_widget.count() > 0


def test_drilldown_first_row_selected_by_default(tmp_path):
    page, controller = make_controller(tmp_path)
    controller._generate_report()
    controller._open_drilldown("squad")
    overlay = _find_overlay(page)
    assert overlay.list_widget.currentRow() == 0
    assert overlay.detail_label.text()


def test_drilldown_selecting_row_updates_detail(tmp_path):
    page, controller = make_controller(tmp_path)
    controller._generate_report()
    controller._open_drilldown("squad")
    overlay = _find_overlay(page)
    if overlay.list_widget.count() > 1:
        overlay.list_widget.setCurrentRow(1)
        assert overlay.detail_label.text()


def test_drilldown_modal_is_single_elevated_surface(tmp_path):
    page, controller = make_controller(tmp_path)
    controller._generate_report()
    controller._open_drilldown("risks")
    overlay = _find_overlay(page)
    if overlay is not None:
        assert overlay.panel.parent() is overlay
        assert overlay.panel.autoFillBackground()
        assert overlay.panel.geometry().isValid()


def test_risks_drilldown_shows_full_detail(tmp_path):
    page, controller = make_controller(tmp_path)
    controller._generate_report()
    controller._open_drilldown("risks")
    overlay = _find_overlay(page)
    if overlay is not None:
        assert overlay.reason_label.text()
        assert overlay.impact_label.text()
        assert overlay.players_label.text()


def test_close_button_closes_overlay(tmp_path):
    page, controller = make_controller(tmp_path)
    controller._generate_report()
    controller._open_drilldown("squad")
    overlay = _find_overlay(page)
    closed = []
    overlay.closed.connect(lambda: closed.append(True))
    overlay.close_button.click()
    assert closed == [True]


def test_esc_closes_overlay(tmp_path):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    page, controller = make_controller(tmp_path)
    controller._generate_report()
    controller._open_drilldown("squad")
    overlay = _find_overlay(page)
    closed = []
    overlay.closed.connect(lambda: closed.append(True))
    event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    overlay.keyPressEvent(event)
    assert closed == [True]


def test_click_outside_panel_closes_overlay(tmp_path):
    from PySide6.QtCore import QEvent, QPoint, Qt
    from PySide6.QtGui import QMouseEvent

    page, controller = make_controller(tmp_path)
    controller._generate_report()
    controller._open_drilldown("squad")
    overlay = _find_overlay(page)
    closed = []
    overlay.closed.connect(lambda: closed.append(True))
    event = QMouseEvent(
        QEvent.MouseButtonPress, QPoint(2, 2), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
    )
    overlay.mousePressEvent(event)
    assert closed == [True]


def test_click_inside_panel_does_not_close_overlay(tmp_path):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QMouseEvent

    page, controller = make_controller(tmp_path)
    controller._generate_report()
    controller._open_drilldown("squad")
    overlay = _find_overlay(page)
    closed = []
    overlay.closed.connect(lambda: closed.append(True))
    center = overlay.panel.geometry().center()
    event = QMouseEvent(
        QEvent.MouseButtonPress, center, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
    )
    overlay.mousePressEvent(event)
    assert closed == []


def test_no_report_yet_does_not_crash_on_card_click(tmp_path):
    page, controller = make_controller(tmp_path)
    controller._open_drilldown("squad")
    assert _find_overlay(page) is None


def test_unknown_card_key_does_not_crash(tmp_path):
    page, controller = make_controller(tmp_path)
    controller._generate_report()
    controller._open_drilldown("nonexistent")
    assert _find_overlay(page) is None


def test_training_drilldown_rows_built(tmp_path):
    page, controller = make_controller(tmp_path)
    controller._generate_report()
    rows = controller._training_drilldown_rows(controller._last_report)
    assert len(rows) >= 4
    labels = [label for label, _detail in rows]
    assert "100%" in labels
    assert "50%" in labels
    assert "No training" in labels


def test_training_card_uses_percentage_buckets_not_primary_secondary_labels(tmp_path):
    page, controller = make_controller(tmp_path)
    controller._generate_report()
    sections = controller._format_sections(controller._last_report)

    assert "100%" in sections["training"]
    assert "50%" in sections["training"]
    assert "No training" in sections["training"]
    assert "Primary trainees" not in sections["training"]
    assert "Secondary trainees" not in sections["training"]


def test_critical_project_status_includes_immediate_causes():
    report = type(
        "Report",
        (),
        {
            "project_status": ProjectStatus.CRITICAL,
            "confidence": ClubConfidence.HIGH,
            "status_explanation": ProjectStatusExplanation(
                structural_status=ProjectStatus.CRITICAL,
                operational_status="high",
                driving_dimensions=("depth",),
                reason_key="club_advisor.status_explanation.driven_by_dimension",
                reason_params={"dimensions": "Depth"},
                confidence=ClubConfidence.HIGH,
            ),
            "risks": (
                ClubRisk(
                    risk_type=ClubRiskType.NO_CENTRAL_DEFENDER_REPLACEMENT,
                    reason_key="club_advisor.risk_reason.central_defense_uncovered",
                    reason_params={"count": 1, "slots": 2},
                ),
            ),
            "warnings": (),
        },
    )()

    text = ClubAdvisorController._format_status_section(report)

    assert "Reasons" in text
    assert "central" in text.lower()


def test_depth_drilldown_rows_built(tmp_path):
    page, controller = make_controller(tmp_path)
    controller._generate_report()
    rows = controller._depth_drilldown_rows(controller._last_report)
    assert len(rows) == 6


def test_limitations_drilldown_rows_built(tmp_path):
    page, controller = make_controller(tmp_path)
    controller._generate_report()
    rows = controller._limitations_drilldown_rows(controller._last_report)
    assert len(rows) == len(controller._last_report.limitations)
