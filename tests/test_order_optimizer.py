import pytest

from importers.csv_importer import load_players

from engine.optimizers.lineup_optimizer import (
    LineupOptimizer
)

from engine.optimizers.order_optimizer import (
    OrderOptimizer
)
from engine.orders.legal_orders import legal_orders_for_slot

from models.formations import FORMATION_253, FORMATION_352
from models.order import Order
from models.side import Side
from models.team_ratings import TeamRatings


@pytest.fixture(scope="module")
def players():

    return load_players(
        "players.csv"
    )


@pytest.fixture(scope="module")
def opponent():

    return TeamRatings(
        left_defense=25,
        central_defense=35,
        right_defense=24,
        midfield=40,
        left_attack=25,
        central_attack=30,
        right_attack=24
    )


@pytest.fixture(scope="module")
def base_lineup(
    players
):

    return LineupOptimizer.optimize(
        players,
        FORMATION_352
    )


@pytest.fixture(scope="module")
def result(
    base_lineup,
    opponent
):

    return OrderOptimizer.optimize(
        base_lineup,
        opponent,
        beam_width=50
    )


def test_optimizer_returns_complete_lineup(
    result
):

    assert len(
        result.lineup.players
    ) == 11


def test_optimizer_does_not_change_players(
    base_lineup,
    result
):

    base_player_names = {
        lineup_player.player.name
        for lineup_player
        in base_lineup.players
    }

    optimized_player_names = {
        lineup_player.player.name
        for lineup_player
        in result.lineup.players
    }

    assert (
        optimized_player_names
        == base_player_names
    )


def test_optimizer_does_not_change_positions(
    base_lineup,
    result
):

    base_assignments = {
        (
            lineup_player.player.name,
            lineup_player.position,
            lineup_player.side
        )
        for lineup_player
        in base_lineup.players
    }

    optimized_assignments = {
        (
            lineup_player.player.name,
            lineup_player.position,
            lineup_player.side
        )
        for lineup_player
        in result.lineup.players
    }

    assert (
        optimized_assignments
        == base_assignments
    )


def test_optimizer_only_uses_allowed_configurations(
    result
):

    for lineup_player in result.lineup.players:

        allowed_configurations = legal_orders_for_slot(
            lineup_player.position,
            lineup_player.side,
        )

        actual_configuration = (
            lineup_player.order,
            lineup_player.order_side
        )

        allowed_pairs = {
            (
                configuration.order,
                configuration.order_side
            )
            for configuration
            in allowed_configurations
        }

        assert (
            actual_configuration
            in allowed_pairs
        )


def test_towards_wing_has_order_side(
    result
):

    for lineup_player in result.lineup.players:

        if (
            lineup_player.order
            == Order.TOWARDS_WING
        ):

            assert (
                lineup_player.order_side
                in {
                    Side.LEFT,
                    Side.RIGHT,
                }
            )


def test_optimizer_never_emits_towards_wing_for_central_forward(players, opponent):
    lineup = LineupOptimizer.optimize(players, FORMATION_253)
    result = OrderOptimizer.optimize(lineup, opponent, beam_width=50)
    central_forward = next(
        player
        for player in result.lineup.players
        if getattr(player.position, "value", player.position) == "FORWARD"
        and getattr(player.side, "value", player.side) == "CENTER"
    )

    assert central_forward.order != Order.TOWARDS_WING
    assert central_forward.order_side is None


def test_non_towards_wing_has_no_order_side(
    result
):

    for lineup_player in result.lineup.players:

        if (
            lineup_player.order
            != Order.TOWARDS_WING
        ):

            assert (
                lineup_player.order_side
                is None
            )


def test_optimizer_tests_configurations(
    result
):

    assert (
        result.tested_configurations
        > 0
    )


def test_optimizer_does_not_reduce_win_probability(
    result
):

    assert (
        result.probabilities.win
        >= result.baseline_win_probability
    )


def test_probabilities_sum_to_one(
    result
):

    total = (
        result.probabilities.win
        + result.probabilities.draw
        + result.probabilities.loss
    )

    assert total == pytest.approx(
        1.0,
        abs=1e-6
    )


def test_goalkeeper_remains_normal(
    result
):

    goalkeeper = next(
        lineup_player
        for lineup_player
        in result.lineup.players
        if lineup_player.position.value
        == "GOALKEEPER"
    )

    assert goalkeeper.order == Order.NORMAL

    assert goalkeeper.order_side is None


def test_optimizer_is_deterministic(
    base_lineup,
    opponent
):

    first_result = OrderOptimizer.optimize(
        base_lineup,
        opponent,
        beam_width=50
    )

    second_result = OrderOptimizer.optimize(
        base_lineup,
        opponent,
        beam_width=50
    )

    first_configurations = [
        (
            lineup_player.order,
            lineup_player.order_side
        )
        for lineup_player
        in first_result.lineup.players
    ]

    second_configurations = [
        (
            lineup_player.order,
            lineup_player.order_side
        )
        for lineup_player
        in second_result.lineup.players
    ]

    assert (
        first_configurations
        == second_configurations
    )

    assert (
        first_result.probabilities.win
        == pytest.approx(
            second_result.probabilities.win
        )
    )
