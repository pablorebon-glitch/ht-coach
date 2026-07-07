from validation.validator import Validator

from importers.csv_importer import load_players

from engine.optimizers.lineup_optimizer import LineupOptimizer
from engine.analyzers.team_rater import TeamRater

from models.formations import FORMATION_352


def main():

    players = load_players("players.csv")

    lineup = LineupOptimizer.optimize(
        players,
        FORMATION_352
    )

    ratings = TeamRater.calculate(
        lineup
    )

    expected = Validator.load_expected(
        "validation/match_001/expected.json"
    )

    comparison = Validator.compare(
        ratings,
        expected
    )

    print("=" * 60)
    print("MODEL VALIDATION")
    print("=" * 60)

    total_error = 0

    for area, values in comparison.items():

        print(
            f"{area:20}"
            f"{values['calculated']:8.2f}"
            f"{values['expected']:8.2f}"
            f"{values['difference']:8.2f}"
        )

        total_error += abs(values["difference"])

    print()

    print("=" * 60)

    print(
        f"Average Error: "
        f"{total_error / len(comparison):.2f}"
    )


if __name__ == "__main__":
    main()