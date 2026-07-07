from engine.calculators.normal_chance_calculator import (
    NormalChanceCalculator
)


def main():

    scenarios = [

        (10, 100),
        (20, 100),
        (30, 100),
        (40, 100),
        (50, 100),
        (60, 100),
        (70, 100),
        (80, 100),
        (90, 100),

        (100, 100),

        (100, 90),
        (100, 80),
        (100, 70),
        (100, 60),
        (100, 50),
        (100, 40),
        (100, 30),
        (100, 20),
        (100, 10),
    ]

    print()

    print("=" * 105)

    print(
        "MIDFIELD SENSITIVITY ANALYSIS"
    )

    print("=" * 105)

    print(
        f"{'OUR MID':>10}"
        f"{'OPP MID':>10}"
        f"{'RATIO':>12}"
        f"{'POSSESSION':>15}"
        f"{'CHANCE PROB':>16}"
        f"{'EXPECTED CH':>15}"
        f"{'OPP CH':>12}"
    )

    print("-" * 105)

    for (
        our_midfield,
        opponent_midfield
    ) in scenarios:

        result = (
            NormalChanceCalculator.calculate(
                midfield=our_midfield,
                opponent_midfield=(
                    opponent_midfield
                )
            )
        )

        ratio = (
            our_midfield
            / opponent_midfield
            if opponent_midfield > 0
            else float("inf")
        )

        print(
            f"{our_midfield:>10.2f}"
            f"{opponent_midfield:>10.2f}"
            f"{ratio:>12.4f}"
            f"{result.possession * 100:>14.2f}%"
            f"{result.chance_probability * 100:>15.2f}%"
            f"{result.expected_chances:>15.4f}"
            f"{result.opponent_expected_chances:>12.4f}"
        )

    print("=" * 105)


if __name__ == "__main__":
    main()