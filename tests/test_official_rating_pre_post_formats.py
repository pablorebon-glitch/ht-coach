import pytest

from engine.history.official_ratings.parser import (
    COMPACT_PRE,
    DETAILED_POST,
    detect_format,
    parse_official_ratings,
    parse_official_post_ratings,
    parse_official_pre_ratings,
)
from engine.history.official_ratings.validation import (
    OfficialRatingValidationError,
    validate_official_post_rating_snapshot,
    validate_official_pre_rating_snapshot,
    validate_official_rating_snapshot,
)

REAL_SAMPLE_PRE = """[b]Hit'em up - Torres Futbol Club[/b] [matchid=770131822]

[table]
[tr][th]Defensa[/th][td align=center]4.25[/td][td align=center]7[/td][td align=center]3.75[/td][/tr]
[tr][th]Mediocampo[/th][td colspan=3 align=center]7.25[/td][/tr]
[tr][th]Ataque[/th][td align=center]7.75[/td][td align=center]9.75[/td][td align=center]8[/td][/tr]
[/table]

[b]Formación[/b]: 2-5-3 aceptable (6)
[b]Tácticas[/b]: Atacar por el centro clase mundial (13)
[b]Actitud del equipo[/b]: Normal
[b]Estilo de juego[/b]: 100% ofensivo"""

REAL_HF02_PRE = """[b]Hit'em up - Santa Cruz Club[/b] [matchid=770918226]

[table][tr][th]Defensa[/th][td align=center]3.25[/td][td align=center]4.5[/td][td align=center]3.25[/td][/tr][tr][th]Mediocampo[/th][td colspan=3 align=center]7.5[/td][/tr][tr][th]Ataque[/th][td align=center]6.75[/td][td align=center]9.5[/td][td align=center]8.5[/td][/tr][/table]
[b]FormaciÃ³n[/b]: 2-5-3 formidable (9)
[b]TÃ¡cticas[/b]: Atacar por el centro clase mundial (13)
[b]Actitud del equipo[/b]: Normal
[b]Estilo de juego[/b]: 100% ofensivo"""

REAL_HF02_POST = """[table][tr][th][matchid=770725689][/th][th colspan=2]Hit'em up [teamid=2819540][/th][/tr]
[tr][th]Mediocampo[/th][td]aceptable - muy bajo[/td][td align=right]6,00[/td][/tr]
[tr][th]Defensa derecha[/th][td]pobre - bajo[/td][td align=right]3,25[/td][/tr]
[tr][th]Defensa central[/th][td]dÃ©bil - muy alto[/td][td align=right]4,75[/td][/tr]
[tr][th]Defensa izquierda[/th][td]pobre - alto[/td][td align=right]3,50[/td][/tr]
[tr][th]Ataque derecho[/th][td]insuficiente - alto[/td][td align=right]5,50[/td][/tr]
[tr][th]Ataque central[/th][td]bueno - alto[/td][td align=right]7,50[/td][/tr]
[tr][th]Ataque izquierdo[/th][td]aceptable - muy alto[/td][td align=right]6,75[/td][/tr]
[tr][th colspan=3]Tiro indirecto[/th][/tr]
[tr][th]Defensa[/th][td]aceptable - muy bajo[/td][td align=right]6,00[/td][/tr]
[tr][th]Ataque[/th][td]insuficiente - bajo[/td][td align=right]5,25[/td][/tr]
[tr][th colspan=3]Plan de juego[/th][/tr]
[tr][th]Actitud del equipo[/th][td colspan=2](Oculta)[/td][/tr]
[tr][th]TÃ¡ctica[/th][td colspan=2]Atacar por el centro[/td][/tr]
[tr][th]Nivel de tÃ¡ctica[/th][td]clase mundial[/td][td align=right]13[/td][/tr]
[tr][th]Estilo de juego[/th][td colspan=2]100% ofensivo[/td][/tr]
[tr][th colspan=3]Calificaciones medias[/th][/tr]
[tr][th]Experiencia total de los jugadores[/th][td]pobre - muy bajo[/td][td align=right]3,00[/td][/tr]
[tr][th]Mediocampo promedio[/th][td]aceptable - muy bajo[/td][td align=right]6,00[/td][/tr]
[tr][th]Defensa promedio[/th][td]pobre - muy alto[/td][td align=right]3,75[/td][/tr]
[tr][th]Ataque promedio[/th][td]aceptable - alto[/td][td align=right]6,50[/td][/tr]
[tr][th]Promedio total[/th][td]insuficiente - alto[/td][td align=right]5,50[/td][/tr]
[/table]"""

