from pathlib import Path

import pytest

from engine.history.models import SectorRatings
from engine.history.official_ratings.comparison import compare_official_ratings
from engine.history.official_ratings.models import OfficialRatingSnapshot, RatedAttribute
from engine.history.official_ratings.parser import parse_official_ratings
from engine.history.official_ratings.summary import summarize_official_rating_comparison
from engine.history.official_ratings.validation import (
    OfficialRatingParsingError,
    OfficialRatingValidationError,
    validate_official_rating_snapshot,
)


SAMPLE_EN = """
[b]Test FC[/b] [matchid=123456789]

[table]
[tr][th]Defense[/th][td align=center]4.25[/td][td align=center]7.00[/td][td align=center]3.75[/td][/tr]
[tr][th]Midfield[/th][td colspan=3 align=center]7.25[/td][/tr]
[tr][th]Attack[/th][td align=center]7.75[/td][td align=center]9.75[/td][td align=center]8.00[/td][/tr]
[/table]

[b]Formation[/b]: 2-5-3 excellent (8)
[b]Tactics[/b]: Attack in the middle world class (13)
[b]Team Attitude[/b]: Normal
[b]Style of play[/b]: Normal
[b]Average rating[/b]: 7.15
"""

SAMPLE_ES = """
[b]Equipo de Prueba[/b] [matchid=987654321]

[table]
[tr][th]Defensa[/th][td align=center]6.50[/td][td align=center]5.00[/td][td align=center]5.25[/td][/tr]
[tr][th]Mediocampo[/th][td colspan=3 align=center]8.00[/td][/tr]
[tr][th]Ataque[/th][td align=center]6.00[/td][td align=center]7.50[/td][td align=center]6.25[/td][/tr]
[/table]

[b]Formacion[/b]: 4-4-2
[b]Tacticas[/b]: Atacar por el centro
[b]Actitud del equipo[/b]: Normal
[b]Estilo de juego[/b]: Normal
"""

# A verbatim real-world "Copy Ratings" paste, used to calibrate this parser.
REAL_SAMPLE_TORRES_FC = """[b]Hit'em up - Torres Futbol Club[/b] [matchid=770131822]

[table]
[tr][th]Defensa[/th][td align=center]4.25[/td][td align=center]7[/td][td align=center]3.75[/td][/tr]
[tr][th]Mediocampo[/th][td colspan=3 align=center]7.25[/td][/tr]
[tr][th]Ataque[/th][td align=center]7.75[/td][td align=center]9.75[/td][td align=center]8[/td][/tr]
[/table]

[b]Formación[/b]: 2-5-3 aceptable (6)
[b]Tácticas[/b]: Atacar por el centro clase mundial (13)
[b]Actitud del equipo[/b]: Normal
[b]Estilo de juego[/b]: 100% ofensivo"""


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------

def test_parser_extracts_all_seven_core_sectors_english():
    result = parse_official_ratings(SAMPLE_EN)
    assert result.ratings.central_defense == 7.00
    assert result.ratings.left_defense == 4.25
    assert result.ratings.right_defense == 3.75
    assert result.ratings.midfield == 7.25
    assert result.ratings.left_attack == 7.75
    assert result.ratings.central_attack == 9.75
    assert result.ratings.right_attack == 8.00


def test_parser_extracts_all_seven_core_sectors_spanish():
    result = parse_official_ratings(SAMPLE_ES)
    assert result.ratings.left_defense == 6.50
    assert result.ratings.central_defense == 5.00
    assert result.ratings.right_defense == 5.25
    assert result.ratings.midfield == 8.00
    assert result.ratings.left_attack == 6.00
    assert result.ratings.central_attack == 7.50
    assert result.ratings.right_attack == 6.25


def test_parser_extracts_formation_and_tactic():
    result = parse_official_ratings(SAMPLE_EN)
    assert result.formation.label == "2-5-3"
    assert result.tactic.label == "Attack in the middle"
    assert result.tactic.quality == "world class"
    assert result.tactic.level == 13.0


def test_parser_formation_with_quality_and_number_inline():
    text = "Formation: 3-5-2 excellent (8)\nMidfield: 6.0"
    result = parse_official_ratings(text)
    assert result.formation.label == "3-5-2"
    assert result.formation.quality == "excellent"
    assert result.formation.level == 8.0


