from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.player import Player
from models.position import Position
from models.side import Side
from models.tactic import Tactic

from engine.calculators.tactic_level_calculator import (
    TacticLevelCalculator
)


def make_player(
    name,
    passing,
    form=7
):

    return Player(
        name=name,
        age=25,
        days=0,
        speciality="",

        form=form,
        stamina=7,

        goalkeeper=1,
        defending=10,
        playmaking=10,
        winger=10,
        passing=passing,
        scoring=10,
        set_pieces=5,

        experience=5,
        leadership=5,

        tsi=1000,
        salary=1000
    )


def make_lineup(
    passing,
    form=7
):

    lineup = Lineup()

    lineup.players.append(
        LineupPlayer(
            player=make_player(
                "Goalkeeper",
                passing=20,
                form=form
            ),
            position=Position.GOALKEEPER,
            side=Side.CENTER
        )
    )

    for index in range(10):

        lineup.players.append(
            LineupPlayer(
                player=make_player(
                    f"Field Player {index}",
                    passing=passing,
                    form=form
                ),
                position=Position.INNER_MIDFIELDER,
                side=Side.CENTER
            )
        )

    return lineup


def test_normal_tactic_has_zero_level():

    lineup = make_lineup(
        passing=15
    )

    level = (
        TacticLevelCalculator.calculate(
            lineup,
            Tactic.NORMAL
        )
    )

    assert level == 0.0


def test_goalkeeper_is_ignored():

    lineup = make_lineup(
        passing=10
    )

    lineup.players[0].player.passing = 20

    level = (
        TacticLevelCalculator.calculate(
            lineup,
            Tactic.ATTACK_IN_MIDDLE
        )
    )

    assert level == 10.0


def test_average_passing_determines_level():

    lineup = make_lineup(
        passing=10
    )

    lineup.players[1].player.passing = 20

    level = (
        TacticLevelCalculator.calculate(
            lineup,
            Tactic.ATTACK_IN_MIDDLE
        )
    )

    assert level == 11.0


def test_higher_passing_produces_higher_level():

    low_lineup = make_lineup(
        passing=5
    )

    high_lineup = make_lineup(
        passing=15
    )

    low_level = (
        TacticLevelCalculator.calculate(
            low_lineup,
            Tactic.ATTACK_IN_MIDDLE
        )
    )

    high_level = (
        TacticLevelCalculator.calculate(
            high_lineup,
            Tactic.ATTACK_IN_MIDDLE
        )
    )

    assert high_level > low_level


def test_form_affects_tactic_level():

    low_form = make_lineup(
        passing=10,
        form=3
    )

    high_form = make_lineup(
        passing=10,
        form=8
    )

    low_level = (
        TacticLevelCalculator.calculate(
            low_form,
            Tactic.ATTACK_ON_WINGS
        )
    )

    high_level = (
        TacticLevelCalculator.calculate(
            high_form,
            Tactic.ATTACK_ON_WINGS
        )
    )

    assert high_level > low_level


def test_level_is_clamped_to_maximum():

    lineup = make_lineup(
        passing=100
    )

    level = (
        TacticLevelCalculator.calculate(
            lineup,
            Tactic.ATTACK_ON_WINGS
        )
    )

    assert level == 20.0


def test_aim_and_aow_use_same_base_level_for_now():

    lineup = make_lineup(
        passing=12
    )

    aim_level = (
        TacticLevelCalculator.calculate(
            lineup,
            Tactic.ATTACK_IN_MIDDLE
        )
    )

    aow_level = (
        TacticLevelCalculator.calculate(
            lineup,
            Tactic.ATTACK_ON_WINGS
        )
    )

    assert aim_level == aow_level