SYNTHETIC_POST_SAMPLE = """
[b]Hit'em up - Torres Futbol Club[/b] [matchid=770131822]
Midfield: 7.50
Right Defense: 4,25
Central Defense: 7.00
Left Defense: 3.75
Right Attack: 8,00
Central Attack: 9.75
Left Attack: 7.75
Indirect Set Pieces (Defense): 4.0
Indirect Set Pieces (Attack): 5,5
Game Plan: Attack in the middle world class (13)
Average Ratings: 7.15
Hidden Team Attitude: Normal
Playing Style: 100% ofensivo
"""

SYNTHETIC_POST_MINIMAL = """
Midfield: 6.00
Right Defense: 4.00
Central Defense: 6.50
Left Defense: 4.10
Right Attack: 5.00
Central Attack: 6.00
Left Attack: 5.50
"""


def test_detect_format_recognizes_compact_pre():
    assert detect_format(REAL_SAMPLE_PRE) == COMPACT_PRE


def test_detect_format_recognizes_detailed_post():
    assert detect_format(SYNTHETIC_POST_SAMPLE) == DETAILED_POST


def test_detect_format_recognizes_real_detailed_post_table():
    assert detect_format(REAL_HF02_POST) == DETAILED_POST


def test_parser_still_recognizes_real_pre_sample_after_post_support_added():
    result = parse_official_pre_ratings(REAL_SAMPLE_PRE)
    assert result.detected_format == COMPACT_PRE
    assert result.ratings.midfield == 7.25
    assert result.unparsed_lines == ()


def test_post_sample_extracts_all_seven_sectors():
    result = parse_official_post_ratings(SYNTHETIC_POST_SAMPLE)
    assert result.detected_format == DETAILED_POST
    assert result.hattrick_match_id == "770131822"
    assert result.ratings.midfield == 7.50
    assert result.ratings.right_defense == 4.25
    assert result.ratings.central_defense == 7.00
    assert result.ratings.left_defense == 3.75
    assert result.ratings.right_attack == 8.00
    assert result.ratings.central_attack == 9.75
    assert result.ratings.left_attack == 7.75


def test_real_hf02_post_extracts_all_seven_core_sectors():
    result = parse_official_post_ratings(REAL_HF02_POST)

    assert result.detected_format == DETAILED_POST
    assert result.hattrick_match_id == "770725689"
    assert result.team_name == "Hit'em up"
    assert result.ratings.midfield == 6.00
    assert result.ratings.right_defense == 3.25
    assert result.ratings.central_defense == 4.75
    assert result.ratings.left_defense == 3.50
    assert result.ratings.right_attack == 5.50
    assert result.ratings.central_attack == 7.50
    assert result.ratings.left_attack == 6.75
    validate_official_post_rating_snapshot(result)


def test_real_hf02_post_preserves_secondary_ratings_without_overwriting_core_sectors():
    result = parse_official_post_ratings(REAL_HF02_POST)

    assert result.ratings.indirect_defense == 6.00
    assert result.ratings.indirect_attack == 5.25
    assert result.average_rating == 5.50
    assert result.ratings.right_defense == 3.25
    assert result.ratings.central_attack == 7.50


def test_real_hf02_post_preserves_plan_fields_and_allows_hidden_attitude():
    result = parse_official_post_ratings(REAL_HF02_POST)

    assert result.formation.label == ""
    assert result.team_attitude == "(Oculta)"
    assert result.tactic.label == "Atacar por el centro"
    assert result.tactic.quality == "clase mundial"
    assert result.tactic.level == 13.0
    assert result.style == "100% ofensivo"


