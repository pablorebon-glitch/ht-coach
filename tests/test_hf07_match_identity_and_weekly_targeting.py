import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.models import SectorRatings
from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.provisional_record import (
    complete_with_official_post,
    find_or_create_provisional_record,
)
from engine.history.repository import HistoricalMatchRepository
from engine.history.retrospective_pre import save_as_retrospective_simulation
from engine.weekly_training.persistence import WeeklyTrainingRepository
from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.controllers.match_intelligence_controller import (
    MatchIntelligenceController,
)
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.services.match_display_formatter import format_match_record_identity
from ht_coach_app.services.match_intelligence_service import MatchIntelligenceAppService
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    MatchAnalysisResult,
    MatchWorkspaceService,
    TeamRatingsResult,
)
from ht_coach_app.services.opponent_service import OpponentService
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from ht_coach_app.views.match_intelligence_page import MatchIntelligencePage
from ht_coach_app.views.match_page import MatchPage


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def _ratings(midfield):
    return SectorRatings(
        scale="hattrick",
        right_defense=6.0,
        central_defense=7.0,
        left_defense=6.5,
        midfield=midfield,
        right_attack=5.5,
        central_attack=6.0,
        left_attack=5.0,
    )


def _official_snapshot(team_name, match_id, midfield):
    return OfficialRatingSnapshot(
        team_name=team_name,
        hattrick_match_id=match_id,
        ratings=_ratings(midfield),
    )


def _torres_record_with_retrospective_pre(repository):
    record = find_or_create_provisional_record(
        repository,
        opponent_name="Torres Futbol Club",
        match_date="2026-07-26",
        competition_type="league",
        home_away="home",
    )
    completed = complete_with_official_post(
        repository,
        record,
        _official_snapshot("Hit'em up", "770918226", 6.25),
        "770918226",
    )
    return save_as_retrospective_simulation(
        repository,
        completed,
        _official_snapshot("Santa Cruz Club", "771000000", 6.75),
        confidence="low",
        limitation="Simulated after the match.",
    )


def test_retrospective_pre_never_mutates_canonical_torres_identity(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    saved = _torres_record_with_retrospective_pre(repository)
    reloaded = repository.get(saved.snapshot_id)

    assert reloaded.match_context.opponent.opponent_name == "Torres Futbol Club"
    assert reloaded.match_context.match_date == "2026-07-26"
    assert reloaded.match_context.competition_type.value == "league"
    assert reloaded.match_context.home_away.value == "home"
    assert reloaded.match_context.official_match_id == "770918226"
    assert reloaded.official_pre is None
    assert reloaded.official_post.hattrick_match_id == "770918226"
    assert reloaded.retrospective_pre.source_match_id == "771000000"
    assert reloaded.retrospective_pre.team_name == "Santa Cruz Club"
    assert len(repository.list_all()) == 1


def test_canonical_formatter_ignores_retrospective_source_opponent(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    record = _torres_record_with_retrospective_pre(repository)

    label = format_match_record_identity(record)

    assert label == "Hit'em up vs. Torres Futbol Club"
    assert "Santa Cruz" not in label
    assert " - " not in label


def test_official_intelligence_renders_retrospective_pre_and_post(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    record = _torres_record_with_retrospective_pre(repository)
    service = MatchIntelligenceAppService(repository=repository)
    page = MatchIntelligencePage()
    controller = MatchIntelligenceController(page, service=service)

    controller._select_record(record.snapshot_id)

    assert "Hit'em up vs. Torres Futbol Club" in page.record_identity_label.text()
    assert "Santa Cruz" not in page.record_identity_label.text()
    assert "PRE retrospectivo" in page.pre_label.text()
    assert "POST" not in page.pre_label.text()
    assert page.post_label.text() != "No importado"
    assert "Simulación retrospectiva vs. POST oficial" in page.sector_label.text()
    assert page.sector_label.text() != "-"
    assert page.conclusions_label.text() != "-"


def _lineup():
    return [
        LineupPlayerResult(
            number=i,
            position="INNER_MIDFIELDER",
            side="CENTER",
            order="Normal",
            order_side="",
            player_name=f"P{i}",
        )
        for i in range(1, 12)
    ]


def _analysis_result():
    formation = FormationAnalysisResult(
        formation_name="3-5-2",
        recommended_tactic="Normal",
        tactic_level=5,
        win_probability=0.5,
        draw_probability=0.3,
        loss_probability=0.2,
        possession=50.0,
        expected_goals=1.5,
        opponent_expected_goals=1.2,
        is_recommended=True,
        team_ratings=TeamRatingsResult(),
        lineup=_lineup(),
    )
    return MatchAnalysisResult(
        player_count=18,
        opponent_name="Torres Futbol Club",
        formations=[formation],
    )


def _match_controller(tmp_path):
    opponent_service = OpponentService(
        OpponentRepository(storage_path=tmp_path / "opponents.json")
    )
    page = MatchPage()
    controller = MatchController(
        page,
        MatchWorkspaceService(opponent_service),
        MatchWorkspaceRepository(
            storage_path=tmp_path / "settings.json",
            result_storage_path=tmp_path / "result.json",
        ),
        weekly_training_service=WeeklyTrainingAppService(
            repository=WeeklyTrainingRepository(tmp_path / "planner.json")
        ),
    )
    return page, controller


def test_missing_match_date_blocks_weekly_planner_save(tmp_path):
    page, controller = _match_controller(tmp_path)
    controller._settings_repository.save_last_result(_analysis_result())
    page.match_date = lambda: ""
    errors = []
    page.show_error = errors.append

    controller._save_as_first_match()

    assert errors == [
        "Para guardar este partido en el Planificador semanal, primero cargá la fecha del partido."
    ]
    state = controller._weekly_training_service.load_state()
    assert state.match_records == ()
