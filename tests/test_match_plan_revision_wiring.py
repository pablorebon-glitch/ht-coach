import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    MatchAnalysisResult,
    MatchWorkspaceService,
    TeamRatingsResult,
)
from ht_coach_app.services.opponent_service import OpponentService
from ht_coach_app.views.match_page import MatchPage


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def _lineup(names):
    return [
        LineupPlayerResult(
            number=i, position="INNER_MIDFIELDER", side="CENTER",
            order="Normal", order_side="", player_name=name,
        )
        for i, name in enumerate(names, start=1)
    ]


def _result(names, win_probability=0.5, formation_name="3-5-2", midfield=7.0):
    formation = FormationAnalysisResult(
        formation_name=formation_name, recommended_tactic="Normal", tactic_level=5,
        win_probability=win_probability, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=TeamRatingsResult(midfield=midfield),
        lineup=_lineup(names),
    )
    return MatchAnalysisResult(player_count=18, opponent_name="Rival", formations=[formation])


def make_controller(tmp_path):
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
    opponent_service = OpponentService(opponent_repo)
    match_service = MatchWorkspaceService(opponent_service)
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json",
        result_storage_path=tmp_path / "result.json",
    )
    page = MatchPage()
    controller = MatchController(page, match_service, settings_repo)
    return page, controller


def test_compute_and_show_plan_revision_calls_view_when_supported(tmp_path):
    page, controller = make_controller(tmp_path)

    calls = []
    page.show_plan_revision = lambda revision, classification, explanation: calls.append(
        (revision, classification, explanation)
    )

    previous = _result(["A", "B", "C"], win_probability=0.45)
    new = _result(["A", "X", "C"], win_probability=0.55, midfield=7.5)

    controller._compute_and_show_plan_revision(previous, new)

    assert len(calls) == 1
    revision, classification, explanation = calls[0]
    assert "X" in revision.changed_players
    assert "B" in revision.changed_players
    assert explanation.recommendation_key


def test_compute_and_show_plan_revision_skipped_when_view_lacks_support(tmp_path):
    page, controller = make_controller(tmp_path)
    assert not hasattr(page, "show_plan_revision")

    previous = _result(["A", "B", "C"])
    new = _result(["A", "X", "C"])

    controller._compute_and_show_plan_revision(previous, new)  # must not raise


def test_compute_and_show_plan_revision_handles_no_previous_result(tmp_path):
    page, controller = make_controller(tmp_path)
    calls = []
    page.show_plan_revision = lambda revision, classification, explanation: calls.append(revision)

    new = _result(["A", "B", "C"])
    controller._compute_and_show_plan_revision(None, new)

    assert len(calls) == 1
    assert not calls[0].has_previous_plan


def test_compute_and_show_plan_revision_never_raises_on_bad_view_callback(tmp_path):
    page, controller = make_controller(tmp_path)

    def broken_callback(*args):
        raise RuntimeError("boom")

    page.show_plan_revision = broken_callback

    previous = _result(["A", "B", "C"])
    new = _result(["A", "X", "C"])
    controller._compute_and_show_plan_revision(previous, new)  # must not raise
