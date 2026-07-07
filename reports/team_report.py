from engine.analyzers.player_analyzer import PlayerAnalyzer
from models.position import Position


class TeamReport:

    @staticmethod
    def show(players, analyzer):

        print("=" * 60)
        print("HT COACH REPORT")
        print("=" * 60)

        print(f"\nJugadores: {len(players)}")
        print(f"Edad promedio: {analyzer.average_age():.2f}")

        print("\nEspecialidades")

        for speciality, amount in analyzer.specialties().items():
            print(f"{speciality:15} {amount}")

        TeamReport.show_position(
            players,
            Position.CENTRAL_DEFENDER,
            "BEST CENTRAL DEFENDERS"
        )

        TeamReport.show_position(
            players,
            Position.WING_BACK,
            "BEST WING BACKS"
        )
        TeamReport.show_position(
            players,
            Position.INNER_MIDFIELDER,
            "BEST INNER MIDFIELDERS"
        )
        TeamReport.show_position(
            players,
            Position.GOALKEEPER,
            "BEST GOALKEEPERS"
        )
        TeamReport.show_position(
                players,
                Position.WINGER,
                "BEST WINGERS"
        )        
        TeamReport.show_position(
                players,
                Position.FORWARD,
                "BEST FORWARDS"
        )


    @staticmethod
    def show_position(players, position, title):

        print("\n" + "=" * 60)
        print(title)
        print("=" * 60)

        ranking = PlayerAnalyzer.rank_players(
            players,
            position.value
        )

        for player_score in ranking:
            print(
                f"{player_score.player.name:30}"
                f"{player_score.score}"
            )