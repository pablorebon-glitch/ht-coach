from collections import Counter

import pytest

from importers.csv_importer import load_players

from models.formations import (
    FORMATION_352,
    FORMATIONS
)

from models.position import Position
from models.side import Side

from engine.generators.candidate_lineup_generator import (
    CandidateLineupGenerator
)


@pytest.fixture(scope="module")
def players():

    return load_players(
        "players.csv"
    )


def lineup_key(lineup):

    return tuple(
        sorted(
            (
                id(lineup_player.player),
                lineup_player.position.value,
                lineup_player.side.value
            )
            for lineup_player
            in lineup.players
        )
    )


@pytest.mark.parametrize(
    "formation",
    FORMATIONS
)
def test_generated_lineups_have_eleven_players(
    players,
    formation
):

    lineups = CandidateLineupGenerator.generate(
        players,
        formation,
        beam_width=100
    )

    assert lineups

    for lineup in lineups:

        assert len(lineup.players) == 11


@pytest.mark.parametrize(
    "formation",
    FORMATIONS
)
def test_generated_lineups_do_not_repeat_players(
    players,
    formation
):

    lineups = CandidateLineupGenerator.generate(
        players,
        formation,
        beam_width=100
    )

    for lineup in lineups:

        player_ids = [
            id(lineup_player.player)
            for lineup_player
            in lineup.players
        ]

        assert len(player_ids) == len(
            set(player_ids)
        )


@pytest.mark.parametrize(
    "formation",
    FORMATIONS
)
def test_generated_lineups_respect_formation_positions(
    players,
    formation
):

    lineups = CandidateLineupGenerator.generate(
        players,
        formation,
        beam_width=100
    )

    for lineup in lineups:

        actual_positions = Counter(
            lineup_player.position
            for lineup_player
            in lineup.players
        )

        assert actual_positions == Counter(
            formation.positions
        )


@pytest.mark.parametrize(
    "formation",
    FORMATIONS
)
def test_two_lateral_players_use_left_and_right_sides(
    players,
    formation
):

    lineups = CandidateLineupGenerator.generate(
        players,
        formation,
        beam_width=100
    )

    lateral_positions = {
        Position.WING_BACK,
        Position.WINGER,
    }

    for lineup in lineups:

        for position in lateral_positions:

            expected_amount = (
                formation.positions.get(
                    position,
                    0
                )
            )

            lateral_players = [
                lineup_player
                for lineup_player
                in lineup.players
                if lineup_player.position
                == position
            ]

            if expected_amount == 2:

                assert {
                    lineup_player.side
                    for lineup_player
                    in lateral_players
                } == {
                    Side.LEFT,
                    Side.RIGHT
                }


@pytest.mark.parametrize(
    "formation",
    FORMATIONS
)
def test_non_lateral_positions_use_center_side(
    players,
    formation
):

    lineups = CandidateLineupGenerator.generate(
        players,
        formation,
        beam_width=100
    )

    lateral_positions = {
        Position.WING_BACK,
        Position.WINGER,
    }

    for lineup in lineups:

        for lineup_player in lineup.players:

            if (
                lineup_player.position
                not in lateral_positions
            ):

                assert (
                    lineup_player.side
                    == Side.CENTER
                )


@pytest.mark.parametrize(
    "formation",
    FORMATIONS
)
def test_generated_lineups_are_unique(
    players,
    formation
):

    lineups = CandidateLineupGenerator.generate(
        players,
        formation,
        beam_width=100
    )

    keys = [
        lineup_key(lineup)
        for lineup in lineups
    ]

    assert len(keys) == len(set(keys))


@pytest.mark.parametrize(
    "formation",
    FORMATIONS
)
def test_generator_does_not_exceed_beam_width(
    players,
    formation
):

    beam_width = 50

    lineups = CandidateLineupGenerator.generate(
        players,
        formation,
        beam_width=beam_width
    )

    assert len(lineups) <= beam_width


def test_generator_is_deterministic(players):

    first_run = CandidateLineupGenerator.generate(
        players,
        FORMATION_352,
        beam_width=100
    )

    second_run = CandidateLineupGenerator.generate(
        players,
        FORMATION_352,
        beam_width=100
    )

    first_keys = [
        lineup_key(lineup)
        for lineup in first_run
    ]

    second_keys = [
        lineup_key(lineup)
        for lineup in second_run
    ]

    assert first_keys == second_keys