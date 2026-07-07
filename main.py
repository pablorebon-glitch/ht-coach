from importers.csv_importer import load_players

from engine.team_analyzer import TeamAnalyzer
from engine.optimizers.lineup_optimizer import LineupOptimizer
from engine.optimizers.formation_optimizer import FormationOptimizer

from engine.analyzers.team_selector import TeamSelector
from engine.analyzers.team_rater import TeamRater
from engine.analyzers.formation_analyzer import FormationAnalyzer

from reports.team_report import TeamReport
from reports.formation_comparison_report import FormationComparisonReport

from models.formations import FORMATION_352, FORMATIONS


def main():

    # Formación seleccionada manualmente
    formation = FORMATION_352

    # Cargar jugadores
    players = load_players("players.csv")

    # Analizador general del plantel
    analyzer = TeamAnalyzer(players)

    # Mostrar reporte del plantel
    TeamReport.show(
        players,
        analyzer
    )

    print("\n" + "=" * 60)
    print("FORMATION")
    print("=" * 60)
    print(formation.name)

    print("\n" + "=" * 60)
    print(f"BEST XI ({formation.name})")
    print("=" * 60)

    # Calcular mejor XI para la formación seleccionada
    lineup = LineupOptimizer.optimize(
        players,
        formation
    )

    for lp in lineup.players:
        print(f"{lp.position.value:22}{lp.player.name}")

    print("\n" + "=" * 60)
    print("MISSING POSITIONS")
    print("=" * 60)

    missing = TeamSelector.missing_positions(
        lineup,
        formation
    )

    if not missing:
        print("None")
    else:
        for position, amount in missing.items():
            print(f"{position.value:22}{amount}")

    print("\n" + "=" * 60)
    print("ESTIMATED TEAM RATINGS")
    print("=" * 60)

    ratings = TeamRater.calculate(lineup)

    print(f"Left Defense   : {ratings.left_defense:.2f}")
    print(f"Central Defense: {ratings.central_defense:.2f}")
    print(f"Right Defense  : {ratings.right_defense:.2f}")

    print()

    print(f"Midfield       : {ratings.midfield:.2f}")

    print()

    print(f"Left Attack    : {ratings.left_attack:.2f}")
    print(f"Central Attack : {ratings.central_attack:.2f}")
    print(f"Right Attack   : {ratings.right_attack:.2f}")

    print("\n" + "=" * 60)
    print("FORMATION SCORE")
    print("=" * 60)

    score = FormationAnalyzer.overall_score(
        ratings
    )

    print(f"{score:.2f}")

    # Analizar todas las formaciones
    results = FormationOptimizer.optimize(
        players,
        FORMATIONS
    )

    # Mostrar comparación completa
    FormationComparisonReport.show(results)

    print("\n" + "=" * 60)
    print("RECOMMENDED FORMATION")
    print("=" * 60)

    best_formation, best_lineup, best_ratings, best_score = results[0]

    print(f"Formation: {best_formation.name}")
    print(f"Score    : {best_score:.2f}")

    print("\nBEST XI")

    for lp in best_lineup.players:
        print(f"{lp.position.value:22}{lp.player.name}")


if __name__ == "__main__":
    main()