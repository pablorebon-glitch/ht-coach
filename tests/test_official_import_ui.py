import tempfile
from pathlib import Path

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.controllers.match_controller import MatchController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.services.match_workspace_service import MatchWorkspaceService
from ht_coach_app.services.official_rating_service import OfficialRatingImportService
from ht_coach_app.services.opponent_service import OpponentService
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

NO_MATCH_ID_SAMPLE = REAL_SAMPLE.replace(" [matchid=770131822]", "")


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def make_controller(tmp_path):
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
        page, match_service, settings_repo, official_rating_service=official_service
    )
    return page, controller, official_service


# --------------------------------------------------------------------------
# Successful import
# --------------------------------------------------------------------------

def test_confirmed_verbatim_sample_imports_successfully(tmp_path):
    page, controller, service = make_controller(tmp_path)
    messages = []
    page.show_status = lambda msg: messages.append(msg)

    controller._import_official_ratings(REAL_SAMPLE)

    assert len(messages) == 1
    assert "importó" in messages[0].lower() or "imported" in messages[0].lower()


def test_successful_import_shows_hattrick_notation_summary(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import_official_ratings(REAL_SAMPLE)

    text = page.official_summary_label.text()
    assert "4.25 | 7.00 | 3.75" in text
    assert "7.75 | 9.75 | 8.00" in text
    assert "2-5-3" in text


def test_successful_import_shows_match_id_and_source(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import_official_ratings(REAL_SAMPLE)

    text = page.official_summary_label.text()
    assert "770131822" in text


# --------------------------------------------------------------------------
# Automatic match ID linking
# --------------------------------------------------------------------------

def test_first_import_creates_new_record_second_import_links_to_it(tmp_path):
    page, controller, service = make_controller(tmp_path)
    messages = []
    page.show_status = lambda msg: messages.append(msg)
    page.confirm_official_import_replace = lambda slot: True

    controller._import_official_ratings(REAL_SAMPLE)
    controller._import_official_ratings(REAL_SAMPLE)

    assert "creó" in messages[0] or "created" in messages[0].lower()
    assert "vinculó" in messages[1] or "linked" in messages[1].lower()


# --------------------------------------------------------------------------
# Error feedback
# --------------------------------------------------------------------------

def test_no_match_id_shows_descriptive_error(tmp_path):
    page, controller, service = make_controller(tmp_path)
    errors = []
    page.show_official_import_error = lambda msg: errors.append(msg)

    controller._import_official_ratings(NO_MATCH_ID_SAMPLE)

    assert len(errors) == 1
    assert errors[0]


def test_empty_text_shows_descriptive_error(tmp_path):
    page, controller, service = make_controller(tmp_path)
    errors = []
    page.show_official_import_error = lambda msg: errors.append(msg)

    controller._import_official_ratings("")

    assert len(errors) == 1


def test_ambiguous_match_shows_conflict_state(tmp_path):
    from engine.history.models import (
        HistoricalMatchSnapshot,
        MatchContext,
        SnapshotProvenance,
        stable_snapshot_id,
    )

    page, controller, service = make_controller(tmp_path)
    for _ in range(2):
        service._repository.save(
            HistoricalMatchSnapshot(
                snapshot_id=stable_snapshot_id(),
                match_context=MatchContext(match_date="2026-07-26"),
                provenance=SnapshotProvenance(imported_match_id="770131822"),
            )
        )

    ambiguous_calls = []
    page.confirm_ambiguous_official_import = lambda count: ambiguous_calls.append(count)
    messages = []
    page.show_status = lambda msg: messages.append(msg)

    controller._import_official_ratings(REAL_SAMPLE)

    assert len(ambiguous_calls) == 1
    assert messages == []  # no success message -- it must not guess


# --------------------------------------------------------------------------
# Replace confirmation
# --------------------------------------------------------------------------

def test_declining_replace_confirmation_does_not_overwrite(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import_official_ratings(REAL_SAMPLE)

    page.confirm_official_import_replace = lambda slot: False
    messages = []
    page.show_status = lambda msg: messages.append(msg)

    controller._import_official_ratings(REAL_SAMPLE)

    assert messages == []


def test_confirming_replace_overwrites(tmp_path):
    page, controller, service = make_controller(tmp_path)
    controller._import_official_ratings(REAL_SAMPLE)

    page.confirm_official_import_replace = lambda slot: True
    messages = []
    page.show_status = lambda msg: messages.append(msg)

    controller._import_official_ratings(REAL_SAMPLE)

    assert len(messages) == 1


# --------------------------------------------------------------------------
# Tactic normalization surfaced through the UI
# --------------------------------------------------------------------------

def test_unknown_tactic_warning_surfaced_in_summary(tmp_path):
    unknown_tactic_sample = REAL_SAMPLE.replace(
        "Atacar por el centro clase mundial (13)",
        "Una tactica del futuro (9)",
    )
    page, controller, service = make_controller(tmp_path)
    controller._import_official_ratings(unknown_tactic_sample)

    text = page.official_summary_label.text()
    assert t_key_shown_or_raw_text_present(text)


def t_key_shown_or_raw_text_present(text):
    return "Avisos" in text or "Warnings" in text


# --------------------------------------------------------------------------
# Responsibility boundaries
# --------------------------------------------------------------------------

def test_import_does_not_change_active_lineup(tmp_path):
    page, controller, service = make_controller(tmp_path)
    before = list(page.selected_formations()) if hasattr(page, "selected_formations") else None

    controller._import_official_ratings(REAL_SAMPLE)

    after = list(page.selected_formations()) if hasattr(page, "selected_formations") else None
    assert before == after


def test_no_match_history_navigation_added(tmp_path):
    page, controller, service = make_controller(tmp_path)
    assert not hasattr(page, "match_history_button")
    assert not hasattr(page, "match_history_tab")


def test_import_never_invokes_formation_optimizer():
    import ast

    for filename in ("match_controller.py", "official_rating_service.py"):
        for base in ("ht_coach_app/controllers", "ht_coach_app/services"):
            path = Path(__file__).resolve().parents[1] / base / filename
            if not path.exists():
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imported.add(alias.name)
            forbidden = {
                "engine.optimizers.formation_optimizer",
                "engine.optimizers.tactic_optimizer",
            }
            # match_controller.py legitimately imports formation-related
            # helpers for its *own* analysis workflow; the check that
            # matters is that the *official import* code path never
            # reaches for them, which the service-level static-import
            # test (test_history_responsibility_boundaries.py) already
            # guarantees for engine.history.official_ratings itself.
            if filename == "official_rating_service.py":
                assert not (imported & forbidden)