def test_parser_team_attitude_and_style():
    result = parse_official_ratings(SAMPLE_EN)
    assert result.team_attitude == "Normal"
    assert result.style == "Normal"


def test_parser_average_rating():
    result = parse_official_ratings(SAMPLE_EN)
    assert result.average_rating == 7.15


def test_parser_marks_source_as_hattrick_official():
    result = parse_official_ratings(SAMPLE_EN)
    assert result.ratings.source.value == "hattrick_official"


def test_parser_unknown_lines_are_preserved_not_dropped_silently():
    text = SAMPLE_EN + "\nSome completely unknown future field: whatever\n"
    result = parse_official_ratings(text)
    assert any("unknown future field" in line.lower() for line in result.unparsed_lines)
    # the known fields are still correctly parsed despite the unknown line
    assert result.ratings.midfield == 7.25


def test_parser_rejects_empty_text():
    with pytest.raises(OfficialRatingParsingError):
        parse_official_ratings("")
    with pytest.raises(OfficialRatingParsingError):
        parse_official_ratings("   \n   ")
    with pytest.raises(OfficialRatingParsingError):
        parse_official_ratings(None)


def test_parser_comma_decimal_separator_is_tolerated():
    text = "Central defense: 7,00\nMidfield: 6,50"
    result = parse_official_ratings(text)
    assert result.ratings.central_defense == 7.0
    assert result.ratings.midfield == 6.5


def test_parser_indirect_set_pieces_lines():
    text = (
        "Indirect free kicks (defense): 4.0\n"
        "Indirect free kicks (attack): 5.5\n"
    )
    result = parse_official_ratings(text)
    assert result.ratings.indirect_defense == 4.0
    assert result.ratings.indirect_attack == 5.5


def test_parser_captured_at_defaults_to_now_but_is_overridable():
    result = parse_official_ratings(SAMPLE_EN, captured_at="2026-07-20T10:00:00Z")
    assert result.captured_at == "2026-07-20T10:00:00Z"

    default_result = parse_official_ratings(SAMPLE_EN)
    assert default_result.captured_at  # non-empty, auto-generated


def test_parser_short_english_keyword_does_not_eat_longer_spanish_keyword():
    """Regression: 'tactic' (EN) must not consume part of 'tactica' (ES)."""
    text = "Tactica: Ataque por el centro"
    result = parse_official_ratings(text)
    assert result.tactic.label == "Ataque por el centro"


def test_parser_raw_text_preserved_verbatim():
    result = parse_official_ratings(SAMPLE_EN)
    assert result.raw_text == SAMPLE_EN


# --------------------------------------------------------------------------
# Real-world calibration sample
# --------------------------------------------------------------------------

def test_real_sample_extracts_team_name_and_match_id():
    result = parse_official_ratings(REAL_SAMPLE_TORRES_FC, language="es")
    assert result.team_name == "Hit'em up - Torres Futbol Club"
    assert result.hattrick_match_id == "770131822"


def test_real_sample_extracts_all_sector_ratings():
    result = parse_official_ratings(REAL_SAMPLE_TORRES_FC)
    assert result.ratings.left_defense == 4.25
    assert result.ratings.central_defense == 7.0
    assert result.ratings.right_defense == 3.75
    assert result.ratings.midfield == 7.25
    assert result.ratings.left_attack == 7.75
    assert result.ratings.central_attack == 9.75
    assert result.ratings.right_attack == 8.0


def test_real_sample_extracts_formation():
    result = parse_official_ratings(REAL_SAMPLE_TORRES_FC)
    assert result.formation.label == "2-5-3"
    assert result.formation.quality == "aceptable"
    assert result.formation.level == 6.0


def test_real_sample_splits_tactic_name_from_quality_with_no_delimiter():
    """The hardest real-world case: "Atacar por el centro clase mundial
    (13)" has no separator between the tactic name (a known, fixed
    Hattrick value) and its quality word — both are free text."""
    result = parse_official_ratings(REAL_SAMPLE_TORRES_FC)
    assert result.tactic.label == "Atacar por el centro"
    assert result.tactic.quality == "clase mundial"
    assert result.tactic.level == 13.0


