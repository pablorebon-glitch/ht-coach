import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.models import HistoricalMatchSnapshot, MatchContext, OpponentReference
from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.provisional_record import find_or_create_provisional_record
from engine.history.repository import HistoricalMatchRepository
from engine.history.retrospective_pre import save_as_retrospective_simulation
from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.controllers.match_intelligence_controller import (
    MatchIntelligenceController,
)
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.services.match_intelligence_service import MatchIntelligenceAppService
from ht_coach_app.services.match_workspace_service import MatchWorkspaceService
from ht_coach_app.services.official_rating_service import OfficialRatingImportService
from ht_coach_app.services.opponent_service import OpponentService
from ht_coach_app.views.match_intelligence_page import MatchIntelligencePage
from ht_coach_app.views.match_page import MatchPage
from models.opponent import Opponent
from models.team_ratings import TeamRatings


POST_TEXT = """[b]Hit'em up - Torres Futbol Club[/b] [matchid=770918226]

[table]
[tr][th]Defensa[/th][td align=center]4.25[/td][td align=center]7[/td][td align=center]3.75[/td][/tr]
[tr][th]Mediocampo[/th][td colspan=3 align=center]7.25[/td][/tr]
[tr][th]Ataque[/th][td align=center]7.75[/td][td align=center]9.75[/td][td align=center]8[/td][/tr]
[/table]

[b]FormaciÃ³n[/b]: 2-5-3 aceptable (6)
[b]TÃ¡cticas[/b]: Atacar por el centro clase mundial (13)
[b]Actitud del equipo[/b]: Normal
[b]Estilo de juego[/b]: 100% ofensivo"""


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def _retrospective_torres_without_post(repository):
    record = find_or_create_provisional_record(
        repository,
        opponent_name="Torres Futbol Club",
        match_date="2026-07-26",
        competition_type="league",
        home_away="home",
    )
    record = repository.save(
        record.with_updates(
            match_context=MatchContext(
                official_match_id="",
                match_date=record.match_context.match_date,
                competition_type=record.match_context.competition_type,
                home_away=record.match_context.home_away,
                opponent=record.match_context.opponent,
            )
        )
    )
    return save_as_retrospective_simulation(
        repository,
        record,
        OfficialRatingSnapshot(
            team_name="Santa Cruz Club",
            hattrick_match_id="771000000",
        ),
        confidence="low",
        limitation="Simulated after the match.",
    )


def test_post_import_from_selected_record_does_not_jump_to_other_match(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    torres = _retrospective_torres_without_post(repository)
    chaco = repository.save(
        HistoricalMatchSnapshot(
            snapshot_id="chaco",
            match_context=MatchContext(
                official_match_id="770918226",
                opponent=OpponentReference(opponent_name="CA Chaco"),
            ),
        )
    )
    service = MatchIntelligenceAppService(repository=repository)
    page = MatchIntelligencePage()
    controller = MatchIntelligenceController(page, service=service)
    controller._select_record(torres.snapshot_id)

    controller._import(POST_TEXT, "post")

    reloaded_torres = repository.get(torres.snapshot_id)
    reloaded_chaco = repository.get(chaco.snapshot_id)
    assert controller._selected_snapshot_id == torres.snapshot_id
    assert reloaded_torres.official_post is not None
    assert reloaded_torres.match_context.official_match_id == "770918226"
    assert reloaded_torres.retrospective_pre.source_match_id == "771000000"
    assert reloaded_chaco.official_post is None
    assert "Hit'em up vs. Torres Futbol Club" in page.record_identity_label.text()
    assert "CA Chaco" not in page.record_identity_label.text()
    assert page.post_label.text() != "No importado"


def test_replacing_post_is_scoped_to_selected_record(tmp_path, monkeypatch):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    torres = _retrospective_torres_without_post(repository)
    torres = OfficialRatingImportService(repository).import_ratings(
        torres.snapshot_id,
        POST_TEXT,
        slot="post",
    ).snapshot
    repository.save(
        HistoricalMatchSnapshot(
            snapshot_id="chaco",
            match_context=MatchContext(
                official_match_id="770918226",
                opponent=OpponentReference(opponent_name="CA Chaco"),
            ),
            official_post=OfficialRatingSnapshot(team_name="Wrong Chaco POST"),
        )
    )
    service = MatchIntelligenceAppService(repository=repository)
    page = MatchIntelligencePage()
    controller = MatchIntelligenceController(page, service=service)
    controller._select_record(torres.snapshot_id)
    monkeypatch.setattr(
        "ht_coach_app.controllers.match_intelligence_controller.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.Yes,
    )

    from PySide6.QtWidgets import QMessageBox

    controller._import(POST_TEXT, "post")

    assert repository.get(torres.snapshot_id).official_post is not None
    assert repository.get("chaco").official_post.team_name == "Wrong Chaco POST"
    assert controller._selected_snapshot_id == torres.snapshot_id


def _match_controller(tmp_path, known_opponents=()):
    hist_repo = HistoricalMatchRepository(tmp_path / "snapshots.json")
    opponent_repo = OpponentRepository(storage_path=tmp_path / "opponents.json")
    for name in known_opponents:
        opponent_repo.save(Opponent(name=name, ratings=TeamRatings()))
    opponent_service = OpponentService(opponent_repo)
    page = MatchPage()
    controller = MatchController(
        page,
        MatchWorkspaceService(opponent_service),
        MatchWorkspaceRepository(
            storage_path=tmp_path / "settings.json",
            result_storage_path=tmp_path / "result.json",
        ),
        official_rating_service=OfficialRatingImportService(repository=hist_repo),
    )
    return page, controller, hist_repo


def test_edit_saved_match_missing_opponent_uses_synthetic_identity(tmp_path):
    page, controller, hist_repo = _match_controller(
        tmp_path,
        known_opponents=["Torres Futbol Club"],
    )
    record = find_or_create_provisional_record(
        hist_repo,
        opponent_name="CA Chaco",
        match_date="2026-08-09",
        competition_type="league",
    )

    controller.edit_record(record.snapshot_id)

    identity = page.selected_opponent_identity()
    assert page.selected_opponent_name() == "CA Chaco"
    assert identity["opponent_name"] == "CA Chaco"
    assert identity["source"] == "SAVED_MATCH_SNAPSHOT"
    assert "Torres" not in page.opponent_combo.currentText()


def test_missing_saved_opponent_blocks_analysis_without_fallback(tmp_path):
    page, controller, hist_repo = _match_controller(
        tmp_path,
        known_opponents=["Torres Futbol Club"],
    )
    record = find_or_create_provisional_record(
        hist_repo,
        opponent_name="CA Chaco",
        match_date="2026-08-09",
        competition_type="league",
    )
    controller.edit_record(record.snapshot_id)
    errors = []
    page.show_error = errors.append

    controller._analyze()

    assert errors == [
        "Este rival guardado no esta disponible en el gestor de rivales. Agregalo al gestor o selecciona otro rival antes de analizar."
    ]
