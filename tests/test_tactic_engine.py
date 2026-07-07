from engine.tactics.tactic_context import (
    TacticContext
)

from engine.tactics.tactic_engine import (
    TacticEngine
)

from models.tactic import Tactic
from models.team_ratings import TeamRatings


def make_ratings():

    return TeamRatings(
        left_defense=30,
        central_defense=40,
        right_defense=30,
        midfield=45,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )


def test_normal_effects_are_neutral():

    ratings = make_ratings()

    context, effects = (
        TacticEngine.evaluate_effects(
            lineup=None,
            base_ratings=ratings,
            opponent_ratings=ratings,
            tactic=Tactic.NORMAL
        )
    )

    assert context.level == 0.0

    assert (
        effects.our_chance_multiplier
        == 1.0
    )

    assert (
        effects.opponent_chance_multiplier
        == 1.0
    )

    assert (
        effects.counter_attack_chances
        == 0.0
    )

    assert (
        effects.special_event_multiplier
        == 1.0
    )

    assert (
        effects.long_shot_conversion_rate
        == 0.0
    )


def test_pressing_without_lineup_is_neutral():

    ratings = make_ratings()

    _, effects = (
        TacticEngine.evaluate_effects(
            lineup=None,
            base_ratings=ratings,
            opponent_ratings=ratings,
            tactic=Tactic.PRESSING
        )
    )

    assert (
        effects.our_chance_multiplier
        == 1.0
    )

    assert (
        effects.opponent_chance_multiplier
        == 1.0
    )


def test_counter_attacks_without_lineup_adds_no_chances():

    ratings = make_ratings()

    _, effects = (
        TacticEngine.evaluate_effects(
            lineup=None,
            base_ratings=ratings,
            opponent_ratings=ratings,
            tactic=Tactic.COUNTER_ATTACKS
        )
    )

    assert (
        effects.counter_attack_chances
        == 0.0
    )


def test_play_creatively_without_lineup_is_neutral():

    ratings = make_ratings()

    _, effects = (
        TacticEngine.evaluate_effects(
            lineup=None,
            base_ratings=ratings,
            opponent_ratings=ratings,
            tactic=Tactic.PLAY_CREATIVELY
        )
    )

    assert (
        effects.special_event_multiplier
        == 1.0
    )


def test_long_shots_without_lineup_is_neutral():

    ratings = make_ratings()

    _, effects = (
        TacticEngine.evaluate_effects(
            lineup=None,
            base_ratings=ratings,
            opponent_ratings=ratings,
            tactic=Tactic.LONG_SHOTS
        )
    )

    assert (
        effects.long_shot_conversion_rate
        == 0.0
    )


def test_counter_attacks_are_inactive_with_equal_midfield():

    ratings = make_ratings()

    context = TacticContext(
        tactic=Tactic.COUNTER_ATTACKS,
        level=20.0,
        lineup=None,
        base_ratings=ratings,
        opponent_ratings=ratings
    )

    effects = TacticEngine.apply(
        context
    )

    assert (
        effects.counter_attack_chances
        == 0.0
    )


def test_counter_attacks_require_lower_midfield():

    our_ratings = TeamRatings(
        left_defense=30,
        central_defense=40,
        right_defense=30,
        midfield=30,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )

    opponent_ratings = TeamRatings(
        left_defense=30,
        central_defense=40,
        right_defense=30,
        midfield=60,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )

    context = TacticContext(
        tactic=Tactic.COUNTER_ATTACKS,
        level=20.0,
        lineup=None,
        base_ratings=our_ratings,
        opponent_ratings=opponent_ratings
    )

    effects = TacticEngine.apply(
        context
    )

    assert (
        effects.counter_attack_chances
        > 0.0
    )


def test_more_opponent_midfield_dominance_produces_more_counter_attacks():

    our_ratings = TeamRatings(
        left_defense=30,
        central_defense=40,
        right_defense=30,
        midfield=30,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )

    moderate_opponent = TeamRatings(
        left_defense=30,
        central_defense=40,
        right_defense=30,
        midfield=40,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )

    strong_opponent = TeamRatings(
        left_defense=30,
        central_defense=40,
        right_defense=30,
        midfield=70,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )

    moderate_context = TacticContext(
        tactic=Tactic.COUNTER_ATTACKS,
        level=20.0,
        lineup=None,
        base_ratings=our_ratings,
        opponent_ratings=moderate_opponent
    )

    strong_context = TacticContext(
        tactic=Tactic.COUNTER_ATTACKS,
        level=20.0,
        lineup=None,
        base_ratings=our_ratings,
        opponent_ratings=strong_opponent
    )

    moderate_effects = TacticEngine.apply(
        moderate_context
    )

    strong_effects = TacticEngine.apply(
        strong_context
    )

    assert (
        strong_effects.counter_attack_chances
        > moderate_effects.counter_attack_chances
    )


def test_long_shots_are_inactive_against_normal_defense():

    ratings = make_ratings()

    context = TacticContext(
        tactic=Tactic.LONG_SHOTS,
        level=20.0,
        lineup=None,
        base_ratings=ratings,
        opponent_ratings=ratings
    )

    effects = TacticEngine.apply(
        context
    )

    assert (
        effects.long_shot_conversion_rate
        == 0.0
    )


def test_long_shots_activate_against_strong_defense():

    our_ratings = TeamRatings(
        left_defense=30,
        central_defense=40,
        right_defense=30,
        midfield=45,
        left_attack=15,
        central_attack=15,
        right_attack=15
    )

    opponent_ratings = TeamRatings(
        left_defense=60,
        central_defense=60,
        right_defense=60,
        midfield=45,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )

    context = TacticContext(
        tactic=Tactic.LONG_SHOTS,
        level=20.0,
        lineup=None,
        base_ratings=our_ratings,
        opponent_ratings=opponent_ratings
    )

    effects = TacticEngine.apply(
        context
    )

    assert (
        effects.long_shot_conversion_rate
        > 0.0
    )


def test_stronger_defense_increases_long_shot_usage():

    our_ratings = TeamRatings(
        left_defense=30,
        central_defense=40,
        right_defense=30,
        midfield=45,
        left_attack=15,
        central_attack=15,
        right_attack=15
    )

    moderate_opponent = TeamRatings(
        left_defense=30,
        central_defense=30,
        right_defense=30,
        midfield=45,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )

    strong_opponent = TeamRatings(
        left_defense=70,
        central_defense=70,
        right_defense=70,
        midfield=45,
        left_attack=30,
        central_attack=35,
        right_attack=30
    )

    moderate_context = TacticContext(
        tactic=Tactic.LONG_SHOTS,
        level=20.0,
        lineup=None,
        base_ratings=our_ratings,
        opponent_ratings=moderate_opponent
    )

    strong_context = TacticContext(
        tactic=Tactic.LONG_SHOTS,
        level=20.0,
        lineup=None,
        base_ratings=our_ratings,
        opponent_ratings=strong_opponent
    )

    moderate_effects = TacticEngine.apply(
        moderate_context
    )

    strong_effects = TacticEngine.apply(
        strong_context
    )

    assert (
        strong_effects.long_shot_conversion_rate
        > moderate_effects.long_shot_conversion_rate
    )