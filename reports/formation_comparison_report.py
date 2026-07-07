class FormationComparisonReport:

    @staticmethod
    def show(results):

        print("\n" + "=" * 95)
        print("FORMATION COMPARISON")
        print("=" * 95)

        header = (
            f"{'FORMATION':12}"
            f"{'MID':>9}"
            f"{'DEF-L':>9}"
            f"{'DEF-C':>9}"
            f"{'DEF-R':>9}"
            f"{'ATT-L':>9}"
            f"{'ATT-C':>9}"
            f"{'ATT-R':>9}"
            f"{'SCORE':>10}"
        )

        print(header)
        print("-" * 95)

        for formation, lineup, ratings, score in results:

            print(
                f"{formation.name:12}"
                f"{ratings.midfield:9.2f}"
                f"{ratings.left_defense:9.2f}"
                f"{ratings.central_defense:9.2f}"
                f"{ratings.right_defense:9.2f}"
                f"{ratings.left_attack:9.2f}"
                f"{ratings.central_attack:9.2f}"
                f"{ratings.right_attack:9.2f}"
                f"{score:10.2f}"
            )

        print("=" * 95)