def test_real_hf02_pre_behavior_remains_compact_pre():
    result = parse_official_pre_ratings(REAL_HF02_PRE)

    assert result.detected_format == COMPACT_PRE
    assert result.hattrick_match_id == "770918226"
    assert result.formation.label == "2-5-3"
    assert result.ratings.midfield == 7.5


def test_post_sample_extracts_indirect_set_pieces():
    result = parse_official_ratings(SYNTHETIC_POST_SAMPLE)
    assert result.ratings.indirect_defense == 4.0
    assert result.ratings.indirect_attack == 5.5


def test_post_sample_game_plan_maps_to_tactic_with_canonical_resolution():
    from models.tactic import Tactic

    result = parse_official_ratings(SYNTHETIC_POST_SAMPLE)
    assert result.tactic.label == "Attack in the middle"
    assert result.tactic.quality == "world class"
    assert result.tactic.level == 13.0
    assert result.canonical_tactic == Tactic.ATTACK_IN_MIDDLE.value


def test_post_sample_hidden_team_attitude_maps_to_team_attitude():
    result = parse_official_ratings(SYNTHETIC_POST_SAMPLE)
    assert result.team_attitude == "Normal"


def test_post_sample_playing_style_maps_to_style():
    result = parse_official_ratings(SYNTHETIC_POST_SAMPLE)
    assert result.style == "100% ofensivo"


def test_post_sample_average_ratings_plural_form_recognized():
    result = parse_official_ratings(SYNTHETIC_POST_SAMPLE)
    assert result.average_rating == 7.15


def test_post_sample_has_no_unparsed_lines():
    result = parse_official_ratings(SYNTHETIC_POST_SAMPLE)
    assert result.unparsed_lines == ()


def test_post_sample_passes_validation():
    result = parse_official_post_ratings(SYNTHETIC_POST_SAMPLE)
    validate_official_post_rating_snapshot(result)


def test_pre_and_post_have_independent_validation_rules():
    pre_like_without_formation = parse_official_ratings(
        "[table][tr][th]Defense[/th][td]4.0[/td][td]6.0[/td][td]4.0[/td][/tr]"
        "[tr][th]Midfield[/th][td colspan=3]6.0[/td][/tr]"
        "[tr][th]Attack[/th][td]5.0[/td][td]6.0[/td][td]5.5[/td][/tr][/table]"
    )
    post_without_formation = parse_official_post_ratings(SYNTHETIC_POST_MINIMAL)

    with pytest.raises(OfficialRatingValidationError):
        validate_official_pre_rating_snapshot(pre_like_without_formation)
    validate_official_post_rating_snapshot(post_without_formation)


def test_decimal_comma_and_point_both_normalize_correctly():
    comma_sample = "Midfield: 7,50\nCentral Defense: 6,00"
    point_sample = "Midfield: 7.50\nCentral Defense: 6.00"
    comma_result = parse_official_ratings(comma_sample)
    point_result = parse_official_ratings(point_sample)
    assert comma_result.ratings.midfield == point_result.ratings.midfield == 7.50
    assert comma_result.ratings.central_defense == point_result.ratings.central_defense == 6.00


def test_post_may_omit_formation_and_team_attitude_without_failing():
    result = parse_official_ratings(SYNTHETIC_POST_MINIMAL)
    assert result.formation.label == ""
    assert result.team_attitude == ""
    validate_official_rating_snapshot(result)


def test_post_minimal_sample_still_recognizes_all_seven_sectors():
    result = parse_official_ratings(SYNTHETIC_POST_MINIMAL)
    for sector in (
        "midfield", "right_defense", "central_defense", "left_defense",
        "right_attack", "central_attack", "left_attack",
    ):
        assert getattr(result.ratings, sector) is not None


def test_detected_format_persists_through_round_trip():
    result = parse_official_ratings(SYNTHETIC_POST_SAMPLE)
    payload = result.to_dict()
    from engine.history.official_ratings.models import OfficialRatingSnapshot

    restored = OfficialRatingSnapshot.from_dict(payload)
    assert restored.detected_format == DETAILED_POST
