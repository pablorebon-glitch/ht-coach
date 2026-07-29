import pytest

from engine.history.models import SectorRatings
from engine.history.official_ratings.models import RatedAttribute
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.services.official_rating_formatting import (
    format_hattrick_notation,
    format_rated_attribute,
    format_sector_band,
)
from ht_coach_app.services.official_rating_service import (
    POST,
    PRE,
    OfficialRatingImportError,
    OfficialRatingImportService,
)


SAMPLE_TEXT = """
Formation: 2-5-3
Central defense: 7.00
Left defense: 4.25
Right defense: 3.75
Midfield: 7.25
Left attack: 7.75
Central attack: 9.75
Right attack: 8.00
Tactic: Attack in the middle
Tactic level: world class (13)
Team Attitude: Normal
"""


def make_snapshot(repository):
    from engine.history.models import HistoricalMatchSnapshot, MatchContext, stable_snapshot_id

    snapshot = HistoricalMatchSnapshot(
        snapshot_id=stable_snapshot_id(),
        match_context=MatchContext(match_date="2026-07-20"),
    )
    return repository.save(snapshot)


# --------------------------------------------------------------------------
# Import service
# --------------------------------------------------------------------------

def test_import_ratings_attaches_pre_slot(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    snapshot = make_snapshot(repository)
    service = OfficialRatingImportService(repository=repository)

    updated = service.import_ratings(snapshot.snapshot_id, SAMPLE_TEXT, slot=PRE)

    assert updated.snapshot.official_pre is not None
    assert updated.snapshot.official_pre.ratings.midfield == 7.25
    assert updated.snapshot.official_post is None


def test_import_ratings_attaches_post_slot_without_touching_pre(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    snapshot = make_snapshot(repository)
    service = OfficialRatingImportService(repository=repository)

    service.import_ratings(snapshot.snapshot_id, SAMPLE_TEXT, slot=PRE)
    post_text = SAMPLE_TEXT.replace("Midfield: 7.25", "Midfield: 7.50")
    updated = service.import_ratings(snapshot.snapshot_id, post_text, slot=POST)

    assert updated.snapshot.official_pre.ratings.midfield == 7.25
    assert updated.snapshot.official_post.ratings.midfield == 7.50


def test_import_persists_through_repository(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    snapshot = make_snapshot(repository)
    service = OfficialRatingImportService(repository=repository)

    service.import_ratings(snapshot.snapshot_id, SAMPLE_TEXT, slot=PRE)

    reloaded = repository.get(snapshot.snapshot_id)
    assert reloaded.official_pre.ratings.midfield == 7.25


def test_import_unknown_snapshot_raises_clear_error(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    service = OfficialRatingImportService(repository=repository)

    with pytest.raises(OfficialRatingImportError):
        service.import_ratings("does-not-exist", SAMPLE_TEXT, slot=PRE)


def test_import_invalid_slot_raises_clear_error(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    snapshot = make_snapshot(repository)
    service = OfficialRatingImportService(repository=repository)

    with pytest.raises(OfficialRatingImportError):
        service.import_ratings(snapshot.snapshot_id, SAMPLE_TEXT, slot="sideways")


def test_import_malformed_text_raises_clear_error(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    snapshot = make_snapshot(repository)
    service = OfficialRatingImportService(repository=repository)

    with pytest.raises(OfficialRatingImportError):
        service.import_ratings(snapshot.snapshot_id, "not a copy ratings block at all", slot=PRE)


def test_import_does_not_regenerate_or_reinterpret_the_pasted_values(tmp_path):
    """The core design principle: HT Coach never recomputes an imported
    official rating — whatever was parsed is exactly what's stored."""
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    snapshot = make_snapshot(repository)
    service = OfficialRatingImportService(repository=repository)

    updated = service.import_ratings(snapshot.snapshot_id, SAMPLE_TEXT, slot=PRE)
    assert updated.snapshot.official_pre.raw_text.strip() == SAMPLE_TEXT.strip()


# --------------------------------------------------------------------------
# Formatting
# --------------------------------------------------------------------------

def test_format_sector_band_with_all_values():
    assert format_sector_band(4.25, 7.0, 3.75) == "4.25 | 7.00 | 3.75"


def test_format_sector_band_with_missing_value():
    assert format_sector_band(None, 7.0, 3.75) == "? | 7.00 | 3.75"


def test_format_rated_attribute_with_label_quality_and_level():
    attribute = RatedAttribute(label="2-5-3", quality="excellent", level=8)
    assert format_rated_attribute(attribute) == "2-5-3 excellent (8)"


def test_format_rated_attribute_with_only_quality():
    attribute = RatedAttribute(quality="Normal")
    assert format_rated_attribute(attribute) == "Normal"


def test_format_rated_attribute_none_is_empty_string():
    assert format_rated_attribute(None) == ""


def test_format_hattrick_notation_matches_the_brief_example_exactly():
    ratings = SectorRatings(
        left_defense=4.25, central_defense=7.00, right_defense=3.75,
        midfield=7.25, left_attack=7.75, central_attack=9.75, right_attack=8.00,
    )
    formation = RatedAttribute(label="2-5-3", quality="excellent", level=8)
    tactic = RatedAttribute(quality="Attack in the Middle world class", level=13)

    text = format_hattrick_notation(ratings, formation, tactic, "Normal")

    assert text == (
        "Defense\n4.25 | 7.00 | 3.75\n\n"
        "Midfield\n7.25\n\n"
        "Attack\n7.75 | 9.75 | 8.00\n\n"
        "Formation\n2-5-3 excellent (8)\n\n"
        "Tactic\nAttack in the Middle world class (13)\n\n"
        "Team Attitude\nNormal"
    )


def test_format_hattrick_notation_omits_sections_with_nothing_to_show():
    ratings = SectorRatings(midfield=7.0)
    text = format_hattrick_notation(ratings)
    assert "Formation" not in text
    assert "Tactic" not in text
    assert "Team Attitude" not in text
    assert "Midfield" in text


# --------------------------------------------------------------------------
# Prediction vs official comparison (scale-compatibility limitation)
# --------------------------------------------------------------------------

def test_comparison_never_shows_a_numeric_delta_while_scales_unconfirmed():
    from ht_coach_app.services.official_rating_formatting import (
        SCALES_CONFIRMED_COMPATIBLE,
        format_prediction_vs_official_comparison,
    )
    from engine.history.official_ratings.comparison import compare_official_ratings
    from engine.history.official_ratings.parser import parse_official_ratings

    assert SCALES_CONFIRMED_COMPATIBLE is False

    predicted = SectorRatings(
        left_defense=4.0, central_defense=7.0, right_defense=3.5,
        midfield=7.0, left_attack=7.5, central_attack=9.5, right_attack=8.0,
    )
    sample = (
        "[b]Test[/b] [matchid=123]\n\n"
        "[table][tr][th]Defensa[/th][td]4.25[/td][td]7[/td][td]3.75[/td][/tr]"
        "[tr][th]Mediocampo[/th][td colspan=3]7.25[/td][/tr]"
        "[tr][th]Ataque[/th][td]7.75[/td][td]9.75[/td][td]8[/td][/tr][/table]\n"
        "[b]Formación[/b]: 2-5-3"
    )
    pre = parse_official_ratings(sample)
    comparison = compare_official_ratings(predicted, pre, None)

    rows = format_prediction_vs_official_comparison(comparison)
    assert len(rows) == 7
    for sector, predicted_value, official_value, delta in rows:
        assert delta is None
        assert predicted_value != "?"
        assert official_value != "?"


def test_comparison_still_shows_both_raw_values_side_by_side():
    from ht_coach_app.services.official_rating_formatting import (
        format_prediction_vs_official_comparison,
    )
    from engine.history.official_ratings.comparison import compare_official_ratings

    predicted = SectorRatings(midfield=7.0)
    comparison = compare_official_ratings(predicted, None, None)
    rows = format_prediction_vs_official_comparison(comparison)
    midfield_row = next(row for row in rows if row[0] == "midfield")
    assert midfield_row[1] == "7.00"
    assert midfield_row[2] == "?"  # no official value captured yet
