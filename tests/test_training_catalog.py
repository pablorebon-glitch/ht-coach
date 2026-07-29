import pytest

from engine.weekly_training.training_catalog import all_definitions, definition_for
from engine.weekly_training.training_effects import TrainingEffect, best_effect
from engine.weekly_training.training_types import TrainingType
from models.position import Position

FULL = TrainingEffect.FULL
REDUCED = TrainingEffect.REDUCED
VERY_SMALL = TrainingEffect.VERY_SMALL
NONE_EFFECT = TrainingEffect.NONE

ALL_POSITIONS = tuple(Position)


# --------------------------------------------------------------------------
# Catalog integrity
# --------------------------------------------------------------------------

def test_catalog_has_exactly_twelve_training_types():
    assert len(TrainingType) == 12
    assert len(all_definitions()) == 12


def test_catalog_lookup_is_deterministic_and_unique():
    seen = set()
    for training_type in TrainingType:
        definition = definition_for(training_type)
        assert definition is not None
        assert definition.training_type == training_type
        assert training_type not in seen
        seen.add(training_type)


def test_definition_for_accepts_raw_string_value():
    assert definition_for("PLAYMAKING") is definition_for(TrainingType.PLAYMAKING)
    assert definition_for("playmaking") is definition_for(TrainingType.PLAYMAKING)


def test_definition_for_unknown_type_returns_none():
    assert definition_for("SOME_FUTURE_TYPE") is None
    assert definition_for(None) is None


def test_every_definition_has_at_least_one_primary_skill():
    for definition in all_definitions():
        assert len(definition.primary_skills) >= 1


def test_training_definition_rejects_no_skills():
    from engine.weekly_training.training_definition import TrainingDefinition

    with pytest.raises(ValueError):
        TrainingDefinition(training_type=TrainingType.GENERAL, primary_skills=())


def test_training_type_parse_tolerant():
    assert TrainingType.parse("playmaking") == TrainingType.PLAYMAKING
    assert TrainingType.parse("PLAYMAKING") == TrainingType.PLAYMAKING
    assert TrainingType.parse("nonsense") is None
    assert TrainingType.parse("nonsense", default=TrainingType.PLAYMAKING) == (
        TrainingType.PLAYMAKING
    )


def test_training_effect_ordering_and_weights():
    assert FULL.sort_order < REDUCED.sort_order < VERY_SMALL.sort_order < NONE_EFFECT.sort_order
    assert FULL.weight > REDUCED.weight > VERY_SMALL.weight > NONE_EFFECT.weight
    assert best_effect([REDUCED, FULL, VERY_SMALL]) == FULL
    assert best_effect([]) == NONE_EFFECT


# --------------------------------------------------------------------------
# Per-type matrix tests
# --------------------------------------------------------------------------

def test_general_training():
    definition = definition_for(TrainingType.GENERAL)
    assert definition.effect_for(Position.FORWARD, "form") == FULL
    assert definition.effect_for(Position.GOALKEEPER, "form") == FULL
    assert definition.effect_for(Position.GOALKEEPER, "goalkeeping") == VERY_SMALL
    assert definition.effect_for(Position.FORWARD, "goalkeeping") == NONE_EFFECT


def test_set_pieces_training():
    definition = definition_for(TrainingType.SET_PIECES)
    for position in ALL_POSITIONS:
        assert definition.effect_for(position, "set_pieces") == FULL
    assert "goalkeeper_bonus" in definition.special_bonus_rules
    assert "set_pieces_taker_bonus" in definition.special_bonus_rules


def test_defending_training():
    definition = definition_for(TrainingType.DEFENDING)
    assert definition.effect_for(Position.CENTRAL_DEFENDER, "defending") == FULL
    assert definition.effect_for(Position.WING_BACK, "defending") == FULL
    for position in (Position.GOALKEEPER, Position.INNER_MIDFIELDER, Position.WINGER, Position.FORWARD):
        assert definition.effect_for(position, "defending") == VERY_SMALL


def test_scoring_training():
    definition = definition_for(TrainingType.SCORING)
    assert definition.effect_for(Position.FORWARD, "scoring") == FULL
    for position in (Position.GOALKEEPER, Position.CENTRAL_DEFENDER, Position.WING_BACK, Position.INNER_MIDFIELDER, Position.WINGER):
        assert definition.effect_for(position, "scoring") == VERY_SMALL


