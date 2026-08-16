import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    MatchAnalysisResult,
    MatchWorkspaceService,
    TeamRatingsResult,
)
from ht_coach_app.services.official_rating_service import OfficialRatingImportService
from ht_coach_app.services.opponent_service import OpponentService
from ht_coach_app.state.app_events import AppEvents
from ht_coach_app.views.match_page import MatchPage

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


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def _seed_last_result(settings_repo):
    service = MatchWorkspaceService.__new__(MatchWorkspaceService)
    our = TeamRatingsResult(
        left_defense=5.0, central_defense=6.0, right_defense=4.75, midfield=7.0,
        left_attack=7.5, central_attack=9.0, right_attack=7.25,
    )
    opponent = TeamRatingsResult(
        left_defense=6.0, central_defense=7.0, right_defense=5.5, midfield=6.5,
        left_attack=7.5, central_attack=8.0, right_attack=6.0,
    )
    formation = FormationAnalysisResult(
        formation_name="2-5-3", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=our, opponent_ratings=opponent,
        sector_rating_comparisons=service._map_sector_comparisons(our, opponent),
    )
    result = MatchAnalysisResult(player_count=18, opponent_name="Rival", formations=[formation])
    settings_repo.save_last_result(result)
    return result


def make_controller(tmp_path, app_events=None):
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
    opponent_service = OpponentService(opponent_repo)
    match_service = MatchWorkspaceService(opponent_service)
    settings_repo = MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json",
        result_storage_path=tmp_path / "result.json",
    )
    historical_repo = HistoricalMatchRepository(tmp_path / "snapshots.json")
    official_service = OfficialRatingImportService(repository=historical_repo)

    page = MatchPage()
    controller = MatchController(
        page, match_service, settings_repo, app_events=app_events,
        official_rating_service=official_service,
    )
    page.show_official_import_success = lambda: None
    return page, controller, settings_repo


def test_importing_pre_refreshes_last_result_without_reanalysis(tmp_path):
    page, controller, settings_repo = make_controller(tmp_path)
    _seed_last_result(settings_repo)

    before = settings_repo.load_last_result()
    assert any(
        c.comparable for c in before.recommended_formation.sector_rating_comparisons
    )

    controller._import_official_ratings(REAL_SAMPLE)

    after = settings_repo.load_last_result()
    assert any(c.comparable for c in after.recommended_formation.sector_rating_comparisons)


def test_importing_pre_calls_show_results_automatically(tmp_path):
    page, controller, settings_repo = make_controller(tmp_path)
    _seed_last_result(settings_repo)

    calls = []
    page.show_results = lambda result, workspace_state=None: calls.append(result)

    controller._import_official_ratings(REAL_SAMPLE)

    assert len(calls) == 1
    assert any(
        c.comparable for c in calls[0].recommended_formation.sector_rating_comparisons
    )


def test_no_last_result_does_not_crash_on_import(tmp_path):
    page, controller, settings_repo = make_controller(tmp_path)
    controller._import_official_ratings(REAL_SAMPLE)


def test_official_ratings_changed_event_emitted_on_import(tmp_path):
    app_events = AppEvents()
    page, controller, settings_repo = make_controller(tmp_path, app_events=app_events)
    _seed_last_result(settings_repo)

    calls = []
    app_events.official_ratings_changed.connect(lambda: calls.append(True))

    controller._import_official_ratings(REAL_SAMPLE)

    assert calls == [True]


def test_match_intelligence_controller_import_also_notifies_match(tmp_path):
    """Alpha 0.6.7 HF-03, Part 17: the cross-controller notification
    must carry the touched record's own ID, and the Match workspace
    must only refresh when that record is the one it actually has
    open -- never blindly on any import anywhere."""
    from ht_coach_app.controllers.match_intelligence_controller import (
        MatchIntelligenceController,
    )
    from ht_coach_app.services.match_intelligence_service import MatchIntelligenceAppService
    from ht_coach_app.views.match_intelligence_page import MatchIntelligencePage

    historical_repo = HistoricalMatchRepository(tmp_path / "snapshots2.json")
    mi_service = MatchIntelligenceAppService(repository=historical_repo)
    mi_page = MatchIntelligencePage()
    app_events = AppEvents()
    MatchIntelligenceController(mi_page, service=mi_service, app_events=app_events)

    match_page, match_controller, settings_repo = make_controller(tmp_path, app_events=app_events)
    _seed_last_result(settings_repo)
    match_controller._official_rating_service = OfficialRatingImportService(
        repository=historical_repo
    )
    match_page.show_official_import_success = lambda: None

    calls = []
    match_page.show_results = lambda result, workspace_state=None: calls.append(result)

    outcome = mi_service.import_ratings(REAL_SAMPLE, slot="pre")
    # Simulate the Match workspace already having this exact record
    # open -- the common real case is editing a saved match while
    # Official Intelligence also touches it.
    match_controller._editing_snapshot_id = outcome.snapshot.snapshot_id

    app_events.official_ratings_changed.emit(outcome.snapshot.snapshot_id)

    assert len(calls) == 1
    assert any(
        c.comparable for c in calls[0].recommended_formation.sector_rating_comparisons
    )


def test_official_ratings_changed_for_a_different_record_is_ignored(tmp_path):
    """Part 17: receivers must ignore events for other records --
    importing evidence for an unrelated match must never refresh (or
    silently apply data to) a workspace that has a different record
    open."""
    from ht_coach_app.controllers.match_intelligence_controller import (
        MatchIntelligenceController,
    )
    from ht_coach_app.services.match_intelligence_service import MatchIntelligenceAppService
    from ht_coach_app.views.match_intelligence_page import MatchIntelligencePage

    historical_repo = HistoricalMatchRepository(tmp_path / "snapshots2.json")
    mi_service = MatchIntelligenceAppService(repository=historical_repo)
    mi_page = MatchIntelligencePage()
    app_events = AppEvents()
    MatchIntelligenceController(mi_page, service=mi_service, app_events=app_events)

    match_page, match_controller, settings_repo = make_controller(tmp_path, app_events=app_events)
    _seed_last_result(settings_repo)
    match_controller._official_rating_service = OfficialRatingImportService(
        repository=historical_repo
    )
    match_page.show_official_import_success = lambda: None
    match_controller._editing_snapshot_id = "some-other-record-entirely"

    calls = []
    match_page.show_results = lambda result, workspace_state=None: calls.append(result)

    outcome = mi_service.import_ratings(REAL_SAMPLE, slot="pre")
    app_events.official_ratings_changed.emit(outcome.snapshot.snapshot_id)

    assert calls == []
