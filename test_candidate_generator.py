from importers.csv_importer import load_players

from models.formations import FORMATIONS

from engine.analyzers.team_rater import TeamRater
from engine.analyzers.formation_analyzer import FormationAnalyzer

from engine.generators.candidate_lineup_generator import (
    CandidateLineupGenerator
)


players = load_players("players.csv")


for formation in FORMATIONS:

    print()
    print("=" * 95)
    print(f"FORMATION: {formation.name}")
    print("=" * 95)

    lineups = CandidateLineupGenerator.generate(
        players,
        formation
    )

    print(
        f"Generated unique lineups: "
        f"{len(lineups)}"
    )

    evaluated_lineups = []

    for lineup in lineups:

        ratings = TeamRater.calculate(
            lineup
        )

        score = FormationAnalyzer.overall_score(
            ratings
        )

        evaluated_lineups.append(
            (
                lineup,
                ratings,
                score
            )
        )

    evaluated_lineups.sort(
        key=lambda result: result[2],
        reverse=True
    )

    print()
    print("TOP 5 CANDIDATE LINEUPS")

    for index, (
        lineup,
        ratings,
        score
    ) in enumerate(
        evaluated_lineups[:5],
        start=1
    ):

        print()
        print(
            f"{index}. SCORE: {score:.2f}"
        )

        print(
            f"   RATINGS: "
            f"MID {ratings.midfield:.2f} | "
            f"DEF-L {ratings.left_defense:.2f} | "
            f"DEF-C {ratings.central_defense:.2f} | "
            f"DEF-R {ratings.right_defense:.2f} | "
            f"ATT-L {ratings.left_attack:.2f} | "
            f"ATT-C {ratings.central_attack:.2f} | "
            f"ATT-R {ratings.right_attack:.2f}"
        )

        print()

        for lineup_player in lineup.players:

            print(
                f"   "
                f"{lineup_player.side.value:8}"
                f"{lineup_player.position.value:22}"
                f"{lineup_player.player.name}"
            )