def test_winger_training():
    definition = definition_for(TrainingType.WINGER)
    assert definition.effect_for(Position.WINGER, "winger") == FULL
    assert definition.effect_for(Position.WING_BACK, "winger") == REDUCED
    for position in (Position.GOALKEEPER, Position.CENTRAL_DEFENDER, Position.INNER_MIDFIELDER, Position.FORWARD):
        assert definition.effect_for(position, "winger") == VERY_SMALL


def test_shooting_training_is_multi_skill():
    definition = definition_for(TrainingType.SHOOTING)
    assert set(definition.primary_skills) == {"scoring", "set_pieces"}
    for position in ALL_POSITIONS:
        assert definition.effect_for(position, "scoring") == REDUCED
        assert definition.effect_for(position, "set_pieces") == VERY_SMALL


def test_short_passes_training():
    definition = definition_for(TrainingType.SHORT_PASSES)
    for position in (Position.INNER_MIDFIELDER, Position.WINGER, Position.FORWARD):
        assert definition.effect_for(position, "passing") == FULL
    for position in (Position.GOALKEEPER, Position.CENTRAL_DEFENDER, Position.WING_BACK):
        assert definition.effect_for(position, "passing") == VERY_SMALL


def test_playmaking_training_matches_original_behavior():
    definition = definition_for(TrainingType.PLAYMAKING)
    assert definition.effect_for(Position.INNER_MIDFIELDER, "playmaking") == FULL
    assert definition.effect_for(Position.WINGER, "playmaking") == REDUCED
    for position in (Position.GOALKEEPER, Position.CENTRAL_DEFENDER, Position.WING_BACK, Position.FORWARD):
        assert definition.effect_for(position, "playmaking") == VERY_SMALL


def test_goalkeeping_training_has_no_positional_effect_for_others():
    definition = definition_for(TrainingType.GOALKEEPING)
    assert definition.effect_for(Position.GOALKEEPER, "goalkeeping") == FULL
    for position in (Position.CENTRAL_DEFENDER, Position.WING_BACK, Position.INNER_MIDFIELDER, Position.WINGER, Position.FORWARD):
        assert definition.effect_for(position, "goalkeeping") == NONE_EFFECT


def test_through_passes_training():
    definition = definition_for(TrainingType.THROUGH_PASSES)
    for position in (Position.CENTRAL_DEFENDER, Position.WING_BACK, Position.INNER_MIDFIELDER, Position.WINGER):
        assert definition.effect_for(position, "passing") == FULL
    for position in (Position.GOALKEEPER, Position.FORWARD):
        assert definition.effect_for(position, "passing") == VERY_SMALL


def test_defensive_positions_training_is_reduced_not_full():
    definition = definition_for(TrainingType.DEFENSIVE_POSITIONS)
    for position in (Position.GOALKEEPER, Position.CENTRAL_DEFENDER, Position.WING_BACK, Position.INNER_MIDFIELDER, Position.WINGER):
        assert definition.effect_for(position, "defending") == REDUCED
    assert definition.effect_for(Position.FORWARD, "defending") == VERY_SMALL


def test_wing_attacks_training():
    definition = definition_for(TrainingType.WING_ATTACKS)
    assert definition.effect_for(Position.WINGER, "winger") == FULL
    assert definition.effect_for(Position.FORWARD, "winger") == FULL
    for position in (Position.GOALKEEPER, Position.CENTRAL_DEFENDER, Position.WING_BACK, Position.INNER_MIDFIELDER):
        assert definition.effect_for(position, "winger") == VERY_SMALL


# --------------------------------------------------------------------------
# effects_for_position / best_effect_for_position / trainable_positions
# --------------------------------------------------------------------------

def test_effects_for_position_returns_all_trained_skills():
    definition = definition_for(TrainingType.SHOOTING)
    effects = definition.effects_for_position(Position.FORWARD)
    assert effects == {"scoring": REDUCED, "set_pieces": VERY_SMALL}


def test_best_effect_for_position_picks_strongest_skill():
    definition = definition_for(TrainingType.GENERAL)
    assert definition.best_effect_for_position(Position.GOALKEEPER) == FULL


def test_trainable_positions_excludes_none_effect_positions():
    definition = definition_for(TrainingType.GOALKEEPING)
    trainable = definition.trainable_positions()
    assert Position.GOALKEEPER in trainable
    assert Position.FORWARD not in trainable


def test_trainable_positions_includes_all_positions_when_blanket_effect_exists():
    definition = definition_for(TrainingType.PLAYMAKING)
    trainable = definition.trainable_positions()
    assert set(trainable) == set(Position)
