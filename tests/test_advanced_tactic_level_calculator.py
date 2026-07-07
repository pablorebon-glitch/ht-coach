import pytest

from engine.calculators.advanced_tactic_level_calculator import (
    AdvancedTacticLevelCalculator
)

from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.player import Player
from models.position import Position
from models.side import Side
from models.tactic import Tactic


def make_player(
    name,
    passing=10,
    defending=10,
    stamina=10,
    playmaking=10,
    scoring=10,
    set_pieces=10,
    form=7
):

    return Player(
        name=name,
        age=25,
        days=0,
        speciality="",
        form=form,
        stamina=stamina,
        goalkeeper=1,
        defending=defending,
        playmaking=playmaking,
        winger=10,
        passing=passing,
        scoring=scoring,
        set_pieces=set_pieces,
        experience=5,
        leadership=5,
        tsi=1000,
        salary=1000
    )


def make_lineup(
    **skills
):

    lineup = Lineup()

    lineup.players.append(
        LineupPlayer(
            player=make_player(
                "Goalkeeper",
                **skills
            ),
            position=Position.GOALKEEPER,
            side=Side.CENTER
        )
    )

    for index in range(10):

        lineup.players.append(
            LineupPlayer(
                player=make_player(
                    f"Player {index}",
                    **skills
                ),
                position=Position.INNER_MIDFIELDER,
                side=Side.CENTER
            )
        )

    return lineup


@pytest.mark.parametrize(
    "tactic",
    list(Tactic)
)
def test_levels_are_clamped(
    tactic
):

    lineup = make_lineup(
        passing=100,
        defending=100,
        stamina=100,
        playmaking=100,
        scoring=100,
        set_pieces=100
    )

    level = (
        AdvancedTacticLevelCalculator.calculate(
            lineup,
            tactic
        )
    )

    assert 0.0 <= level <= 20.0


def test_normal_level_is_zero():

    lineup = make_lineup()

    assert (
        AdvancedTacticLevelCalculator.calculate(
            lineup,
            Tactic.NORMAL
        )
        == 0.0
    )


def test_pressing_uses_defending_and_stamina():

    weak = make_lineup(
        defending=5,
        stamina=5
    )

    strong = make_lineup(
        defending=15,
        stamina=15
    )

    assert (
        AdvancedTacticLevelCalculator.calculate(
            strong,
            Tactic.PRESSING
        )
        >
        AdvancedTacticLevelCalculator.calculate(
            weak,
            Tactic.PRESSING
        )
    )


def test_counter_attacks_uses_defending_and_passing():

    weak = make_lineup(
        defending=5,
        passing=5
    )

    strong = make_lineup(
        defending=15,
        passing=15
    )

    assert (
        AdvancedTacticLevelCalculator.calculate(
            strong,
            Tactic.COUNTER_ATTACKS
        )
        >
        AdvancedTacticLevelCalculator.calculate(
            weak,
            Tactic.COUNTER_ATTACKS
        )
    )


def test_play_creatively_uses_passing_and_playmaking():

    weak = make_lineup(
        passing=5,
        playmaking=5
    )

    strong = make_lineup(
        passing=15,
        playmaking=15
    )

    assert (
        AdvancedTacticLevelCalculator.calculate(
            strong,
            Tactic.PLAY_CREATIVELY
        )
        >
        AdvancedTacticLevelCalculator.calculate(
            weak,
            Tactic.PLAY_CREATIVELY
        )
    )


def test_long_shots_uses_scoring_and_set_pieces():

    weak = make_lineup(
        scoring=5,
        set_pieces=5
    )

    strong = make_lineup(
        scoring=15,
        set_pieces=15
    )

    assert (
        AdvancedTacticLevelCalculator.calculate(
            strong,
            Tactic.LONG_SHOTS
        )
        >
        AdvancedTacticLevelCalculator.calculate(
            weak,
            Tactic.LONG_SHOTS
        )
    )