class MidfieldExponentComparison:

    EXPONENTS = (
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
    )

    POSSESSIONS = (
        0.30,
        0.35,
        0.40,
        0.45,
        0.50,
        0.55,
        0.60,
        0.65,
        0.70,
    )

    TOTAL_NORMAL_CHANCES = 10.0

    @staticmethod
    def chance_share(
        possession,
        exponent
    ):

        opponent_possession = (
            1.0
            - possession
        )

        our_strength = (
            possession
            ** exponent
        )

        opponent_strength = (
            opponent_possession
            ** exponent
        )

        total_strength = (
            our_strength
            + opponent_strength
        )

        if total_strength <= 0:
            return 0.5

        return (
            our_strength
            / total_strength
        )

    @classmethod
    def run(cls):

        print()

        print("=" * 108)

        print(
            "MIDFIELD EXPONENT COMPARISON"
        )

        print("=" * 108)

        header = (
            f"{'POSSESSION':>12}"
        )

        for exponent in cls.EXPONENTS:

            header += (
                f"{f'K={exponent:.1f}':>18}"
            )

        print(header)

        print("-" * 108)

        for possession in cls.POSSESSIONS:

            row = (
                f"{possession * 100:>11.2f}%"
            )

            for exponent in cls.EXPONENTS:

                chance_share = (
                    cls.chance_share(
                        possession,
                        exponent
                    )
                )

                expected_chances = (
                    cls.TOTAL_NORMAL_CHANCES
                    * chance_share
                )

                cell = (
                    f"{chance_share * 100:>7.2f}%"
                    f" / "
                    f"{expected_chances:>5.2f}"
                )

                row += (
                    f"{cell:>18}"
                )

            print(row)

        print("=" * 108)

        print()

        print(
            "CELL FORMAT: "
            "CHANCE SHARE / EXPECTED CHANCES"
        )


def main():

    MidfieldExponentComparison.run()


if __name__ == "__main__":
    main()