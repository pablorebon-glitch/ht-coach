from copy import deepcopy

from importers.csv_importer import load_players

from models.formations import FORMATION_352
from models.side import Side

from engine.rating.player_rating_engine import (
    PlayerRatingEngine
)

from engine.optimizers.lineup_optimizer import (
    LineupOptimizer
)

from models.team_ratings import TeamRatings


players = load_players("players.csv")


def find_player(players, name):

    for player in players:

        if player.name == name:
            return player

    raise ValueError(
        f"Player not found: {name}"
    )


def show_player_form_curve(
    player,
    position,
    side=Side.CENTER
):

    print()
    print("=" * 80)
    print(f"FORM CURVE: {player.name}")
    print("=" * 80)

    original_form = player.form

    previous_score = None

    for form in range(1, 9):

        player.form = form

        score = PlayerRatingEngine.calculate(
            player,
            position,
            side
        )

        monotonic = (
            previous_score is None
            or score >= previous_score
        )

        print(
            f"Form {form}: "
            f"{score:8.2f} "
            f"{'OK' if monotonic else 'ERROR'}"
        )

        previous_score = score

    player.form = original_form


def show_lineup(lineup):

    for lineup_player in lineup.players:

        print(
            f"{lineup_player.side.value:8}"
            f"{lineup_player.position.value:22}"
            f"{lineup_player.player.name}"
            f" | Form {lineup_player.player.form}"
        )


def run_optimizer_test(
    players,
    opponent
):

    result = LineupOptimizer.optimize_against(
        players,
        FORMATION_352,
        opponent
    )

    print(
        f"Win probability: "
        f"{result.probabilities.win * 100:.2f}%"
    )

    print()

    show_lineup(
        result.lineup
    )

    return result


opponent = TeamRatings(
    left_defense=25,
    central_defense=35,
    right_defense=24,
    midfield=40,
    left_attack=25,
    central_attack=30,
    right_attack=24
)


test_players = deepcopy(
    players
)


player_a = find_player(
    test_players,
    "Pierre-Jean Delion"
)

player_b = find_player(
    test_players,
    "Fabián Abbiendi"
)


show_player_form_curve(
    player_a,
    "INNER_MIDFIELDER"
)


print()
print("=" * 80)
print("BASELINE")
print("=" * 80)

baseline_result = run_optimizer_test(
    test_players,
    opponent
)


print()
print("=" * 80)
print(
    f"SCENARIO 1: "
    f"{player_a.name} FORM 1 / "
    f"{player_b.name} FORM 8"
)
print("=" * 80)

player_a.form = 1
player_b.form = 8

scenario_1_result = run_optimizer_test(
    test_players,
    opponent
)


print()
print("=" * 80)
print(
    f"SCENARIO 2: "
    f"{player_a.name} FORM 8 / "
    f"{player_b.name} FORM 1"
)
print("=" * 80)

player_a.form = 8
player_b.form = 1

scenario_2_result = run_optimizer_test(
    test_players,
    opponent
)


print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)

print(
    f"Baseline win  : "
    f"{baseline_result.probabilities.win * 100:.2f}%"
)

print(
    f"Scenario 1 win: "
    f"{scenario_1_result.probabilities.win * 100:.2f}%"
)

print(
    f"Scenario 2 win: "
    f"{scenario_2_result.probabilities.win * 100:.2f}%"
)