def test_real_sample_team_attitude_and_style():
    result = parse_official_ratings(REAL_SAMPLE_TORRES_FC)
    assert result.team_attitude == "Normal"
    assert result.style == "100% ofensivo"


def test_real_sample_has_no_unparsed_lines():
    result = parse_official_ratings(REAL_SAMPLE_TORRES_FC)
    assert result.unparsed_lines == ()


def test_real_sample_sector_order_is_left_center_right_and_orientation_independent():
    """The copied table provides Defense/Attack as (left, center, right)
    columns, in that order. This order is a property of the *data*, not
    of how the Formation Board happens to mirror a lineup visually for
    display -- nothing in the parser or the model reads or depends on
    any pitch-orientation/mirroring state, so it can never be reversed
    by it."""
    result = parse_official_ratings(REAL_SAMPLE_TORRES_FC)
    assert (
        result.ratings.left_defense,
        result.ratings.central_defense,
        result.ratings.right_defense,
    ) == (4.25, 7.0, 3.75)
    assert (
        result.ratings.left_attack,
        result.ratings.central_attack,
        result.ratings.right_attack,
    ) == (7.75, 9.75, 8.0)


def test_parser_module_never_imports_formation_board_code():
    """A structural guarantee alongside the value-based one above: the
    parser can't be influenced by Formation Board orientation state
    because it doesn't even import anything from it."""
    import ast

    path = (
        Path(__file__).resolve().parents[1]
        / "engine" / "history" / "official_ratings" / "parser.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    assert not any("formation_board" in module for module in imported)


def test_real_sample_validates_successfully():
    result = parse_official_ratings(REAL_SAMPLE_TORRES_FC)
    validate_official_rating_snapshot(result)


def test_real_sample_hattrick_wording_differs_from_apps_own_translation():
    """This app's own localization says "ataque por el centro" (noun);
    real Hattrick text says "atacar por el centro" (verb). Both must be
    recognized as the same tactic."""
    result = parse_official_ratings(REAL_SAMPLE_TORRES_FC)
    assert "atacar" in result.tactic.label.lower()


# --------------------------------------------------------------------------
# Tactic canonicalization
# --------------------------------------------------------------------------

def test_real_sample_resolves_canonical_tactic():
    from models.tactic import Tactic

    result = parse_official_ratings(REAL_SAMPLE_TORRES_FC)
    assert result.canonical_tactic == Tactic.ATTACK_IN_MIDDLE.value
    assert result.warnings == ()


def test_apps_own_translation_also_resolves_to_the_same_canonical_tactic():
    from models.tactic import Tactic

    text = "Tacticas: Ataque por el centro clase mundial (13)\nFormation: 3-5-2"
    result = parse_official_ratings(text)
    assert result.canonical_tactic == Tactic.ATTACK_IN_MIDDLE.value


def test_unknown_tactic_preserves_raw_value_and_produces_warning():
    text = "Tactics: Some Future Tactic Nobody Knows (9)\nFormation: 3-5-2"
    result = parse_official_ratings(text)
    assert result.canonical_tactic == ""
    assert "official_rating.warning.unsupported_tactic" in result.warnings
    # the raw text is still preserved -- an unknown tactic never
    # invalidates the rest of the import
    assert "Some Future Tactic" in result.tactic.raw_text


def test_unknown_tactic_does_not_invalidate_otherwise_usable_ratings():
    text = (
        "Formation: 3-5-2\n"
        "Tactics: Some Future Tactic Nobody Knows (9)\n"
        "Central defense: 7.0\nLeft defense: 4.0\nRight defense: 3.5\n"
        "Midfield: 6.0\nLeft attack: 5.0\nCentral attack: 6.0\nRight attack: 5.5\n"
    )
    result = parse_official_ratings(text)
    validate_official_rating_snapshot(result)  # must not raise
    assert result.ratings.midfield == 6.0


def test_all_seven_hattrick_tactics_are_resolved_from_english():
    from models.tactic import Tactic

    cases = {
        "Normal": Tactic.NORMAL,
        "Attack in the middle": Tactic.ATTACK_IN_MIDDLE,
        "Attack on Wings": Tactic.ATTACK_ON_WINGS,
        "Pressing": Tactic.PRESSING,
        "Counter-Attacks": Tactic.COUNTER_ATTACKS,
        "Play Creatively": Tactic.PLAY_CREATIVELY,
        "Long Shots": Tactic.LONG_SHOTS,
    }
    for text, expected in cases.items():
        result = parse_official_ratings(f"Tactics: {text}\nFormation: 3-5-2")
        assert result.canonical_tactic == expected.value, text


def test_all_seven_hattrick_tactics_are_resolved_from_spanish():
    from models.tactic import Tactic

    cases = {
        "Atacar por el centro": Tactic.ATTACK_IN_MIDDLE,
        "Atacar por las bandas": Tactic.ATTACK_ON_WINGS,
        "Presion": Tactic.PRESSING,
        "Contraataques": Tactic.COUNTER_ATTACKS,
        "Jugar creativamente": Tactic.PLAY_CREATIVELY,
        "Tiros lejanos": Tactic.LONG_SHOTS,
    }
    for text, expected in cases.items():
        result = parse_official_ratings(f"Tacticas: {text}\nFormation: 3-5-2")
        assert result.canonical_tactic == expected.value, text


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def test_validate_accepts_a_complete_snapshot():
    snapshot = parse_official_ratings(SAMPLE_EN)
    assert validate_official_rating_snapshot(snapshot) is snapshot


def test_validate_rejects_incomplete_sector_coverage():
    text = "Formation: 3-5-2\nMidfield: 6.0"
    snapshot = parse_official_ratings(text)
    with pytest.raises(OfficialRatingValidationError):
        validate_official_rating_snapshot(snapshot)


def test_validate_accepts_detailed_post_missing_formation():
    """Alpha 0.6.3: DETAILED_POST may legitimately omit formation --
    this must no longer fail validation (it did before POST support
    was added, when every input was assumed to be COMPACT_PRE-shaped)."""
    text = "\n".join(
        f"{label}: 6.0" for label in (
            "Central defense", "Left defense", "Right defense",
            "Midfield", "Left attack", "Central attack", "Right attack",
        )
    )
    snapshot = parse_official_ratings(text)
    assert snapshot.detected_format == "DETAILED_POST"
    validate_official_rating_snapshot(snapshot)  # must not raise


def test_validate_rejects_compact_pre_missing_formation():
    """COMPACT_PRE (a [table] block present) still requires a
    formation token -- it's always present in the confirmed real PRE
    sample, so its absence signals a genuinely malformed paste."""
    text = (
        "[table][tr][th]Defense[/th][td]4.0[/td][td]6.0[/td][td]4.0[/td][/tr]"
        "[tr][th]Midfield[/th][td colspan=3]6.0[/td][/tr]"
        "[tr][th]Attack[/th][td]5.0[/td][td]6.0[/td][td]5.5[/td][/tr][/table]"
    )
    snapshot = parse_official_ratings(text)
    assert snapshot.detected_format == "COMPACT_PRE"
    with pytest.raises(OfficialRatingValidationError):
        validate_official_rating_snapshot(snapshot)


def test_validate_minimum_sectors_is_configurable():
    text = "Formation: 3-5-2\nCentral defense: 6.0\nMidfield: 7.0"
    snapshot = parse_official_ratings(text)
    with pytest.raises(OfficialRatingValidationError):
        validate_official_rating_snapshot(snapshot, minimum_sectors=4)
    # but with a lower bar it's accepted
    validate_official_rating_snapshot(snapshot, minimum_sectors=2)


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------

def make_predicted():
    return SectorRatings(
        left_defense=4.0, central_defense=7.0, right_defense=3.5,
        midfield=7.0, left_attack=7.5, central_attack=9.5, right_attack=8.0,
    )


def test_comparison_with_prediction_and_pre_only():
    predicted = make_predicted()
    pre = parse_official_ratings(SAMPLE_EN)
    comparison = compare_official_ratings(predicted, pre, None)

    midfield = comparison.sector("midfield")
    assert midfield.predicted_value == 7.0
    assert midfield.official_pre_value == 7.25
    assert midfield.predicted_vs_pre_delta == pytest.approx(0.25)
    assert midfield.official_post_value is None
    assert midfield.pre_vs_post_delta is None


def test_comparison_with_all_three_present():
    predicted = make_predicted()
    pre = parse_official_ratings(SAMPLE_EN)
    post_text = SAMPLE_EN.replace("Midfield: 7.25", "Midfield: 7.25")
    post = parse_official_ratings(post_text)
    comparison = compare_official_ratings(predicted, pre, post)

    midfield = comparison.sector("midfield")
    assert midfield.pre_vs_post_delta == 0.0


def test_comparison_with_nothing_present_has_all_none_deltas():
    comparison = compare_official_ratings(None, None, None)
    for sector in comparison.sectors:
        assert sector.predicted_value is None
        assert sector.official_pre_value is None
        assert sector.official_post_value is None
        assert sector.predicted_vs_pre_delta is None


def test_comparison_covers_all_seven_reported_sectors():
    comparison = compare_official_ratings(make_predicted(), None, None)
    assert len(comparison.sectors) == 7


def test_comparison_serializes_to_dict():
    comparison = compare_official_ratings(make_predicted(), parse_official_ratings(SAMPLE_EN), None)
    payload = comparison.to_dict()
    assert "sectors" in payload
    assert len(payload["sectors"]) == 7


# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------

def test_summary_average_and_max_error():
    predicted = SectorRatings(
        left_defense=4.0, central_defense=7.0, right_defense=3.5,
        midfield=7.0, left_attack=7.5, central_attack=9.5, right_attack=8.0,
    )
    pre = parse_official_ratings(SAMPLE_EN)
    comparison = compare_official_ratings(predicted, pre, None)
    summary = summarize_official_rating_comparison(comparison, "official_pre")

    assert summary.average_error is not None
    assert summary.maximum_error is not None
    assert summary.confidence == "high"
    assert summary.missing_sectors == ()


def test_summary_identifies_closest_and_furthest_sectors():
    predicted = SectorRatings(
        left_defense=4.25, central_defense=7.00, right_defense=3.75,
        midfield=5.0, left_attack=7.75, central_attack=9.75, right_attack=8.00,
    )
    pre = parse_official_ratings(SAMPLE_EN)  # midfield official = 7.25, predicted = 5.0 -> biggest gap
    comparison = compare_official_ratings(predicted, pre, None)
    summary = summarize_official_rating_comparison(comparison, "official_pre")

    assert summary.furthest_sector == "midfield"
    assert summary.closest_sector != "midfield"


def test_summary_with_no_data_is_insufficient():
    comparison = compare_official_ratings(None, None, None)
    summary = summarize_official_rating_comparison(comparison, "official_pre")
    assert summary.confidence == "insufficient_data"
    assert summary.average_error is None
    assert len(summary.missing_sectors) == 7


def test_summary_missing_sectors_tracked_separately_from_present_ones():
    text = "Formation: 3-5-2\nCentral defense: 7.0\nMidfield: 7.0\nLeft attack: 7.0\nCentral attack: 7.0"
    pre = parse_official_ratings(text)
    comparison = compare_official_ratings(make_predicted(), pre, None)
    summary = summarize_official_rating_comparison(comparison, "official_pre")

    assert "left_defense" in summary.missing_sectors
    assert "right_defense" in summary.missing_sectors
    assert "right_attack" in summary.missing_sectors


def test_summary_confidence_scales_with_coverage():
    # only 2 of 7 sectors present -> low confidence
    text = "Formation: 3-5-2\nCentral defense: 7.0\nMidfield: 7.0"
    pre = parse_official_ratings(text)
    comparison = compare_official_ratings(make_predicted(), pre, None)
    summary = summarize_official_rating_comparison(comparison, "official_pre")
    assert summary.confidence == "low"


def test_summary_compared_against_official_post():
    predicted = make_predicted()
    post = parse_official_ratings(SAMPLE_EN)
    comparison = compare_official_ratings(predicted, None, post)
    summary = summarize_official_rating_comparison(comparison, "official_post")
    assert summary.compared_against == "official_post"
    assert summary.average_error is not None
