import pytest

from engine.history.models import HistoricalMatchSnapshot, MatchContext, stable_snapshot_id
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.services.official_rating_service import (
    POST,
    PRE,
    OfficialRatingAmbiguousMatch,
    OfficialRatingImportError,
    OfficialRatingImportService,
    OfficialRatingReplaceConfirmationRequired,
)

SAMPLE_TEXT = """[b]Hit'em up - Torres Futbol Club[/b] [matchid=770131822]

[table]
[tr][th]Defensa[/th][td align=center]4.25[/td][td align=center]7[/td][td align=center]3.75[/td][/tr]
[tr][th]Mediocampo[/th][td colspan=3 align=center]7.25[/td][/tr]
[tr][th]Ataque[/th][td align=center]7.75[/td][td align=center]9.75[/td][td align=center]8[/td][/tr]
[/table]

[b]Formación[/b]: 2-5-3 aceptable (6)
[b]Tácticas[/b]: Atacar por el centro clase mundial (13)
[b]Actitud del equipo[/b]: Normal
[b]Estilo de juego[/b]: 100% ofensivo"""

SAMPLE_TEXT_NO_MATCH_ID = SAMPLE_TEXT.replace(" [matchid=770131822]", "")


def make_snapshot_with_match_id(repository, hattrick_match_id, opponent="Torres Futbol Club"):
    from engine.history.models import OpponentReference, SnapshotProvenance

    snapshot = HistoricalMatchSnapshot(
        snapshot_id=stable_snapshot_id(),
        match_context=MatchContext(
            match_date="2026-07-26", opponent=OpponentReference(opponent_name=opponent)
        ),
        provenance=SnapshotProvenance(imported_match_id=hattrick_match_id),
    )
    return repository.save(snapshot)


# --------------------------------------------------------------------------
# Automatic match ID linking
# --------------------------------------------------------------------------

def test_links_automatically_when_exactly_one_snapshot_matches(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    existing = make_snapshot_with_match_id(repository, "770131822")
    service = OfficialRatingImportService(repository=repository)

    outcome = service.import_and_link(SAMPLE_TEXT, slot=PRE)

    assert outcome.was_linked_to_existing_match
    assert not outcome.was_new_snapshot_created
    assert outcome.snapshot.snapshot_id == existing.snapshot_id
    assert outcome.snapshot.official_pre.ratings.midfield == 7.25


def test_creates_identifiable_snapshot_when_no_match_exists(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    service = OfficialRatingImportService(repository=repository)

    outcome = service.import_and_link(SAMPLE_TEXT, slot=PRE)

    assert outcome.was_new_snapshot_created
    assert not outcome.was_linked_to_existing_match
    assert outcome.snapshot.provenance.imported_match_id == "770131822"
    assert outcome.snapshot.official_pre is not None

    # it's really persisted, not just returned in memory
    reloaded = repository.get(outcome.snapshot.snapshot_id)
    assert reloaded.official_pre.ratings.midfield == 7.25


def test_ambiguous_match_raises_with_candidates_rather_than_guessing(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    make_snapshot_with_match_id(repository, "770131822", opponent="Team A")
    make_snapshot_with_match_id(repository, "770131822", opponent="Team B")
    service = OfficialRatingImportService(repository=repository)

    with pytest.raises(OfficialRatingAmbiguousMatch) as exc_info:
        service.import_and_link(SAMPLE_TEXT, slot=PRE)

    assert len(exc_info.value.candidates) == 2
    assert exc_info.value.hattrick_match_id == "770131822"


def test_no_match_id_in_text_requires_explicit_snapshot_selection(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    service = OfficialRatingImportService(repository=repository)

    with pytest.raises(OfficialRatingImportError):
        service.import_and_link(SAMPLE_TEXT_NO_MATCH_ID, slot=PRE)


def test_find_snapshots_by_hattrick_match_id(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    make_snapshot_with_match_id(repository, "111")
    make_snapshot_with_match_id(repository, "222")
    service = OfficialRatingImportService(repository=repository)

    assert len(service.find_snapshots_by_hattrick_match_id("111")) == 1
    assert len(service.find_snapshots_by_hattrick_match_id("999")) == 0
    assert service.find_snapshots_by_hattrick_match_id("") == ()


# --------------------------------------------------------------------------
# PRE / POST replace-confirmation semantics
# --------------------------------------------------------------------------

def test_pre_import_succeeds_without_confirmation_when_slot_is_empty(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    make_snapshot_with_match_id(repository, "770131822")
    service = OfficialRatingImportService(repository=repository)

    outcome = service.import_and_link(SAMPLE_TEXT, slot=PRE)
    assert outcome.snapshot.official_pre is not None


def test_replacing_existing_pre_requires_explicit_confirmation(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    make_snapshot_with_match_id(repository, "770131822")
    service = OfficialRatingImportService(repository=repository)

    service.import_and_link(SAMPLE_TEXT, slot=PRE)

    with pytest.raises(OfficialRatingReplaceConfirmationRequired) as exc_info:
        service.import_and_link(SAMPLE_TEXT, slot=PRE)
    assert exc_info.value.slot == PRE

    # with explicit confirmation, it proceeds
    outcome = service.import_and_link(SAMPLE_TEXT, slot=PRE, confirm_replace=True)
    assert outcome.snapshot.official_pre is not None


def test_post_is_never_automatically_inferred_just_because_pre_exists(tmp_path):
    """A second identical-format paste must not silently become POST --
    the caller always states the slot explicitly."""
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    make_snapshot_with_match_id(repository, "770131822")
    service = OfficialRatingImportService(repository=repository)

    service.import_and_link(SAMPLE_TEXT, slot=PRE)
    # explicitly requesting PRE again (not POST) must still require
    # confirmation, never silently redirect to POST
    with pytest.raises(OfficialRatingReplaceConfirmationRequired):
        service.import_and_link(SAMPLE_TEXT, slot=PRE)


def test_post_import_is_independent_of_pre(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    make_snapshot_with_match_id(repository, "770131822")
    service = OfficialRatingImportService(repository=repository)

    service.import_and_link(SAMPLE_TEXT, slot=PRE)
    outcome = service.import_and_link(SAMPLE_TEXT, slot=POST)

    assert outcome.snapshot.official_pre is not None
    assert outcome.snapshot.official_post is not None


def test_import_ratings_also_requires_confirmation_to_replace(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    snapshot = make_snapshot_with_match_id(repository, "770131822")
    service = OfficialRatingImportService(repository=repository)

    service.import_ratings(snapshot.snapshot_id, SAMPLE_TEXT, slot=PRE)
    with pytest.raises(OfficialRatingReplaceConfirmationRequired):
        service.import_ratings(snapshot.snapshot_id, SAMPLE_TEXT, slot=PRE)

    outcome = service.import_ratings(
        snapshot.snapshot_id, SAMPLE_TEXT, slot=PRE, confirm_replace=True
    )
    assert outcome.snapshot.official_pre is not None
